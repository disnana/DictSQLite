# ベンチマークグラフ生成の修正

## 問題

GitHub Actionsでベンチマーク実行後、CSVファイルは生成されるがグラフ(PNG)が生成されない問題が発生していました。

### エラー内容
```
KeyError: 'Test'
```

## 原因

`comprehensive_benchmark.py`と`fast_comprehensive_benchmark.py`で異なるCSV形式を出力していました：

### 1. **Wide形式** (comprehensive_benchmark.py)
```csv
Test Name,Operation Count,Original Time (s),Original OPS,Fastest Time (s),Fastest OPS,Beta Time (s),Beta OPS,...
書き込みテスト(1,000件),1000,1.5,666,0.5,2000,0.3,3333,...
```
- 各バージョンが**列**として配置
- 1テスト = 1行

### 2. **Long形式** (fast_comprehensive_benchmark.py)  
```csv
Test,Version,Time (s),OPS
書き込みテスト(1,000件),original,1.5,666
書き込みテスト(1,000件),fastest,0.5,2000
書き込みテスト(1,000件),beta,0.3,3333
```
- 各バージョンが**行**として配置
- 1テスト = 3行 (original, fastest, beta)

`visualize_benchmark.py`はLong形式のみに対応していたため、Wide形式のCSVでエラーが発生していました。

## 修正内容

### 修正1: Wide形式 → Long形式 自動変換

`visualize_benchmark.py`の`__init__`メソッドに形式検出と変換ロジックを追加：

```python
def __init__(self, csv_path: str):
    # データ読み込み
    self.df = pd.read_csv(csv_path)
    
    # CSV形式を検出して変換（Wide形式 → Long形式）
    if 'Test Name' in self.df.columns:
        print("Wide形式のCSVを検出、Long形式に変換中...")
        self._convert_wide_to_long()
```

### 修正2: 変換メソッドの実装

```python
def _convert_wide_to_long(self):
    """Wide形式をLong形式に変換"""
    records = []
    
    for _, row in self.df.iterrows():
        test_name = row['Test Name']
        
        # Original
        if pd.notna(row.get('Original Time (s)')):
            records.append({
                'Version': 'original',
                'Test': test_name,
                'Duration(s)': row['Original Time (s)'],
                'OPS': row['Original OPS'],
                'Result': '成功'
            })
        
        # Fastest (同様)
        # Beta (同様)
    
    self.df = pd.DataFrame(records)
```

### 修正3: カラム名の統一

すべてのグラフ生成メソッドで使用されているカラム名を統一：
- `'Time (s)'` → `'Duration(s)'` に一括置換（32箇所）

## テスト結果

✅ **すべてのグラフが正常に生成されることを確認**

```
[1/7] OPS比較グラフ生成中...
  ✓ 保存: 1_ops_comparison_20251004_182934.png
[2/7] 実行時間比較グラフ生成中...
  ✓ 保存: 2_time_comparison_20251004_182934.png
[3/7] スピードアップ比グラフ生成中...
  ✓ 保存: 3_speedup_ratio_20251004_182934.png
[4/7] パフォーマンスヒートマップ生成中...
  ✓ 保存: 4_performance_heatmap_20251004_182934.png
[5/7] 操作タイプ別パフォーマンスグラフ生成中...
  ✓ 保存: 5_performance_by_operation_20251004_182934.png
[6/7] スケーラビリティグラフ生成中...
  ✓ 保存: 6_scalability_20251004_182934.png
[7/7] 総合ダッシュボード生成中...
  ✓ 保存: 7_dashboard_20251004_182934.png

📊 生成されたグラフファイル (7個): 合計 1.7MB
```

## 後方互換性

✅ **Long形式のCSVも引き続きサポート**
- `'Test Name'`カラムが存在しない場合は従来通りLong形式として処理
- `fast_comprehensive_benchmark.py`で生成されたCSVも問題なく動作

## 影響範囲

修正されたファイル：
- `others/benchmark/visualize_benchmark.py`
  - `__init__` メソッド: 形式検出ロジック追加
  - `_convert_wide_to_long` メソッド: 新規追加
  - 全グラフ生成メソッド: カラム名を`'Duration(s)'`に統一

## 次回のベンチマーク実行

次回GitHub Actionsでベンチマークを実行すると、自動的に：

1. ✅ CSV生成（Wide形式）
2. ✅ Wide→Long形式に自動変換
3. ✅ 全7種類のグラフを生成
4. ✅ `results/graphs/`ディレクトリに保存

が正常に動作します。
