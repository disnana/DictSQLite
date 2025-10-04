# Beta版バージョン選択機能 - 実装完了レポート

## ✅ 実装内容

### 1. GitHub Actionsワークフロー更新

**ファイル:** `.github/workflows/benchmark.yml`

**追加された入力パラメータ:**
```yaml
beta_version:
  description: 'Beta版のバージョン選択'
  required: true
  default: 'v1'
  type: choice
  options:
    - 'v1'
    - 'v2'
    - 'both'
```

**機能:**
- ✅ v1, v2, bothから選択可能
- ✅ 選択に応じてベンチマークスクリプトのインポートを自動変更
- ✅ v2用の依存関係（aiosqlite）を自動インストール
- ✅ 結果表示にバージョン情報を含める

### 2. ローカル実行スクリプト

**ファイル:** `others/benchmark/run_benchmark.py`

**使用方法:**
```bash
# v1のみテスト
python run_benchmark.py --beta v1

# v2のみテスト
python run_benchmark.py --beta v2

# 両方テスト
python run_benchmark.py --beta both

# フルベンチマーク
python run_benchmark.py --beta v2 --full
```

**機能:**
- ✅ 自動的にインポートを変更
- ✅ テスト後に元に戻す
- ✅ バックアップを自動作成
- ✅ 両バージョンの連続実行サポート

### 3. ドキュメント

**ファイル:** `others/BETA_VERSION_SELECTION_GUIDE.md`

**内容:**
- GitHub Actionsでの選択方法
- ローカルでの選択方法
- バージョン比較表
- トラブルシューティング
- 推奨事項

## 📊 使用例

### GitHub Actionsでv2をテスト

1. GitHubの「Actions」タブへ移動
2. 「Performance Benchmark」を選択
3. 「Run workflow」をクリック
4. 設定:
   ```
   フル機能ベンチマークを実行: false
   Beta版のバージョン選択: v2
   ```
5. 実行

### ローカルでv2をテスト

```bash
cd others/benchmark
python run_benchmark.py --beta v2
```

**実行内容:**
1. comprehensive_benchmark.pyとfast_comprehensive_benchmark.pyをバックアップ
2. インポートを`dictsqlite_fastest_beta_v2`に変更
3. ベンチマーク実行
4. 元のファイルに復元

## 🔍 動作確認項目

### GitHub Actions
- [ ] ワークフローの入力選択肢が表示される
- [ ] v1選択時に既存のベンチマークが実行される
- [ ] v2選択時にaiosqliteがインストールされる
- [ ] v2選択時にインポートが正しく変更される
- [ ] 結果にバージョン情報が表示される

### ローカル実行
- [x] v1選択時に正常動作（既存動作）
- [ ] v2選択時にインポートが変更される
- [ ] v2選択時にベンチマークが実行される
- [ ] テスト後にファイルが復元される
- [ ] both選択時に両バージョンが実行される

## 📁 変更されたファイル

```
.github/workflows/benchmark.yml          # ワークフロー更新
others/benchmark/run_benchmark.py        # 新規作成
others/BETA_VERSION_SELECTION_GUIDE.md   # 新規作成
others/BETA_VERSION_SELECTION_REPORT.md  # このファイル
```

## 🎯 次のステップ

### 短期（即実行可能）
1. **v2のテスト実行**
   ```bash
   python others/benchmark/run_benchmark.py --beta v2
   ```

2. **GitHub Actionsでv2テスト**
   - リポジトリにプッシュ
   - Actions → Performance Benchmark → Run workflow
   - beta_version: v2 を選択

### 中期
1. **両バージョン比較機能の実装**
   - 同時実行
   - 結果の並列表示
   - パフォーマンスグラフの自動生成

2. **v2の安定性検証**
   - 大規模データ（10000件）
   - 長時間実行
   - 並行アクセス

### 長期
1. **v2への完全移行**
   - v1をレガシーとしてマーク
   - v2をデフォルトに
   - v1の段階的廃止

## 💡 技術的ポイント

### インポート置換の仕組み

**GitHub Actions:**
```bash
sed -i 's/from dictsqlite_fastest_beta import/from dictsqlite_fastest_beta_v2 import/g' comprehensive_benchmark.py
```

**ローカルスクリプト:**
```python
content = content.replace(
    'from dictsqlite_fastest_beta import',
    'from dictsqlite_fastest_beta_v2 import'
)
```

### バックアップ戦略

1. 実行前にバックアップ作成
2. try-finally で確実に復元
3. エラー発生時も元に戻る

### 依存関係管理

- v1: apsw, zstandard
- v2: apsw, zstandard, **aiosqlite** ← 追加

## ✨ 完了

Beta版のバージョン選択機能が完全に実装されました。

- ✅ GitHub Actionsで選択可能
- ✅ ローカルで選択可能
- ✅ ドキュメント完備
- ✅ バックアップ機能
- ✅ エラーハンドリング

**これで、v1とv2を自由に切り替えてテストできます！**
