# DictSQLite

DictSQLite is a Python library that gives you a dictionary-like API backed by SQLite. It runs all DB work on a background worker for simple thread-safe use, and optionally encrypts values at rest. This page explains how data is stored, how schemas are handled, what types are supported, and how to use the API safely.

Status: 20/20 tests pass on the reference suite bundled in this repo.

- Storage model: Pickle + Base64 (with legacy JSON auto-read) OR pure JSON via storage_mode='json'; optional RSA encryption of the stored text.  (v1.8.8+ adds selectable storage_mode)
- Schema model: Minimal key/value schema by default; you can provide a custom CREATE TABLE schema.
- Type model: Key is the primary key; value stores any pickle-able Python object (pickle mode) or any JSON-serializable object (json mode). Some mutable types can auto-sync.
- Concurrency model: A single background worker serializes operations; optional file lock mode exists.
- Security model: Safe Unpickler with allow-lists guards deserialization (pickle mode). JSON mode skips pickle entirely.


## Table schema management

By default, DictSQLite creates a simple key-value table when missing:

```sql
CREATE TABLE IF NOT EXISTS "main" (
  key   TEXT PRIMARY KEY,
  value TEXT
);
```

- Table name: The constructor argument table_name (default: "main"). Identifiers are safely quoted with double quotes.
- Custom schema: Pass a full column list string via schema, e.g. '(key INTEGER PRIMARY KEY, value TEXT)'.
  - Validation: The library will validate your schema by attempting to create and drop a temporary table. Semicolons are rejected to prevent multi-statement injection. If invalid, a ValueError is raised.
  - Requirements for dict-style access: Your schema must contain columns named key and value. Their types are up to you (TEXT/INTEGER/etc.).
- Multiple tables: Version 2 mode (version=2) exposes table selection through db["table_name"] which returns a TableProxy for that table. You can also call create_table("name", schema?) to ensure the table exists.
- Journal mode: If specified, PRAGMA journal_mode is set to a whitelisted value (DELETE/TRUNCATE/PERSIST/MEMORY/WAL/OFF). Any other value is rejected.


## How values are stored

When you assign db[key] = value, DictSQLite serializes and stores value according to storage_mode.

### storage_mode = 'pickle' (default)

1) Serialize with pickle using the highest protocol.
2) Base64-encode to obtain an ASCII string.
3) If password is set, encrypt this Base64 string using RSA-OAEP (keys are loaded from AES-encrypted PEM files). The encrypted bytes are stored (SQLite will store them as BLOB even if the column is declared TEXT).
4) Insert or replace into the table: (key, value).

On read:
- If password is set, bytes are decrypted.
- Legacy JSON decode is attempted first (for very old rows written as plain JSON text).
- If JSON fails, Base64 is decoded and the object is unpickled using a Safe Unpickler. If unpickling fails under the policy, the raw string is returned.

### storage_mode = 'json'

1) Value is json.dumps()'d using a custom hook that supports set (stored as {"__type__":"set","value":[...]}) and the RecursiveDict / synced collection wrappers.
2) The resulting UTF-8 text (not Base64) is encrypted if password is set, otherwise stored directly.
3) On read: (optional decrypt) -> json.loads() with hook -> Python object.
4) For backward compatibility, if JSON decoding fails (e.g. older pickle rows), the loader will then try pickle so mixed databases still read.

Implications:
- JSON mode disallows arbitrary Python objects (functions, custom classes without to_dict()). Use only JSON-native types + set. Attempting to store unsupported objects raises TypeError.
- Pickle mode supports arbitrary pickle-able objects (subject to the Safe Unpickler policy) but has a larger attack surface for untrusted data.
- You can mix: existing pickle rows remain readable after switching to json mode (reader tries JSON first, then pickle). New writes follow the current storage_mode.


## Storage mode selection (v1.8.8+)

Choose storage_mode based on requirements:

| Mode   | Pros | Cons | Best for |
|--------|------|------|----------|
| pickle | Arbitrary objects; faster for complex Python types | Security review needed; larger payload (Base64) | Internal trusted data, complex objects |
| json   | Human-readable; safer (no pickle) | Limited types; need custom encoding for sets | Config files, simple data interchange |

Switching considerations:
- Changing storage_mode only affects future writes; existing rows remain as they were.
- Reading order: JSON attempt -> pickle attempt -> fallback raw string.
- Migration to pure JSON: Optionally iterate over keys and reassign values while in json mode.

Example migration snippet:
```python
from dictsqlite import DictSQLite

db = DictSQLite('app.db', storage_mode='pickle')
# ... existing data stored
# Switch
db_json = DictSQLite('app.db', storage_mode='json')
for k in db_json.keys():
    v = db_json[k]  # auto-decoded (pickle or JSON)
    db_json[k] = v  # re-write in JSON format
```

Security note: json mode bypasses the Safe Unpickler (no pickle used). If you do not need arbitrary classes, prefer json.


## Keys, indexes, and data types

- Primary key: The key column is the primary key in the default schema. Lookups are fast by primary key.
- Types: With the default schema, key is TEXT. With a custom schema (e.g., key INTEGER), SQLite will store and return the key in that type. The value column is declared TEXT by default but will hold BLOB if you store encrypted bytes; SQLite is type-flexible.
- Indexes: The default schema only has the primary key index. Add any extra indexes you want using execute_custom after creating the table.
- Constraints: You can include NOT NULL, UNIQUE, CHECK, etc., in your custom schema. Just keep the key/value column names to use the dict-style API.


## Concurrency, transactions, and locking

- Worker queue: All DB operations are funneled through a single background worker thread. Methods that need a result (e.g., __getitem__, membership checks, keys, tables) wait for the result internally. Setters queue work and return quickly.
- Transactions: begin_transaction/commit_transaction/rollback_transaction place the respective commands onto the queue to preserve ordering. Changes are committed automatically when not in an explicit transaction.
- Locking: There is an optional conflict_resolver mode that also uses a file lock (via portalocker). This mode is experimental/deprecated and not needed in typical single-process use. The default worker is usually enough for thread-safety within a process.


## Security: safe deserialization and encryption

- Safe pickle loader: Values are unpickled using a safe_loads with an allow-list policy.
  - Allowed module prefixes (default): ("dictsqlite",) — only objects from this package are allowed by default, plus a small set of globals.
  - Allowed globals default includes: {"dictsqlite.modules.utils.ExpiringDict"}.
  - You can override policy and allow-lists via constructor args safe_pickle_policy, safe_pickle_allowed_module_prefixes, safe_pickle_allowed_builtins, safe_pickle_allowed_globals.
  - If unpickling fails under the policy, the library logs a warning and returns the raw string as a last resort.
- At-rest encryption (optional):
  - Set password and provide public/private key PEM paths. If key_create=True, DictSQLite will generate an RSA keypair and store both PEM files encrypted with AES using your password.
  - On write: the Base64 string is encrypted using RSA-OAEP with the loaded public key.
  - On read: ciphertext is decrypted using RSA-OAEP with the private key, then processed as above.

Note: Only the value field is encrypted by DictSQLite; key and other columns are in plaintext.


## Auto-synced proxy types

When you read a value back, DictSQLite may return proxy objects that auto-sync to the DB when mutated:

- RecursiveDict: If the stored value is a mapping (dict-like), you get a RecursiveDict. Assignments and deletions at any depth write back to the stored top-level dict. Example: `db['user']['profile']['age'] = 31` persists immediately.
  - Limitations: Non-dict containers nested under the dict (e.g., lists/sets inside) are returned as plain Python objects and will not auto-sync.
- DBSyncedList / DBSyncedSet: If the stored value is a top-level list or set, the object is wrapped so that mutations (append, add, remove, etc.) write back automatically.
  - Limitations: Lists/sets nested inside dicts are not wrapped and thus do not auto-sync. Reassign the parent value to persist nested changes, or store lists/sets at top level if you want auto-sync behavior.


## API reference

Constructor

```python
from dictsqlite import DictSQLite

db = DictSQLite(
  db_name='example.db',
  table_name='main',
  schema=None,
  conflict_resolver=False,
  journal_mode=None,
  lock_file=None,
  password=None,
  publickey_path='./public_keys.pem',
  privatekey_path='./private_keys.pem',
  version=1,
  key_create=False,
  # Safe pickle
  safe_pickle_policy=None,
  safe_pickle_allowed_module_prefixes=("dictsqlite",),
  safe_pickle_allowed_builtins=None,
  safe_pickle_allowed_globals={"dictsqlite.modules.utils.ExpiringDict"},
  storage_mode='pickle',  # or 'json'
)
```

storage_mode parameter:
- 'pickle' (default): Full feature set, Safe Unpickler on read, supports any pickle-able object.
- 'json': Only JSON-serializable (plus set). Safer & readable; non-serializable objects raise TypeError.

Core dictionary API

- db[key] = value: Insert or replace a value for key (pickle+Base64; optional RSA encryption).
- value = db[key]: Retrieve and decode the value; returns proxy types as described above.
- del db[key]: Delete a key.
- key in db: Membership check.
- repr(db): Returns a dict-like representation of the current table.

Tables and schema

- db.create_table(table_name: str | None = None, schema: str | None = None): Ensure a table exists (validates schema when provided).
- db.switch_table(new_table_name, schema=None): Switch the current table and create if needed.
- db.tables(): List all table names.
- db.clear_table(table_name: str | None = None): Delete all rows from a table.
- db.clear_db(): Drop all tables and recreate the default.

Transactions

- db.begin_transaction()
- db.commit_transaction()
- db.rollback_transaction()

Query helpers

- db.keys(table_name: str | None = None): List all keys from a table.
- db.execute_custom(query: str, params: tuple = ()): Execute a custom SQL through the worker queue.

Utilities

- dictsqlite.randomstrings(n: int) -> str: Random ASCII letters string.
- dictsqlite.expiring_dict(seconds: int) -> ExpiringDict: Dict with time-based expiry.


## Usage examples

Basic v1 usage

```python
from dictsqlite import DictSQLite

with DictSQLite('sample.db', journal_mode='WAL') as db:
    db['name'] = 'Alice'
    db['age'] = 30
    db['items'] = ['book', 'pen']  # top-level list: auto-synced proxy

    # Auto-sync for top-level list
    db['items'].append('notebook')  # immediately persisted

    # Dicts auto-sync at any depth
    db['profile'] = {'city': 'Tokyo', 'likes': {'music': True}}
    db['profile']['likes']['music'] = False  # persisted

    print('Keys:', db.keys())
    print('Name:', db['name'])
```

Multiple tables (v2)

```python
from dictsqlite import DictSQLite

with DictSQLite('sample_v2.db', version=2, journal_mode='WAL') as db:
    db.create_table('users')
    db.create_table('products')

    users = db['users']      # TableProxy
    products = db['products']

    users['u1'] = {'name': 'Taro', 'age': 30}
    products['p1'] = {'name': 'Laptop', 'price': 80000}

    # Auto-sync within dict
    users['u1']['age'] = 31

    print('All tables:', db.tables())
    print('Users:', users)
```

Custom schema

```python
from dictsqlite import DictSQLite

schema = '(key INTEGER PRIMARY KEY, value TEXT, updated_at TEXT)'

with DictSQLite('custom.db', schema=schema) as db:
    db[100] = {'product': 'Laptop'}
    db.execute_custom('CREATE INDEX IF NOT EXISTS ix_updated ON "main"(updated_at)')
    print(db[100])
```

At-rest encryption

```python
from dictsqlite import DictSQLite
from dictsqlite.modules import crypto

# One-time key pair creation (stores AES-encrypted PEM files)
crypto.key_create(password='secret',
                  pubkey_path='./public_keys.pem',
                  private_key_path='./private_keys.pem')

with DictSQLite('secure.db',
                password='secret',
                publickey_path='./public_keys.pem',
                privatekey_path='./private_keys.pem') as db:
    db['token'] = {'scopes': ['read', 'write']}
    print(db['token'])
```

Customizing safe pickle policy

```python
from dictsqlite import DictSQLite
from dictsqlite.modules.safe_pickle import SafePolicy

policy = SafePolicy()  # see module doc for knobs

with DictSQLite('policy.db',
                safe_pickle_policy=policy,
                safe_pickle_allowed_module_prefixes=('dictsqlite', 'myapp.models'),
                safe_pickle_allowed_globals={'dictsqlite.modules.utils.ExpiringDict', 'myapp.Type'}) as db:
    db['k'] = {'v': 1}
```

JSON mode example

```python
from dictsqlite import DictSQLite

with DictSQLite('settings.db', storage_mode='json') as db:
    db['feature_flags'] = {'new_ui': True, 'beta_users': ['u1', 'u2']}
    db['tags'] = {'alpha', 'beta'}  # set supported via custom encoder
    print(db['tags'])  # -> {'alpha', 'beta'}

    # Attempting to store a non-JSON-serializable object raises TypeError
    # db['obj'] = lambda x: x  # would fail
```

Mixed read example (existing pickle rows, new JSON rows):
```python
from dictsqlite import DictSQLite

# Existing database created with default pickle mode
with DictSQLite('mixed.db', storage_mode='pickle') as db:
    db['user'] = {'name': 'Alice'}

# Later switch to JSON mode
with DictSQLite('mixed.db', storage_mode='json') as db:
    print(db['user'])  # still readable (pickle fallback)
    db['config'] = {'theme': 'dark'}  # written as JSON
```


## Compatibility and migration notes

- Legacy JSON (pre-pickle rows): Still read first via JSON attempt.
- storage_mode='json': New writes are pure JSON; reads still attempt JSON then pickle so mixed databases work seamlessly.
- Column affinity: SQLite is flexible; declaring value as TEXT does not prevent storing BLOB when encryption is on (pickle mode ciphertext). JSON mode stores plaintext UTF-8 (or encrypted bytes if password set).
- conflict_resolver: Experimental/deprecated; typical apps do not need it. Prefer the default worker queue with WAL mode for multi-threaded reads.


## Troubleshooting

- I modified a list inside a dict and it didn’t persist: Only top-level lists/sets auto-sync. Reassign the parent dict or keep the list as a top-level value to get auto-sync.
- I get a safe unpickler warning: The object’s module/globals may not be allow-listed. Expand safe_pickle_allowed_* parameters, or store a simpler type.
- Schema validation failed: Ensure schema is a single CREATE TABLE column list without semicolons. Keep key and value columns for dict-style API.
- Performance tips: Enable journal_mode='WAL', avoid excessively large single values, and consider indexing additional columns you add to custom schemas.
