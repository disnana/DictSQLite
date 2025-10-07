# Fix Summary: actionsのパフォーマンスベンチマークについて

## 問題の概要

GitHub Actionsでパフォーマンスベンチマークを `--beta all` モードで実行した場合、全バージョン (v1, v2, v3, v4) のベンチマークが実行されるべきですが、`compare_versions.py` を実行すると以下のように1個のバージョンしか検出されない問題がありました：

```
利用可能なバージョン: 1個
  ✓ v2: 19件のテスト結果
================================================================================
バージョン間比較ツール
================================================================================
⚠ バージョン間比較には少なくとも2つのバージョンが必要です（現在: 1個）
   別のバージョンでベンチマークを実行してから、再度このツールを実行してください。
```

## 原因

`benchmark_all_versions.py` スクリプトは：
1. 4つのバージョン (v1, v2, v3, v4) すべてのベンチマークを実行
2. 結果をコンソールに表示
3. **しかし、VersionManagerに結果を保存していなかった**

そのため、`compare_versions.py` が実行されても、保存された結果がないため、バージョン間比較ができませんでした。

## 修正内容

`others/beta-versions/dictsqlite-fastest/beta/benchmark_all_versions.py` を以下のように修正：

### 1. VersionManagerのインポート追加

```python
# Import VersionManager
try:
    from version_manager import VersionManager
    VERSION_MANAGER_AVAILABLE = True
except ImportError:
    print("⚠ VersionManagerが利用できません。結果は保存されません。")
    VERSION_MANAGER_AVAILABLE = False
```

### 2. 結果保存関数の追加

```python
def save_version_results(version_name: str, results_dict: Dict[str, Tuple[float, float]], test_labels: list):
    """Save benchmark results for a specific version to VersionManager."""
    if not VERSION_MANAGER_AVAILABLE:
        return
    
    # Create VersionManager with explicit beta_version
    vm = VersionManager(beta_version=version_name)
    
    # Generate CSV content
    csv_lines = []
    csv_lines.append("Test Name,Operation Count,Original Time (s),Original OPS,Fastest Time (s),Fastest OPS,Beta Time (s),Beta OPS,Speedup (Fastest/Original),Speedup (Beta/Original),Speedup (Beta/Fastest)")
    
    test_names = ['basic_write', 'basic_read', 'concurrent_read', 'bulk_insert', 'mixed_ops']
    operation_counts = [300, 300, 600, 500, 400]
    
    for test_name, label, op_count in zip(test_names, test_labels, operation_counts):
        elapsed, ops = results_dict[test_name]
        csv_lines.append(f"{label},{op_count},N/A,N/A,N/A,N/A,{elapsed},{ops},N/A,N/A,N/A")
    
    csv_content = '\n'.join(csv_lines)
    
    # Save to version manager
    saved_files = vm.save_benchmark_result(
        csv_content=csv_content,
        version_string=version_name
    )
    
    print(f"\n✓ {version_name} の結果を保存しました: {saved_files.get('csv', 'N/A')}")
```

### 3. 各バージョンのベンチマーク実行後に結果を保存

```python
# Run benchmarks
v1_results = await run_v1_benchmark(v1_path)
if VERSION_MANAGER_AVAILABLE:
    save_version_results('v1', v1_results, test_labels)

v2_results = await run_v2_benchmark(v2_path)
if VERSION_MANAGER_AVAILABLE:
    save_version_results('v2', v2_results, test_labels)

v3_results = await run_v3_benchmark(v3_path)
if VERSION_MANAGER_AVAILABLE:
    save_version_results('v3', v3_results, test_labels)

v4_results = await run_v4_benchmark(v4_path)
if VERSION_MANAGER_AVAILABLE:
    save_version_results('v4', v4_results, test_labels)
```

## 修正後の動作

`python run_benchmark.py --beta all` を実行すると：

1. v1, v2, v3, v4 すべてのベンチマークが実行される
2. 各バージョンの結果が以下のディレクトリに保存される：
   - `others/benchmark/results/versions/v1/benchmark.csv`
   - `others/benchmark/results/versions/v2/benchmark.csv`
   - `others/benchmark/results/versions/v3/benchmark.csv`
   - `others/benchmark/results/versions/v4/benchmark.csv`

3. `compare_versions.py` を実行すると、4個のバージョンが検出される：

```
利用可能なバージョン: 4個
  ✓ v1: 5件のテスト結果
  ✓ v2: 5件のテスト結果
  ✓ v3: 5件のテスト結果
  ✓ v4: 5件のテスト結果
```

4. バージョン間比較グラフとレポートが正常に生成される

## テスト結果

以下のテストを実施し、すべて成功：

- ✅ VersionManagerが各バージョン (v1-v4) で正しく動作することを確認
- ✅ 各バージョンの結果が正しいCSVフォーマットで保存されることを確認
- ✅ `list_available_versions()` が4個のバージョンを返すことを確認
- ✅ CSVヘッダーが `comprehensive_benchmark.py` と互換性があることを確認
- ✅ `compare_versions.py` がすべてのバージョンを読み込めることを確認

## 影響範囲

- ✅ 最小限の変更（外科的修正）
- ✅ 既存機能への破壊的変更なし
- ✅ 単一バージョンベンチマークとの後方互換性あり
- ✅ バージョン間比較機能が意図通りに動作可能

## 変更ファイル

- `others/beta-versions/dictsqlite-fastest/beta/benchmark_all_versions.py`
  - VersionManagerのインポート追加
  - `save_version_results()` 関数追加
  - `main()` 関数の修正（各バージョン実行後に結果保存）
