# DictSQLite v4.2 包括的テストスイート

## 概要

このディレクトリには、DictSQLite v4.2の包括的なテストスイートが含まれています。既存のテストに加えて、エッジケース、統合シナリオ、ストレステストをカバーする3つの新しいテストファイルが追加されました。

## 新しいテストファイル

### 1. test_comprehensive_edge_cases.py (39テスト)

エッジケースとエラーハンドリングのテスト：

- **TestEdgeCaseKeys**: キーのエッジケース
  - 空文字列キー
  - 非常に長いキー（10KB）
  - 特殊文字を含むキー（NULL文字、引用符、記号など）
  - Unicodeエッジケース（絵文字、複合文字、ゼロ幅文字）
  - 数値文字列キー

- **TestEdgeCaseValues**: 値のエッジケース
  - 空のバイト列
  - 非常に大きな値（100MB）
  - すべてのバイト値（0-255）
  - NULLバイトの繰り返し

- **TestJSONBEdgeCases**: JSONBモードのエッジケース
  - 深くネストされた構造（10階層）
  - 大きなJSON配列（10,000要素）
  - 混合型配列
  - 空のコンテナ
  - Null値を含む辞書
  - 数値の極値
  - Unicode文字

- **TestErrorHandling**: エラーハンドリング
  - 存在しないキーへのアクセス
  - 無効なストレージモード
  - 無効な永続化モード
  - JSONBでシリアライズ不可能なオブジェクト
  - Bytesモードで辞書を保存しようとする

- **TestTableEdgeCases**: テーブル機能のエッジケース
  - 多数のテーブル（100個）
  - 特殊文字を含むテーブル名
  - テーブル間のキー隔離
  - 空のテーブル名

- **TestConcurrentOperations**: 並行操作
  - 高速連続書き込み（10,000回）
  - 読み書き交互実行
  - 削除と再作成の繰り返し

- **TestBoundaryConditions**: 境界条件
  - ホットティア容量制限
  - 空のデータベースのフラッシュ
  - 複数回のclose呼び出し
  - close後の操作

- **TestDataIntegrity**: データ整合性
  - フラッシュ後の永続性
  - 上書きの一貫性
  - 混合操作の整合性
  - テーブル間のデータ整合性

- **TestAsyncEdgeCases**: 非同期版のエッジケース
  - 高速操作（1,000回）
  - テーブル操作

### 2. test_comprehensive_integration.py (21テスト)

統合テストと実世界のシナリオ：

- **TestStorageModeIntegration**: ストレージモードの統合
  - Pickle + 暗号化
  - JSONB + 複数テーブル
  - JSON + Safe Pickle
  - Bytes + 暗号化

- **TestPersistModeIntegration**: 永続化モードの統合
  - メモリモード + JSONB
  - 遅延モード + テーブル
  - 即時書き込みモード + 暗号化

- **TestRealWorldScenarios**: 実世界のシナリオ
  - ユーザーセッション管理
  - 設定ストレージ
  - キャッシュレイヤー
  - マルチテナントデータ
  - ジョブキュー

- **TestFeatureCombinations**: 機能の組み合わせ
  - すべてのセキュリティ機能
  - すべてのパフォーマンス機能
  - 混合テーブルストレージモード

- **TestAsyncIntegration**: 非同期統合
  - 非同期 + JSONB + テーブル
  - 非同期バッチ + テーブル

- **TestStatsAndMonitoring**: 統計とモニタリング
  - すべての機能有効時の統計
  - 各種操作後の統計変化

- **TestMigrationScenarios**: マイグレーションシナリオ
  - BytesモードからJSONBモードへ
  - 既存DBに暗号化を追加

### 3. test_comprehensive_stress.py (18テスト)

ストレステストとパフォーマンス検証：

- **TestLargeScaleData**: 大規模データ
  - 10万エントリ
  - 大きな値（各1MB × 100個）
  - 多数のテーブル（1,000個）

- **TestStressPatterns**: ストレスパターン
  - 高速連続更新（10,000回）
  - 交互操作（書き込み・読み込み・削除）
  - 一括削除（10,000エントリ）

- **TestPerformanceBoundaries**: パフォーマンス境界
  - ホットティアオーバーフロー
  - メモリモード制限
  - 遅延モードバッファ

- **TestAsyncStress**: 非同期ストレス
  - 高スループット（10,000エントリ）
  - バッチ操作（10,000アイテム）

- **TestEncryptionPerformance**: 暗号化パフォーマンス
  - 暗号化のオーバーヘッド測定

- **TestConcurrencyPatterns**: 並行パターン
  - 複数テーブルへの交互アクセス

- **TestLongRunningOperations**: 長時間実行
  - 持続的な書き込み負荷（10秒間）
  - 繰り返しセッションサイクル（100回）

- **TestMemoryManagement**: メモリ管理
  - 削除後のメモリクリーンアップ
  - ガベージコレクション

## テスト実行方法

### すべてのテストを実行

```bash
cd others/beta-versions/dictsqlite_v4.2
python -m pytest tests/ -v
```

### 新しい包括的テストのみ実行

```bash
# エッジケーステスト
python -m pytest tests/test_comprehensive_edge_cases.py -v

# 統合テスト
python -m pytest tests/test_comprehensive_integration.py -v

# ストレステスト（時間がかかる）
python -m pytest tests/test_comprehensive_stress.py -v
```

### 特定のテストクラスを実行

```bash
# JSONBエッジケースのみ
python -m pytest tests/test_comprehensive_edge_cases.py::TestJSONBEdgeCases -v

# 実世界シナリオのみ
python -m pytest tests/test_comprehensive_integration.py::TestRealWorldScenarios -v
```

### ストレステストの一部を実行（高速テストのみ）

```bash
# 100kエントリテストを除外
python -m pytest tests/test_comprehensive_stress.py -v -k "not test_100k"
```

## テストカバレッジ

これらの新しいテストにより、以下の領域が網羅されます：

1. **基本機能**: 既存のテストでカバー
2. **エッジケース**: 39の新しいテスト
3. **統合シナリオ**: 21の新しいテスト
4. **ストレステスト**: 18の新しいテスト
5. **パフォーマンス**: 既存 + 新しいストレステスト
6. **セキュリティ**: 既存のtest_v4_security.py + 統合テスト

### 合計テスト数

- **既存テスト**: 
  - test_v4_security.py: 19テスト
  - test_jsonb_table_support.py: 10テスト
  - test_v3_compatibility.py: ~15テスト
  - その他: ~50テスト

- **新規テスト**: 78テスト
  - test_comprehensive_edge_cases.py: 39テスト
  - test_comprehensive_integration.py: 21テスト
  - test_comprehensive_stress.py: 18テスト

**総計**: 約170テスト以上

## テスト設計の原則

1. **隔離性**: 各テストは独立して実行可能
2. **再現性**: 一時ファイルを使用し、テスト後にクリーンアップ
3. **包括性**: 正常系と異常系の両方をカバー
4. **実用性**: 実世界の使用パターンに基づく
5. **パフォーマンス**: 大規模データでの動作検証

## 注意事項

- ストレステストは実行に時間がかかる場合があります（特に100kエントリテスト）
- 一部のテストは実装の詳細に依存するため、実際の動作に合わせて調整されています
- 暗号化テストはパスワードを使用しますが、テスト用の簡易的なものです

## 今後の拡張

さらに以下のテストを追加することで、カバレッジを向上できます：

1. マルチスレッド並行アクセステスト
2. ネットワーク障害シミュレーション
3. ディスク容量不足のテスト
4. メモリ不足のテスト
5. より複雑なデータ型のテスト
6. パフォーマンスリグレッションテスト

## まとめ

これらの包括的なテストにより、DictSQLite v4.2のすべての主要機能、エッジケース、統合シナリオ、パフォーマンス特性が徹底的に検証されます。
