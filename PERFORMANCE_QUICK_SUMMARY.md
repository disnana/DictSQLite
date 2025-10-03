# パフォーマンステスト結果サマリー
# Performance Test Results Summary

**テスト実施日時**: 2025-10-03  
**ベンチマークスクリプト**: `comprehensive_performance_benchmark.py`

---

## 📊 クイックサマリー / Quick Summary

### ベストパフォーマンス / Best Performance by Operation

| 操作タイプ | 最速バージョン | OPS | 備考 |
|-----------|--------------|-----|------|
| 個別書き込み / Individual Write | **Beta (optimized)** | 247K ops/s | ベースライン比 1.04x |
| 個別読み込み / Individual Read | **DictSQLite-Fastest** | 61K ops/s | ベースライン比 4.04x |
| バルク書き込み / Bulk Write | **DictSQLite-Fastest** | 438K ops/s | ベースライン比 1.31x |
| 更新 / Update | **DictSQLite (original)** | 303K ops/s | ベースライン |
| 削除 / Delete | **DictSQLite (original)** | 524K ops/s | ベースライン |
| 混合操作 / Mixed Operations | **Beta (optimized)** | 117K ops/s | - |

---

## 🏆 バージョン別推奨ユースケース / Recommended Use Cases

### DictSQLite (オリジナル版)
**推奨用途:**
- 更新操作が多いワークロード (303K ops/s)
- 削除操作が多いワークロード (524K ops/s)
- シンプルな依存関係を求める場合
- 互換性重視のプロジェクト

**特徴:**
- ✅ 安定性が高い
- ✅ 更新・削除が高速
- ⚠️ 読み込みは比較的遅い (15K ops/s)

---

### DictSQLite-Fastest
**推奨用途:**
- 大量の読み込み操作 (61K ops/s - 4倍高速)
- バルク操作が中心 (438K ops/s - 1.3倍高速)
- 読み取り重視のアプリケーション
- 非同期操作が必要な場合

**特徴:**
- ✅ APSW使用で読み込みが高速
- ✅ バルク操作に最適化
- ✅ 非同期サポート
- ⚠️ 更新・削除は比較的遅い

---

### Beta (最適化版)
**推奨用途:**
- 個別の書き込みが頻繁なワークロード (247K ops/s)
- 混合ワークロード (117K ops/s)
- メモリに余裕があるシステム
- 最新機能を試したい場合

**特徴:**
- ✅ LRUキャッシュで書き込みが高速
- ✅ メモリ最適化機能
- ✅ 混合操作に強い
- ✅ memory_budget_mb による細かな制御
- ⚠️ 非同期操作は現在最適化中

---

## 📈 詳細比較グラフ (テキスト版)

### 個別書き込み (Individual Write) - 1,000/10,000 items

```
DictSQLite        : ████████████████████████ 238K ops/s (baseline)
DictSQLite-Fastest: ████                     43K ops/s  (0.18x)
Beta (normal)     : ████████████████████████ 242K ops/s (1.02x)
Beta (optimized)  : █████████████████████████ 247K ops/s (1.04x) ⭐
```

### 個別読み込み (Individual Read) - 1,000/10,000 items

```
DictSQLite        : ███                      15K ops/s (baseline)
DictSQLite-Fastest: ████████████             61K ops/s (4.04x) ⭐
Beta (optimized)  : ████████████             61K ops/s (4.03x) ⭐
```

### バルク書き込み (Bulk Write) - 1,000/10,000 items

```
DictSQLite        : ████████████████         335K ops/s (baseline)
DictSQLite-Fastest: ██████████████████████   438K ops/s (1.31x) ⭐
Beta (optimized)  : ████████████████         330K ops/s (0.98x)
```

### 更新 (Update) - 1,000/10,000 items

```
DictSQLite        : ██████████████████       303K ops/s (baseline) ⭐
DictSQLite-Fastest: ██                       34K ops/s  (0.11x)
Beta (optimized)  : █████████████            227K ops/s (0.75x)
```

### 削除 (Delete) - 1,000/10,000 items

```
DictSQLite        : ██████████████████████████ 524K ops/s (baseline) ⭐
DictSQLite-Fastest: ██                         49K ops/s  (0.09x)
Beta (optimized)  : ███                        63K ops/s  (0.12x)
```

### 混合操作 (Mixed: Read/Write/Update) - 10,000 items

```
DictSQLite-Fastest: ███████                  38K ops/s
Beta (optimized)  : ███████████████████      117K ops/s ⭐
```

---

## 💡 選択ガイド / Selection Guide

### シナリオ別の推奨

#### シナリオ 1: 読み取り重視のアプリケーション
**推奨**: DictSQLite-Fastest
- 理由: 読み込み速度が4倍、バルク操作も高速

#### シナリオ 2: 書き込み重視のアプリケーション
**推奨**: Beta (optimized)
- 理由: 個別書き込みが最速、混合ワークロードにも対応

#### シナリオ 3: 更新・削除が多いアプリケーション
**推奨**: DictSQLite (original)
- 理由: 更新・削除操作が圧倒的に高速

#### シナリオ 4: バランス型アプリケーション
**推奨**: Beta (optimized)
- 理由: 混合操作に優れ、総合的なパフォーマンスが良好

#### シナリオ 5: 非同期が必要
**推奨**: DictSQLite-Fastest
- 理由: 安定した非同期サポート（Beta版は現在最適化中）

---

## 🔍 詳細データへのアクセス

### CSV形式の生データ
📄 **ファイル**: `performance_results.csv`
- Excel、Google Sheets等で開いて分析可能
- 全22行の詳細な測定データ

### 詳細レポート
📄 **ファイル**: `performance_summary.md`
- 操作別の詳細比較テーブル
- 速度倍率サマリー
- 主な発見事項

### 使用方法ガイド
📄 **ファイル**: `BENCHMARK_USAGE.md`
- 実行方法
- カスタマイズ方法
- トラブルシューティング

---

## 🚀 ベンチマークの実行方法

```bash
# リポジトリのルートディレクトリで実行
python comprehensive_performance_benchmark.py

# 約1-2分で完了
# 自動的にCSVとMarkdownファイルが生成されます
```

---

## 📝 注意事項

1. **環境依存**: テスト結果はシステム性能に依存します
2. **データ量**: 各バージョンで異なるアイテム数でテスト（公平性を考慮）
3. **非同期制限**: Beta版の非同期操作は現在最適化中のため一部スキップ
4. **推奨事項**: 実際のユースケースで個別にテストすることを推奨

---

**最終更新**: 2025-10-03  
**作成者**: Comprehensive Performance Benchmark Tool
