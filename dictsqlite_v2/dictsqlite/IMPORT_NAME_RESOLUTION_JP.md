# インポート名の問題解決 (Import Name Resolution)

## 問題の概要

**ディレクトリ構造:** `dictsqlite_v2/dictsqlite/`  
**期待されるインポート:** `from dictsqlite import DictSQLiteV4`  
**問題:** `dictsqlite`ではなく`dictsqlite_v2`としてビルドされるリスク

## 原因

Pythonパッケージ名(wheelファイル名)は**`pyproject.toml`の`[project]`セクションの`name`フィールド**で決定されます。

ディレクトリ構造が`dictsqlite_v2/dictsqlite/`なので、どちらの名前を使うべきか混乱が生じる可能性があります：
- ディレクトリ名: `dictsqlite_v2`(親) / `dictsqlite`(現在)
- Pythonモジュール名(Rustの`#[pymodule]`から): `dictsqlite`
- 望ましいパッケージ名: `dictsqlite`

もし`pyproject.toml`が`name = "dictsqlite_v2"`と設定されていた場合(親ディレクトリ名に合わせて)、wheelは`dictsqlite_v2-x.x.x.whl`という名前になり、内部のモジュールは`dictsqlite`のままなので、インポート時に混乱が生じます。

## 解決策

### 現在の設定(正しい)

**pyproject.toml:**
```toml
[project]
name = "dictsqlite"  # ✅ Pythonモジュール名と一致させる必要があります
```

**Cargo.toml:**
```toml
[package]
name = "dictsqlite"

[lib]
name = "dictsqlite"

[package.metadata.maturin]
name = "dictsqlite"  # 一貫性のため(maturin >= 0.14では冗長)
```

**src/lib.rs:**
```rust
#[pymodule]
fn dictsqlite(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // モジュール名は "dictsqlite"
}
```

### 重要なポイント

1. **`pyproject.toml`の`[project] name`**がwheelパッケージ名を制御します
2. **Rustの`#[pymodule]`属性**がPythonモジュール名を制御します
3. **両方が一致する必要があります**(`from dictsqlite import ...`が動作するため)
4. **`[package.metadata.maturin] name`**は後方互換性のために保持されていますが、maturin >= 0.14では冗長です

### ビルド結果

✅ **正しい:**
- Wheel: `dictsqlite-2.0.4-cp39-abi3-linux_x86_64.whl`
- インポート: `from dictsqlite import DictSQLiteV4`

❌ **間違い**(もし`pyproject.toml`が`name = "dictsqlite_v2"`だった場合):
- Wheel: `dictsqlite_v2-2.0.4-cp39-abi3-linux_x86_64.whl`
- インポート試行: `from dictsqlite_v2 import ...` ← 失敗する！
- 実際の内部モジュール: `dictsqlite/` ← 不一致！

## 検証方法

設定を検証するには:

```bash
# Wheelをビルド
maturin build --release

# Wheel名を確認(dictsqlite-*.whlであるべき。dictsqlite_v2-*.whlではない)
ls target/wheels/

# インストールとテスト
pip install target/wheels/dictsqlite-*.whl
python -c "from dictsqlite import DictSQLiteV4; print('✅ インポート成功')"
```

## なぜディレクトリが`dictsqlite_v2`なのか

親ディレクトリ`dictsqlite_v2`は以下の目的で使用されています:
- **リポジトリの整理**: v1実装とv2実装を分離
- **開発の明確化**: これがv2コードベースであることを示す
- **パッケージ名ではありません**

パッケージ名は`dictsqlite`のままにする理由:
- **ユーザーの簡便性**: バージョン間で一貫したインポートパス
- **後方互換性**: v1と同じインポートパス
- **PyPI命名**: PyPIで同じパッケージ名を維持

## 予防策

この問題を防ぐために:
1. ✅ 常に`pyproject.toml [project] name = "dictsqlite"`を維持
2. ✅ `Cargo.toml [package.metadata.maturin] name = "dictsqlite"`を維持
3. ✅ `#[pymodule] fn dictsqlite`が一致していることを確認
4. ⚠️ これらをディレクトリ名`dictsqlite_v2`に合わせて変更しないでください

## 状態

**解決日:** 2025年10月9日  
**状態:** ✅ 解決済み（設定が正しいことを確認）

## 追加ドキュメント

詳細な英語ドキュメントは`IMPORT_NAME_RESOLUTION.md`を参照してください。
