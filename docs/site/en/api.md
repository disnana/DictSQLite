---
outline: [2, 3]
---

# API Reference

Public ValidKit APIs and validator factories.

## Top-level functions

### `validate`

```python
validate(data: Any, schema: Any, partial: bool = False, base: Any = None, migrate: Optional[Dict[str, Any]] = None, collect_errors: bool = False) -> Union[Any, ForwardRef('ValidationResult')]
```

Validates data against a schema. With `collect_errors=True`, it returns `ValidationResult` and gathers multiple errors.

### `compile`

```python
compile(schema: Any) -> validkit.compiled.CompiledSchema
```

Precompiles a schema and returns `CompiledSchema` for repeated validation. Core validators, lists, and dictionaries are optimized with generated Python code.

### `Schema`

```python
Schema(schema: Any) -> None
```

A thin typing helper. Combining `Schema[T]` with `TypedDict` helps IDEs infer validated return shapes.

## Validator factories

| Factory | Class | Validates |
|---|---|---|
| `v.str()` | `StringValidator` | 文字列 / string |
| `v.int()` | `NumberValidator` | 整数 / integer |
| `v.float()` | `NumberValidator` | 浮動小数点 / float |
| `v.bool()` | `BoolValidator` | 真偽値 / boolean |
| `v.list(schema)` | `ListValidator` | リスト・タプル / list and tuple |
| `v.dict(key_type, schema)` | `DictValidator` | 辞書 / dict |
| `v.oneof(values)` | `OneOfValidator` | 候補値 / allowed values |
| `v.instance(type)` | `InstanceValidator` | 任意クラス / custom instance |
| `v.datetime()` | `DateTimeValidator` | 日時 / datetime |
| `v.uuid()` | `UUIDValidator` | UUID |
| `v.mac()` | `MACValidator` | MAC address |
| `v.sid()` | `SIDValidator` | Windows SID |
| `v.hwid()` | `HWIDValidator` | Hardware ID |
| `v.ip()` | `IPValidator` | IP address |
| `v.snowflake()` | `SnowflakeValidator` | Discord Snowflake |
| `v.version()` | `VersionValidator` | Semantic Versioning |
| `v.url()` | `URLValidator` | URL |
| `v.enum(enum_cls)` | `EnumValidator` | Enum |

## Common chain methods

| Method | Purpose |
|---|---|
| `.optional()` | Allow missing values and `None` |
| `.default(value)` | Fill missing values |
| `.coerce()` | Coerce compatible values |
| `.custom(func)` | Add validation or transformation |
| `.when(func)` | Conditional requirement based on root data |
| `.env(key, decryptor=None)` | Environment fallback |
| `.secret()` | Mask error values |
| `.error_msg(text)` | Override error messages |
| `.examples(list)` | Examples for docs and sample generation |
| `.description(text)` | Field description metadata |

## Base validator methods

`coerce`, `custom`, `default`, `description`, `env`, `error_msg`, `examples`, `optional`, `secret`, `validate`, `when`

## Return and error types

- `ValidationError`: Represents a single validation failure. It exposes `message`, `path`, and `value`.
- `ValidationResult`: Returned when collecting multiple errors. It exposes `data` and `errors`.
- `CompiledSchema`: Returned by `compile(schema)`. Use `.validate(...)` to validate data.
