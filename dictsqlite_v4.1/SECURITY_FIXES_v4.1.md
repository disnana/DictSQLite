# DictSQLite v4.1 - セキュリティ修正版

## 概要

DictSQLite v4.1は、v4.0で検出されたセキュリティ脆弱性を修正したバージョンです。
OSS セキュリティチェックツール（cargo audit）を使用して脆弱性を検証し、必要な修正を実施しました。

## 修正されたセキュリティ脆弱性

### RUSTSEC-2025-0020: PyO3 バッファオーバーフロー脆弱性

**深刻度**: 高

**影響**: 
- pyo3 0.20.3 の `PyString::from_object` 関数にバッファオーバーフローのリスクが存在
- 悪意のある Python 文字列データにより、メモリ破壊やクラッシュが発生する可能性

**修正内容**:
- pyo3 を 0.20.3 から 0.24.1 にアップグレード
- pyo3 0.24 の新しい Bound API に対応するためコードを更新

**変更されたファイル**:
- `Cargo.toml`: pyo3 のバージョンを `0.20` → `0.24.1` に更新
- `src/lib.rs`: Bound API を使用するように更新
  - `Bound<'_, PyDict>` を使用した関数シグネチャの更新
  - PyModule の新しい API に対応

## セキュリティ検証結果

### Cargo Audit

```bash
$ cargo audit
    Scanning Cargo.lock for vulnerabilities (199 crate dependencies)
```

**結果**: ✅ 脆弱性なし

### ビルドとテスト

```bash
$ cargo build
    Finished `dev` profile [unoptimized + debuginfo] target(s)
```

**結果**: ✅ ビルド成功

```bash
$ cargo test
running 7 tests
test result: ok. 7 passed; 0 failed; 0 ignored
```

**結果**: ✅ 全テスト成功

## API 変更

pyo3 0.24 へのアップグレードに伴い、以下の API 変更があります：

### Python から使用する場合

**変更なし** - Python API は完全に互換性があります。

### Rust から使用する場合

1. **PyModule の変更**:
   ```rust
   // v4.0 (旧)
   #[pymodule]
   fn dictsqlite_v4(_py: Python, m: &PyModule) -> PyResult<()> {
       // ...
   }
   
   // v4.1 (新)
   #[pymodule]
   fn dictsqlite_v4(m: &Bound<'_, PyModule>) -> PyResult<()> {
       // ...
   }
   ```

2. **PyDict の変更**:
   ```rust
   // v4.0 (旧)
   fn bulk_insert(&self, items: &PyDict) -> PyResult<()> {
       for (key, value) in items.iter() {
           // ...
       }
   }
   
   // v4.1 (新)
   fn bulk_insert(&self, items: Bound<'_, PyDict>) -> PyResult<()> {
       for (key, value) in items.iter() {
           // ...
       }
   }
   ```

## セキュリティ機能（v4.0 から継承）

v4.1 は v4.0 のすべてのセキュリティ機能を維持しています：

- ✅ AES-256-GCM 暗号化（認証付き暗号化）
- ✅ PBKDF2-HMAC-SHA256 による鍵導出（100,000 反復）
- ✅ Safe Pickle バリデーション（危険な pickle opcode の検出）
- ✅ SQL インジェクション対策（パラメータ化クエリ）

## 推奨事項

1. **即座のアップグレード**: v4.0 を使用している場合は、v4.1 へのアップグレードを強く推奨します
2. **定期的なセキュリティ監査**: `cargo audit` を定期的に実行してください
3. **依存関係の更新**: セキュリティパッチがリリースされた際は速やかに更新してください

## バージョン情報

- **バージョン**: 4.1.0
- **リリース日**: 2025年
- **ライセンス**: MIT
- **著者**: Disnana <support@disnana.com>

## 参考資料

- [RUSTSEC-2025-0020](https://rustsec.org/advisories/RUSTSEC-2025-0020)
- [PyO3 Migration Guide](https://pyo3.rs/main/migration)
- [Cargo Audit](https://github.com/rustsec/rustsec/tree/main/cargo-audit)

## 謝辞

この脆弱性の報告と修正にご協力いただいたすべての方々に感謝いたします。
