# DictSQLite ネイティブ拡張機能

## 概要

DictSQLiteは、パフォーマンスを大幅に向上させるため、Rustで書かれたオプションのネイティブ拡張機能をサポートするようになりました。ネイティブ拡張機能は、完全なAPI互換性を維持しながら、コア操作を10〜100倍高速化します。

## 機能

- **高性能**: 純粋なPython実装より10〜100倍高速
- **メモリ効率**: ネイティブRustデータ構造による最適化されたメモリ使用量
- **スレッドセーフ**: Rustの安全性保証により構築
- **ランタイム依存なし**: 静的コンパイル、追加の依存関係なし
- **自動フォールバック**: ネイティブ拡張機能が利用できない場合、純粋なPythonにシームレスにフォールバック
- **完全な互換性**: 既存のDictSQLiteコードと100% API互換

## インストール

### オプション1: ビルド済みホイールを使用（推奨）

```bash
pip install dictsqlite
```

一般的なプラットフォーム（Linux、macOS、Windows）のx86_64向けにビルド済みホイールが利用可能になる予定です。

### オプション2: ソースからビルド

ネイティブ拡張機能を自分でビルドする場合:

1. https://rustup.rs/ からRustをインストール

2. リポジトリをクローン:
```bash
git clone https://github.com/disnana/DictSQLite.git
cd DictSQLite
```

3. ネイティブ拡張機能をビルド:
```bash
./build_native.sh
```

または手動で:
```bash
pip install maturin
cd dictsqlite_native
maturin build --release
pip install target/wheels/*.whl
```

## 使用方法

ネイティブ拡張機能はユーザーに対して透過的です。通常通りDictSQLiteを使用するだけです:

```python
from dictsqlite import DictSQLite

# ネイティブ拡張機能が利用可能な場合、自動的に使用されます
db = DictSQLite('mydb.db')
db['key'] = 'value'
```

### ネイティブ拡張機能の状態確認

```python
from dictsqlite.native_wrapper import is_native_available

if is_native_available():
    print("🚀 高性能ネイティブRust拡張機能を使用中")
else:
    print("⚠️ 純粋なPythonフォールバックを使用中")
```

## パフォーマンス比較

`dictsqlite-fastest/beta/investigate_v2_speedup.py`のベンチマークに基づく:

| 操作 | 純粋なPython | ネイティブRust | 高速化 |
|------|--------------|----------------|--------|
| キャッシュ読み込み | 1M ops/sec | 50-100M ops/sec | **50-100倍** |
| キャッシュ書き込み | 800K ops/sec | 40-80M ops/sec | **50-100倍** |
| SQLite読み込み | 100K ops/sec | 2-5M ops/sec | **20-50倍** |
| SQLite書き込み | 50K ops/sec | 1-2M ops/sec | **20-40倍** |
| バルクインサート | 200K ops/sec | 5-10M ops/sec | **25-50倍** |

*注意: 実際のパフォーマンスは、ハードウェア、データサイズ、ワークロードパターンによって異なる場合があります。*

## アーキテクチャ

ネイティブ拡張機能は2つの主要コンポーネントで構成されています:

### 1. NativeCache
- Rustの`lru`クレートを使用した高性能LRUキャッシュ
- 可能な限りロックフリーの読み取り操作
- 最小限の競合でスレッドセーフ

### 2. NativeSQLite  
- `rusqlite`を使用した最適化されたSQLiteラッパー
- プリペアドステートメントのキャッシング
- バッチ操作の最適化
- コネクションプールのサポート

## 技術的詳細

### なぜRust？

- **パフォーマンス**: 手動メモリ管理なしでC/C++に匹敵
- **安全性**: ガベージコレクションなしでメモリ安全性を実現
- **並行性**: Rustの所有権モデルによる安全な並行処理
- **相互運用性**: PyO3による優れたPython統合
- **ツール**: Cargoによる堅牢なビルドと依存関係管理

### 検討した代替案

`investigate_v2_speedup.py`で述べられているように、以下を検討しました:
- ✅ **Rust**（選択）: 最高のパフォーマンス/安全性のトレードオフ、優れたPython相互運用性
- ❌ Cython: 良好なパフォーマンスだが安全性が低く、保守が困難
- ❌ C++: 優れたパフォーマンスだが手動メモリ管理が必要
- ❌ Go: 良好なパフォーマンスだがランタイムオーバーヘッドが大きい
- ❌ Node.js: CPU集約的な操作には不適切

## 開発

### 開発用ビルド

```bash
cd dictsqlite_native
maturin develop
```

### テストの実行

```bash
python -m pytest tests/ -v
```

### ベンチマーク

```bash
python dictsqlite-fastest/beta/performance_benchmark.py
```

## トラブルシューティング

### ネイティブ拡張機能が読み込まれない

ネイティブ拡張機能の読み込みに失敗した場合:

1. Pythonのバージョンを確認（Python 3.9+が必要）
2. アーキテクチャの互換性を確認（x86_64、aarch64）
3. ログでエラーメッセージを確認
4. 純粋なPythonフォールバックが自動的に使用されます

### ビルドの問題

ソースからのビルドに失敗した場合:

1. Rustがインストールされていることを確認: `rustc --version`
2. Rustを更新: `rustup update`
3. ビルド依存関係をインストール（プラットフォームによって異なる）
4. 不足しているシステムライブラリのエラーメッセージを確認

## 貢献

ネイティブ拡張機能への貢献を歓迎します！以下を確認してください:

- コードがRustのベストプラクティスに従っている
- すべてのテストが合格
- パフォーマンスの改善がベンチマークされている
- 変更がAPI互換性を維持している

## ライセンス

ネイティブ拡張機能は、DictSQLiteと同じMITライセンスでライセンスされています。

## 将来の改善

計画されている改善:
- [ ] async/awaitサポート
- [ ] バルク操作のSIMD最適化
- [ ] より良いメモリ効率のためのカスタムアロケータ
- [ ] 可能な限りゼロコピーシリアライゼーション
- [ ] アクセスパターンに基づく高度なプリフェッチング
