# 問題解決の概要

## 問題のタイトル
importが予定と違う

## 問題の説明
dictsqlite_v2/dictsqlite のimportがdictsqliteになるはずが、なぜかdictsqlite_v2としてビルドされる。原因の特定と解決がしたい。

## 根本原因の分析

Pythonのwheelパッケージ名は、ディレクトリ名ではなく、**`pyproject.toml`の`[project]`セクションの`name`フィールド**で決定されます。

### ディレクトリ構造
```
dictsqlite_v2/          ← 親ディレクトリ（整理のためのみ）
└── dictsqlite/         ← 実際のパッケージディレクトリ
    ├── Cargo.toml
    ├── pyproject.toml
    └── src/
        └── lib.rs
```

### 命名の混乱リスク

ディレクトリ構造が`dictsqlite_v2/dictsqlite/`なので、どの名前を使うべきか混乱が生じる可能性があります：
- ディレクトリ名: `dictsqlite_v2`（親）または`dictsqlite`（現在）
- Pythonモジュール名（Rustから）: `dictsqlite`
- 望ましいパッケージ名: `dictsqlite`

もし`pyproject.toml`が`name = "dictsqlite_v2"`と設定されていた場合（親ディレクトリ名に合わせて）、wheelは`dictsqlite_v2-x.x.x.whl`という名前になり、混乱が生じます。

## 現在の設定（正しいことを確認済み）

### pyproject.toml
```toml
[project]
name = "dictsqlite"  # ✅ 正しい - モジュール名と一致
```

### Cargo.toml
```toml
[package]
name = "dictsqlite"

[lib]
name = "dictsqlite"

[package.metadata.maturin]
name = "dictsqlite"  # ✅ 正しい - 一貫性のため
```

### src/lib.rs
```rust
#[pymodule]
fn dictsqlite(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // ✅ 正しい - モジュール名は "dictsqlite"
}
```

## 実施した解決アクション

### 1. ドキュメント
- ✅ `pyproject.toml`に詳細なコメントを追加
- ✅ `Cargo.toml`に詳細なコメントを追加
- ✅ `IMPORT_NAME_RESOLUTION.md`を作成（英語ドキュメント）
- ✅ `IMPORT_NAME_RESOLUTION_JP.md`を作成（日本語ドキュメント）

### 2. バリデーション
- ✅ `validate_package_name.py`スクリプトを作成
  - `pyproject.toml [project] name = "dictsqlite"`を検証
  - `Cargo.toml [package] name = "dictsqlite"`を検証
  - `Cargo.toml [lib] name = "dictsqlite"`を検証
  - `Cargo.toml [package.metadata.maturin] name = "dictsqlite"`を検証
  - ビルドされたwheelの名前が`dictsqlite-`で始まることを検証

### 3. ビルドスクリプトの統合
- ✅ `build.sh`にビルド前のバリデーションを追加
- ✅ `build_production.sh`にビルド前のバリデーションを追加
- ✅ `build_production.sh`の不正なインポートパスを修正（`dictsqlite_v4` → `dictsqlite`）

### 4. 検証
- ✅ Wheelが正しくビルドされる: `dictsqlite-2.0.4-cp39-abi3-manylinux_2_34_x86_64.whl`
- ✅ インポートが正しく動作: `from dictsqlite import DictSQLiteV4`
- ✅ すべてのバリデーションチェックがパス
- ✅ スモークテストがパス

## 重要な学び

1. **主要な制御**: `pyproject.toml [project] name`がwheelパッケージ名を決定する
2. **モジュール名**: Rustの`#[pymodule]`属性がPythonモジュール名を決定する
3. **一貫性が必要**: インポートが正しく動作するために、両方が一致する必要がある
4. **ディレクトリ名**: 親ディレクトリ名（`dictsqlite_v2`）は整理のためであり、パッケージ名ではない
5. **バリデーション**: 自動バリデーションにより、誤設定を防ぐ

## 予防策

この問題を今後防ぐために：
1. ✅ `validate_package_name.py`スクリプトがビルド前に毎回実行される
2. ✅ 設定ファイルに明確なコメントで名前の変更に対して警告
3. ✅ ドキュメントで命名構造を説明
4. ⚠️ `pyproject.toml [project] name`をディレクトリ名に合わせて変更**しないでください**

## テスト

### ビルドテスト
```bash
cd dictsqlite_v2/dictsqlite
./build.sh
```

期待される出力：
- ✅ バリデーションチェックがパス
- ✅ Wheel: `dictsqlite-2.0.4-cp39-abi3-manylinux_2_34_x86_64.whl`

### インポートテスト
```python
from dictsqlite import DictSQLiteV4, AsyncDictSQLite
```

期待される結果：✅ インポートが成功する

## 変更されたファイル

1. `dictsqlite_v2/dictsqlite/pyproject.toml` - 明確なコメントを追加
2. `dictsqlite_v2/dictsqlite/Cargo.toml` - 明確なコメントを追加
3. `dictsqlite_v2/dictsqlite/build.sh` - バリデーションステップを追加
4. `dictsqlite_v2/dictsqlite/build_production.sh` - バリデーションステップを追加、インポートパスを修正

## 作成されたファイル

1. `dictsqlite_v2/dictsqlite/IMPORT_NAME_RESOLUTION.md` - 英語ドキュメント
2. `dictsqlite_v2/dictsqlite/IMPORT_NAME_RESOLUTION_JP.md` - 日本語ドキュメント
3. `dictsqlite_v2/dictsqlite/validate_package_name.py` - バリデーションスクリプト
4. `dictsqlite_v2/dictsqlite/RESOLUTION_SUMMARY.md` - 英語版の概要
5. `dictsqlite_v2/dictsqlite/RESOLUTION_SUMMARY_JP.md` - このファイル（日本語版の概要）

## 結論

設定はすでに正しかったのですが、ドキュメントとバリデーションが不足していました。以下により問題が解決されました：
- 設定がなぜこうでなければならないかをドキュメント化
- 今後の誤設定を防ぐためのバリデーションを追加
- ビルドスクリプトを修正して正しいインポートパスを使用

**ステータス: ✅ 解決済み**

---

日付: 2025年10月9日
解決者: GitHub Copilot
