# dictsqlite_v2 pytestテストスイート

## 概要

このフォルダには、dictsqlite_v2の包括的なpytestテストスイートが含まれています。
基本的な機能からオプション機能まで、同期・非同期の両方を徹底的にテストします。

## 新規追加されたテストファイル

### 基本機能テスト
1. **test_basic_operations.py** - 基本操作テスト（約50テスト）
   - CRUD操作、辞書型インターフェース、コンテキストマネージャー、イテレータ、エラーハンドリング

2. **test_storage_modes.py** - ストレージモードテスト（約40テスト）
   - Bytes、Pickle、JSONB、JSONモードの詳細テスト

3. **test_persistence_modes.py** - 永続化モードテスト（約30テスト）
   - Memory、Lazy、Writethroughモードの詳細テスト

### 非同期機能テスト
4. **test_async_operations.py** - 非同期操作テスト（約35テスト）
   - 非同期CRUD、バッチ操作、並行操作、エラーハンドリング

### 高度な機能テスト
5. **test_advanced_features.py** - 高度な機能テスト（約35テスト）
   - 暗号化、Safe Pickle、マルチテーブル、ホットティア、統計

## 既存のテストファイル

- **test_comprehensive_edge_cases.py** - エッジケーステスト（39テスト）
- **test_comprehensive_integration.py** - 統合テスト（21テスト）
- **test_comprehensive_stress.py** - ストレステスト（18テスト）
- その他の専門的なテストファイル

## テスト総数

- **新規テスト**: 約190テスト
- **既存テスト**: 約100テスト
- **合計**: 約290テスト以上

## 実行方法

### すべてのテストを実行
```bash
cd dictsqlite_v2/dictsqlite
python -m pytest tests/ -v
```

### 新規テストのみ実行
```bash
# 基本操作
python -m pytest tests/test_basic_operations.py -v

# ストレージモード
python -m pytest tests/test_storage_modes.py -v

# 永続化モード
python -m pytest tests/test_persistence_modes.py -v

# 非同期操作
python -m pytest tests/test_async_operations.py -v

# 高度な機能
python -m pytest tests/test_advanced_features.py -v
```

### 特定のテストクラスを実行
```bash
python -m pytest tests/test_basic_operations.py::TestBasicCRUD -v
```

## 前提条件

### モジュールのビルド
```bash
cd dictsqlite_v2/dictsqlite
maturin develop --release
```

### 依存関係
```bash
pip install pytest pytest-asyncio
```

## テストカバレッジ

新しいテストにより、以下がカバーされます：

✅ **基本機能**: CRUD、辞書型API、コンテキストマネージャー、イテレータ  
✅ **ストレージモード**: Bytes、Pickle、JSONB、JSON  
✅ **永続化モード**: Memory、Lazy、Writethrough  
✅ **非同期操作**: 基本～高並行度（最大1000並行）  
✅ **暗号化**: AES-256-GCM  
✅ **Safe Pickle**: セキュアなオブジェクト直列化  
✅ **マルチテーブル**: 複数テーブルの隔離  
✅ **ホットティア**: キャパシティ管理とLRU eviction  
✅ **統計**: モニタリングとパフォーマンス測定  
✅ **エラーハンドリング**: すべての異常系  

## 詳細ドキュメント

詳細な情報は以下のファイルを参照してください：
- [README_NEW_COMPREHENSIVE_TESTS.md](./README_NEW_COMPREHENSIVE_TESTS.md) - 新規テストの詳細説明
- [README_COMPREHENSIVE_TESTS.md](./README_COMPREHENSIVE_TESTS.md) - 既存テストの説明

## 貢献

新しいテストを追加する際は、以下の原則に従ってください：

1. **隔離性**: 各テストは独立して実行可能
2. **再現性**: 一時ファイルを使用し、テスト後にクリーンアップ
3. **包括性**: 正常系と異常系の両方をカバー
4. **実用性**: 実世界の使用パターンに基づく
5. **パフォーマンス**: 大規模データでの動作検証
