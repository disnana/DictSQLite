_C=True
_B=False
_A=None
import random,sqlite3,threading,queue,secrets,string,portalocker
__version__='1.3.3'
def randomstrings(n):return''.join(secrets.choice(string.ascii_letters)for A in range(n))
class DictSQLite_beta:
	def __init__(A,db_name,table_name='main',schema=_A,conflict_resolver=_B,journal_mode=_A,lock_file=_A):
		D=lock_file;C=journal_mode;B=db_name;A.db_name=B;A.table_name=table_name;A.conn=sqlite3.connect(B,check_same_thread=_B);A.cursor=A.conn.cursor();A.in_transaction=_B
		if D is _A:A.lock_file=f"{B}.lock"
		else:A.lock_file=D
		A.operation_queue=queue.Queue();A.conflict_resolver=conflict_resolver
		if A.conflict_resolver:A.worker_thread=threading.Thread(target=A._process_queue_conflict_resolver);A.worker_thread.daemon=_C;A.worker_thread.start()
		else:A.worker_thread=threading.Thread(target=A._process_queue);A.worker_thread.daemon=_C;A.worker_thread.start()
		A.create_table(schema=schema)
		if not C is _A:A.conn.execute(f"PRAGMA journal_mode={C};")
	def _process_queue(B):
		while _C:
			D,E,F,A=B.operation_queue.get()
			try:
				G=D(*E,**F)
				if A is not _A:A.put(G)
			except Exception as C:
				print(f"An error occurred while processing the queue: {C}")
				if A is not _A:A.put(C)
			finally:B.operation_queue.task_done()
	def _process_queue_conflict_resolver(A):
		while _C:
			D,E,F,B=A.operation_queue.get()
			with open(A.lock_file,'w')as G:
				portalocker.lock(G,portalocker.LOCK_EX);A._process_queue()
				try:
					H=D(*E,**F)
					if B is not _A:B.put(H)
				except Exception as C:
					print(f"An error occurred while processing the queue: {C}")
					if B is not _A:B.put(C)
				finally:A.operation_queue.task_done()
	def create_table(B,table_name=_A,schema=_A):
		C=table_name;A=schema
		if not C is _A:B.table_name=C
		A=A if A else'(key TEXT PRIMARY KEY, value TEXT)';D=f"CREATE TABLE IF NOT EXISTS {B.table_name} {A}"
		if not B._validate_schema(A):raise ValueError(f"Invalid schema provided: {A}")
		B.operation_queue.put((B._execute,(D,),{},_A))
	def _validate_schema(A,schema):
		'一時的なテーブルを作成してスキーマを検証します。'
		try:
			def C():A.cursor.execute("\n                        SELECT name FROM sqlite_master WHERE type='table'\n                    ");B=A.cursor.fetchall();return[A[0]for A in B]
			B=randomstrings(random.randint(1,30))
			while B in C():B=randomstrings(random.randint(1,30))
			A.cursor.execute(f"CREATE TABLE {B} {schema}");A.cursor.execute(f"DROP TABLE {B}");return _C
		except Exception as D:print(f"Schema validation failed: {D}");return _B
	def _execute(A,query,params=()):
		A.cursor.execute(query,params)
		if not A.in_transaction:A.conn.commit()
	def __setitem__(A,key,value):A.operation_queue.put((A._execute,(f"\n            INSERT OR REPLACE INTO {A.table_name} (key, value)\n            VALUES (?, ?)\n        ",(key,value)),{},_A))
	def __getitem__(B,key):
		C=queue.Queue();B.operation_queue.put((B._fetchone,(f"\n            SELECT value FROM {B.table_name} WHERE key = ?\n        ",(key,)),{},C));A=C.get()
		if isinstance(A,Exception):raise A
		if A is _A:raise KeyError(f"Key {key} not found.")
		return A[0]
	def _fetchone(A,query,params=()):A.cursor.execute(query,params);return A.cursor.fetchone()
	def __delitem__(A,key):A.operation_queue.put((A._execute,(f"\n            DELETE FROM {A.table_name} WHERE key = ?\n        ",(key,)),{},_A))
	def __contains__(A,key):
		C=queue.Queue();A.operation_queue.put((A._fetchone,(f"\n            SELECT 1 FROM {A.table_name} WHERE key = ?\n        ",(key,)),{},C));B=C.get()
		if isinstance(B,Exception):raise B
		return B is not _A
	def __repr__(A):
		C=queue.Queue();A.operation_queue.put((A._fetchall,(f"\n            SELECT key, value FROM {A.table_name}\n        ",),{},C));B=C.get()
		if isinstance(B,Exception):raise B
		return str(dict(B))
	def _fetchall(A,query,params=()):A.cursor.execute(query,params);return A.cursor.fetchall()
	def keys(A):
		C=queue.Queue();A.operation_queue.put((A._fetchall,(f"\n            SELECT key FROM {A.table_name}\n        ",),{},C));B=C.get()
		if isinstance(B,Exception):raise B
		return[A[0]for A in B]
	def begin_transaction(A):A.operation_queue.put((A._begin_transaction,(),{},_A))
	def _begin_transaction(A):A.conn.execute('BEGIN TRANSACTION');A.in_transaction=_C
	def commit_transaction(A):A.operation_queue.put((A._commit_transaction,(),{},_A))
	def _commit_transaction(A):
		try:
			if A.in_transaction:A.conn.execute('COMMIT')
		finally:A.in_transaction=_B
	def rollback_transaction(A):A.operation_queue.put((A._rollback_transaction,(),{},_A))
	def _rollback_transaction(A):
		try:
			if A.in_transaction:A.conn.execute('ROLLBACK')
		finally:A.in_transaction=_B
	def switch_table(A,new_table_name,schema=_A):A.operation_queue.put((A._switch_table,(new_table_name,schema),{},_A));A.operation_queue.join()
	def _switch_table(A,new_table_name,schema):A.table_name=new_table_name;A.create_table(schema)
	def has_key(A,key):return key in A
	def clear_db(A):A.operation_queue.put((A._clear_db,(),{},_A));A.operation_queue.join()
	def _clear_db(A):
		A.cursor.execute(f"\n            SELECT name FROM sqlite_master WHERE type='table'\n        ");B=A.cursor.fetchall()
		for C in B:A.cursor.execute(f"DROP TABLE IF EXISTS {C[0]}")
		if not A.in_transaction:A.conn.commit()
		A.table_name='main';A.create_table()
	def tables(B):
		C=queue.Queue();B.operation_queue.put((B._fetchall,(f"\n            SELECT name FROM sqlite_master WHERE type='table'\n        ",),{},C));A=C.get()
		if isinstance(A,Exception):raise A
		return[A[0]for A in A]
	def clear_table(A,table_name=_A):
		B=table_name
		if B is _A:B=A.table_name
		A.operation_queue.put((A._execute,(f"\n            DELETE FROM {B}\n        ",),{},_A))
	def __enter__(A):return A
	def __exit__(A,exc_type,exc_val,exc_tb):A.close()
	def close(A):A.operation_queue.join();A.conn.close()
