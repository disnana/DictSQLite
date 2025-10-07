# DictSQLite v4.2 Performance Testing Guide

## 概要

このディレクトリには、DictSQLite v4.2の包括的なパフォーマンステストスイートが含まれています。

## テストの特徴

### 📊 包括的なテストカバレッジ

1. **非同期書き込みバッファリング** - 300倍高速化の検証
2. **同期WriteThrough バッチ書き込み** - 43倍高速化の検証
3. **Persistモード比較** - Memory/Lazy/WriteThrough
4. **暗号化オーバーヘッド** - AES-256-GCM
5. **Safe Pickle検証** - オーバーヘッド測定
6. **バッチ操作** - batch_get/batch_set
7. **混合読み書きパターン** - 実世界のシナリオ
8. **機能組み合わせ** - 全機能の統合テスト

### 🔧 テストパラメータ

各テストは以下のバリエーションでテストされます：
- バッファサイズ: 1, 10, 50, 100, 200
- 暗号化: あり/なし
- Safe Pickle: あり/なし
- Persistモード: memory, lazy, writethrough

## 使用方法

### 1. 本番ビルド

```bash
cd others/beta-versions/dictsqlite_v4.2
./build_production.sh
```

このスクリプトは以下を実行します：
- Cargo clean
- Release モードでビルド（最大最適化）
- LTO (Link-Time Optimization) 有効
- デバッグシンボル削除
- 自動インストール
- スモークテスト

### 2. パフォーマンステスト実行

#### 基本実行

```bash
python tests/test_v4.2_comprehensive_performance.py
```

#### カスタマイズ実行

```bash
# イテレーション数を指定
python tests/test_v4.2_comprehensive_performance.py --iterations 5

# 出力ファイル名を指定
python tests/test_v4.2_comprehensive_performance.py --output my_results.json

# JSON出力を無効化
python tests/test_v4.2_comprehensive_performance.py --no-json
```

### 3. 結果の確認

テスト実行後、以下のファイルが生成されます：

- `performance_results.json` - 全テスト結果（JSON形式）

JSON構造：
```json
{
  "version": "4.2.0",
  "timestamp": "2025-01-01T12:00:00",
  "iterations": 3,
  "tests": {
    "async_write_buffer_100": {
      "avg_time": 0.123,
      "stdev": 0.005,
      "min_time": 0.118,
      "max_time": 0.128,
      "iterations": [0.123, 0.118, 0.128]
    },
    ...
  }
}
```

## GitHub Actions 自動化

### ワークフロー: v4.2-performance.yml

このワークフローは以下を自動化します：

1. **ビルド＆テスト**
   - 複数OS（Ubuntu, macOS）
   - 複数Python バージョン（3.9-3.12）
   - 本番ビルド
   - 包括的パフォーマンステスト

2. **ベンチマーク比較**
   - v4.1とv4.2の比較
   - 改善倍率の計算
   - レポート生成

3. **セキュリティチェック**
   - Cargo Clippy
   - Cargo Audit
   - フォーマットチェック

### トリガー

ワークフローは以下で実行されます：

- `others/beta-versions/dictsqlite_v4.2/` の変更時
- Pull Request作成時
- 手動トリガー（workflow_dispatch）

### 手動実行

GitHub UI から：
1. Actions タブ
2. "DictSQLite v4.2 Performance Tests" を選択
3. "Run workflow" をクリック
4. イテレーション数を入力（オプション）

### 結果の取得

実行後、Artifacts からダウンロード：
- `performance-results-*` - OS/Pythonバージョン別の結果
- `benchmark-comparison` - v4.1 vs v4.2 比較

## テスト結果の解釈

### 期待される結果

#### Test 1: 非同期書き込みバッファリング

```
buffer_size=1:   約 30秒 / 1000件
buffer_size=100: 約 0.1秒 / 1000件
改善倍率: 300倍
```

#### Test 2: 同期WriteThrough バッチ書き込み

```
buffer_size=1:   約 29.79K ops/sec
buffer_size=100: 約 1.30M ops/sec
改善倍率: 43倍
```

#### Test 3: Persistモード比較

```
Memory:       最速（永続化なし）
Lazy:         高速（flushで永続化）
WriteThrough: v4.2で大幅改善（バッファリング）
```

#### Test 4-5: オーバーヘッド

```
暗号化:       10-30% オーバーヘッド（許容範囲）
Safe Pickle:  5-15% オーバーヘッド（許容範囲）
```

### パフォーマンス低下の調査

期待値を下回る場合：

1. **ビルド確認**
   ```bash
   # Release モードか確認
   cargo build --release --verbose
   ```

2. **システムリソース確認**
   ```bash
   # CPU/メモリ使用率
   top
   htop
   ```

3. **ディスクI/O確認**
   ```bash
   # tmpfs を使用
   export TMPDIR=/dev/shm
   python tests/test_v4.2_comprehensive_performance.py
   ```

4. **詳細ログ有効化**
   ```bash
   RUST_LOG=debug python tests/test_v4.2_comprehensive_performance.py
   ```

## カスタムテストの追加

テストスイートは拡張可能です：

```python
def test_my_custom_scenario(self):
    """Test 9: Custom scenario"""
    print("\n" + "="*80)
    print("TEST 9: カスタムシナリオ")
    print("="*80)
    
    # テストロジック
    # ...
```

`run_all()` メソッドのテストリストに追加：

```python
tests = [
    # ... 既存のテスト
    self.test_my_custom_scenario,
]
```

## トラブルシューティング

### ビルドエラー

```bash
# クリーンビルド
cd others/beta-versions/dictsqlite_v4.2
cargo clean
./build_production.sh
```

### インポートエラー

```bash
# インストール確認
pip list | grep dictsqlite

# 再インストール
pip uninstall dictsqlite_v4 -y
./build_production.sh
```

### テスト失敗

```bash
# 詳細モードで実行
python tests/test_v4.2_comprehensive_performance.py -v

# 個別テスト実行
python -c "
from test_v4.2_comprehensive_performance import PerformanceTestSuite
suite = PerformanceTestSuite()
suite.test_async_write_buffering()
"
```

## パフォーマンスチューニング

### バッファサイズの最適化

テスト結果から最適なバッファサイズを決定：

```python
# 小: メモリ効率重視
db = DictSQLiteV4("mydb.db", buffer_size=50)

# 中: バランス（デフォルト）
db = DictSQLiteV4("mydb.db", buffer_size=100)

# 大: スループット重視
db = DictSQLiteV4("mydb.db", buffer_size=500)
```

### Persistモードの選択

```python
# 最速（データ損失リスクあり）
db = DictSQLiteV4("mydb.db", persist_mode="memory")

# 高速（定期的にflush必要）
db = DictSQLiteV4("mydb.db", persist_mode="lazy")

# 安全（v4.2でバッファリング改善）
db = DictSQLiteV4("mydb.db", persist_mode="writethrough", buffer_size=100)
```

## CI/CD統合

### GitLab CI

```yaml
v4.2-performance:
  script:
    - cd others/beta-versions/dictsqlite_v4.2
    - ./build_production.sh
    - python tests/test_v4.2_comprehensive_performance.py
  artifacts:
    paths:
      - others/beta-versions/dictsqlite_v4.2/performance_results.json
```

### Jenkins

```groovy
stage('v4.2 Performance') {
    steps {
        sh 'cd others/beta-versions/dictsqlite_v4.2'
        sh './build_production.sh'
        sh 'python tests/test_v4.2_comprehensive_performance.py'
    }
    post {
        always {
            archiveArtifacts 'performance_results.json'
        }
    }
}
```

## 参考資料

- [README_V4.2_JP.md](README_V4.2_JP.md) - v4.2使用方法
- [V4.2_IMPLEMENTATION_SUMMARY.md](V4.2_IMPLEMENTATION_SUMMARY.md) - 実装詳細
- [V4.1_OPTIMIZATION_FINAL_REPORT_JP.md](V4.1_OPTIMIZATION_FINAL_REPORT_JP.md) - 最適化根拠

---

**作成日**: 2025年  
**バージョン**: 4.2.0
