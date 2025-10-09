# __init__.py ビルド問題の修正概要

## 問題

Rust でビルドした際に、`__init__.py` がビルドに含まれていませんでした。これは、Rust モジュールの名前が Python パッケージ名と競合していたためです。

## 原因

1. **Rust モジュール名の競合**: `src/lib.rs` で `#[pymodule] fn dictsqlite(...)` と定義されており、これが `dictsqlite` という名前のネイティブモジュールを作成していました。

2. **Python パッケージ構造の問題**: Python ソースファイル（`__init__.py`、`modules/`）がプロジェクトルートに配置されていたため、maturin が正しく認識できませんでした。

3. **maturin 設定の不足**: `pyproject.toml` に Python ソースファイルの場所を指定する設定がありませんでした。

## 解決策

以下の3つの変更を実施しました:

### 1. Python ソースファイルの再配置

```
dictsqlite/
├── __init__.py              <- 削除
├── modules/                 <- 削除
│   ├── __init__.py
│   └── safe_pickle.py
└── python/                  <- 新規作成
    └── dictsqlite/
        ├── __init__.py      <- 移動
        └── modules/         <- 移動
            ├── __init__.py
            └── safe_pickle.py
```

### 2. pyproject.toml の更新

```toml
[tool.maturin]
# Python ソースファイルが python/ サブディレクトリにあることを指定
python-source = "python"
# ネイティブ拡張モジュールをサブモジュールとして配置
module-name = "dictsqlite._native"
```

### 3. Rust モジュール名の変更

`src/lib.rs` の最後:
```rust
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {  // dictsqlite -> _native に変更
    m.add_class::<DictSQLiteV4>()?;
    m.add_class::<AsyncDictSQLite>()?;
    m.add_class::<TableProxy>()?;
    m.add_class::<AsyncTableProxy>()?;
    Ok(())
}
```

### 4. __init__.py のインポート更新

```python
# 変更前
from dictsqlite import DictSQLiteV4 as _NativeDictSQLiteV4
from dictsqlite import AsyncDictSQLite as _NativeAsyncDictSQLite

# 変更後
from dictsqlite._native import DictSQLiteV4 as _NativeDictSQLiteV4
from dictsqlite._native import AsyncDictSQLite as _NativeAsyncDictSQLite
```

## 動作確認

以下のコマンドで動作を確認できます:

```bash
# ビルド
cd dictsqlite_v2/dictsqlite
bash build.sh

# Python での動作確認
python3 << 'EOF'
import dictsqlite
import tempfile
import os

# データベース作成
db_path = os.path.join(tempfile.mkdtemp(), 'test.db')
db = dictsqlite.DictSQLiteV4(db_path)

# データ追加
db['key1'] = 'value1'
db['key2'] = 'value2'

# 辞書として出力
print(dict(db.items()))
# 出力: {'key1': 'value1', 'key2': 'value2'}
EOF
```

## 結果

✅ `__init__.py` がビルドに正しく含まれるようになりました  
✅ モジュールのインポートが正常に動作します  
✅ データベースを作成して辞書として操作できます  
✅ `build.sh` でビルドして、モジュールを import して db を作り print したものが db の中身を返す dict として動作します

## 参考資料

- [Maturin Mixed Python/Rust Projects](https://www.maturin.rs/project_layout.html#mixed-pythonrust-projects)
- [PyO3 Module Documentation](https://pyo3.rs/latest/module.html)
