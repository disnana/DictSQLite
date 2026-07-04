---
outline: [2, 3]
---

# API リファレンス

ValidKit の公開 API と主要バリデータの一覧です。

## Top-level functions

### `validate`

```python
validate(data: Any, schema: Any, partial: bool = False, base: Any = None, migrate: Optional[Dict[str, Any]] = None, collect_errors: bool = False) -> Union[Any, ForwardRef('ValidationResult')]
```

データとスキーマを受け取り、検証済みデータを返します。`collect_errors=True` の場合は `ValidationResult` を返し、複数のエラーをまとめて確認できます。

### `compile`

```python
compile(schema: Any) -> validkit.compiled.CompiledSchema
```

スキーマを事前コンパイルし、繰り返し検証向けの `CompiledSchema` を返します。基本型・リスト・辞書・一部の組み込みバリデータは生成コードで高速化されます。

### `Schema`

```python
Schema(schema: Any) -> None
```

型補完を助ける薄いラッパーです。`Schema[T]` と `TypedDict` を組み合わせると IDE が戻り値の形を推論しやすくなります。

## Validator factories

| ファクトリ | クラス | 検証対象 |
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

| メソッド | 用途 |
|---|---|
| `.optional()` | 欠損値と `None` を許容 |
| `.default(value)` | 欠損時の値を補完 |
| `.coerce()` | 可能な範囲で型変換 |
| `.custom(func)` | 追加の検証・変換 |
| `.when(func)` | 親データに基づく条件付き必須 |
| `.env(key, decryptor=None)` | 環境変数フォールバック |
| `.secret()` | エラー時の値をマスク |
| `.error_msg(text)` | エラーメッセージを上書き |
| `.examples(list)` | サンプル生成・ドキュメント用の例 |
| `.description(text)` | フィールド説明 |

## Base validator methods

`coerce`, `custom`, `default`, `description`, `env`, `error_msg`, `examples`, `optional`, `secret`, `validate`, `when`

## Return and error types

- `ValidationError`: 単一エラーを表します。`message`, `path`, `value` を持ちます。
- `ValidationResult`: 複数エラー収集時の戻り値です。`data` と `errors` を持ちます。
- `CompiledSchema`: `compile(schema)` の戻り値です。`.validate(...)` で検証します。
