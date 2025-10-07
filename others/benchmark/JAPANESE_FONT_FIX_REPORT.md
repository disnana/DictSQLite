# グラフの日本語文字化け修正レポート

## 問題の概要

GitHub Actionsのベンチマークで生成されるグラフにおいて、日本語テキストが文字化け（□□□として表示）していた。

## 原因分析

### 根本原因

`generate_graphs.py` と `compare_versions.py` において、以下の問題がありました：

1. **インポート順序の問題**: matplotlib/seabornを**先に**インポートしてから、`setup_japanese_font()`を呼び出していた
2. **設定の上書き**: フォント設定後に重要な設定（`axes.unicode_minus`）が再適用されていなかった

```python
# 修正前（問題あり）
import matplotlib.pyplot as plt  # ← matplotlibを先にインポート
import seaborn as sns

# その後でフォント設定
from visualize_benchmark import setup_japanese_font
setup_japanese_font()  # ← 手遅れ！既にmatplotlibが初期化済み
```

### なぜこれが問題なのか

matplotlibは最初のインポート時にフォント設定を読み込んで初期化します。その後で`setup_japanese_font()`を呼び出しても、既に初期化済みのため、フォント設定が正しく適用されません。

## 修正内容

### 1. インポート順序の修正

フォント設定を**matplotlibインポート前**に実行するよう変更：

```python
# 修正後（正しい順序）
import sys
from pathlib import Path
import warnings

# 日本語フォント設定を最初に実行（matplotlibインポート前）
try:
    from visualize_benchmark import setup_japanese_font
    setup_japanese_font()  # ← matplotlibインポート前に実行
except ImportError:
    print("⚠ 日本語フォント設定をスキップ")

# matplotlibとseabornはフォント設定後にインポート
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# マイナス記号の文字化け防止（フォント設定後に再適用）
plt.rcParams['axes.unicode_minus'] = False
```

### 2. 変更ファイル

- `others/benchmark/generate_graphs.py`
- `others/benchmark/compare_versions.py`

## 検証結果

### 修正前
```
⚠ Glyph 12496 (\N{KATAKANA LETTER BA}) missing from font(s) DejaVu Sans.
⚠ Glyph 12540 (\N{KATAKANA-HIRAGANA PROLONGED SOUND MARK}) missing from font(s) DejaVu Sans.
（多数の警告が発生）
```

### 修正後
```
✓ 日本語フォント設定: Noto Sans CJK JP
✓ データ読み込み: 9行
✓ グラフ生成成功!

📝 フォント設定:
   font.sans-serif: ['Noto Sans CJK JP', 'Yu Gothic UI']
   axes.unicode_minus: False
```

## その他の修正

### バージョン比較の初回実行について

issue で「グラフの出力が2回目からなのも気になる」という指摘がありましたが、これは**仕様通りの動作**です：

- **個別バージョンのグラフ**: 初回実行から生成される ✅
- **バージョン間比較グラフ**: 2つ以上のバージョンが必要（2回目以降） ✅

`compare_versions.py` のエラーメッセージを改善し、この仕様を明確化しました：

```python
if len(self.version_data) < 2:
    print(f"\n⚠ バージョン間比較には少なくとも2つのバージョンが必要です（現在: {len(self.version_data)}個）")
    print("   別のバージョンでベンチマークを実行してから、再度このツールを実行してください。")
    return
```

## v4のパフォーマンス問題について

issue で「v4がv2より遅い」という指摘がありましたが、これは別の調査が必要な問題です：

### 考えられる原因
1. リリースモードでビルドされていない可能性（`--release`フラグ）
2. `hot_capacity` の設定が不適切
3. 非同期モードが無効になっている
4. 根本的なアーキテクチャの問題

### 推奨される調査項目
- v4のビルド設定の確認
- ベンチマーク実行時の設定パラメータの検証
- README_JP.mdの「パフォーマンスが期待値より低い」セクションの確認

これは今回の文字化け修正とは別の問題として、新しいissueで追跡することを推奨します。

## まとめ

| 項目 | 状態 | 説明 |
|-----|------|-----|
| 日本語文字化け | ✅ 修正完了 | インポート順序を修正 |
| 2回目からグラフ | ✅ 仕様確認 | バージョン比較は2つ以上必要（正常動作） |
| v4パフォーマンス | ⚠️ 別調査必要 | 設定・ビルド方法の検証が必要 |

## テスト方法

修正が正しく機能していることを確認するには：

```bash
cd others/benchmark

# テストCSVを作成
cat > /tmp/test_benchmark.csv << 'EOF'
Version,Test,OPS,Duration(s),Result
original,基本操作,100000,0.5,成功
fastest,基本操作,250000,0.2,成功
beta,基本操作,180000,0.28,成功
EOF

# グラフ生成
python3 generate_graphs.py /tmp/test_benchmark.csv --version test

# 生成されたグラフを確認
ls -lh /tmp/graphs/stats_summary.png
```

正常に動作していれば、日本語フォント設定メッセージが表示され、警告なしでグラフが生成されます。
