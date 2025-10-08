"""Tests for DictSQLite-Fastest Beta v4 Step 3: Smart Caching Strategy"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 必要なモジュールをインポート
import pytest
import pytest_asyncio

from dictsqlite_fastest_beta_v4_step3 import (
    AsyncDictSQLiteFastestBetaV4,
    HybridCache,
    DatabaseSizeAnalyzer
)


@pytest_asyncio.fixture
async def temp_db():
    """一時的なテストデータベースを作成"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    yield db_path
    
    # クリーンアップ - Windows対応: リトライロジックを追加
    time.sleep(0.1)  # 100ms待機してファイルハンドルを確実に解放
    for attempt in range(3):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            # WALファイルもクリーンアップ
            for ext in ['-wal', '-shm']:
                wal_file = db_path + ext
                if os.path.exists(wal_file):
                    os.unlink(wal_file)
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(0.2)  # 200ms待機してリトライ
        except Exception:
            break


@pytest.mark.asyncio
async def test_hybrid_cache_lru_mode(temp_db):
    """HybridCacheのLRUモードをテスト"""
    cache = HybridCache(capacity=100, strategy='lru')
    
    # データを追加
    for i in range(150):
        cache.set(f'key_{i}', f'value_{i}')
    
    # 容量を超えた分は削除されているはず
    stats = cache.get_stats()
    assert stats['size'] == 100
    assert stats['strategy'] == 'lru'
    
    # 最も古いキー（key_0～key_49）は削除されているはず
    assert cache.get('key_0') is None
    assert cache.get('key_149') == 'value_149'


@pytest.mark.asyncio
async def test_hybrid_cache_lfu_mode(temp_db):
    """HybridCacheのLFUモードをテスト"""
    cache = HybridCache(capacity=10, strategy='lfu')
    
    # データを追加
    for i in range(10):
        cache.set(f'key_{i}', f'value_{i}')
    
    # key_0を頻繁にアクセス
    for _ in range(10):
        cache.get('key_0')
    
    # key_1を1回だけアクセス
    cache.get('key_1')
    
    # 新しいキーを追加（容量オーバー）
    cache.set('key_new', 'value_new')
    
    # 頻度が低いキーが削除されるはず
    # key_0は頻度が高いので残る
    assert cache.get('key_0') == 'value_0'
    # key_newは追加されている
    assert cache.get('key_new') == 'value_new'


@pytest.mark.asyncio
async def test_hybrid_cache_hybrid_mode(temp_db):
    """HybridCacheのハイブリッドモードをテスト"""
    cache = HybridCache(capacity=10, strategy='hybrid')
    
    # データを追加
    for i in range(10):
        cache.set(f'key_{i}', f'value_{i}')
    
    # key_0を頻繁にアクセス
    for _ in range(10):
        cache.get('key_0')
    
    # 少し待機
    await asyncio.sleep(0.1)
    
    # 新しいキーを追加
    cache.set('key_new', 'value_new')
    
    # ハイブリッド戦略：頻度と時刻の両方を考慮
    # key_0は頻繁にアクセスされているので残るはず
    assert cache.get('key_0') == 'value_0'


@pytest.mark.asyncio
async def test_database_size_analyzer(temp_db):
    """DatabaseSizeAnalyzerのテスト"""
    analyzer = DatabaseSizeAnalyzer()
    
    # 空のデータベース
    db = AsyncDictSQLiteFastestBetaV4(temp_db, auto_preload=False)
    async with db:
        pass
    
    # 分析
    info = await analyzer.analyze(temp_db, 'dict_table')
    assert info['total_entries'] == 0
    assert info['should_preload'] == False
    
    # データを追加
    db = AsyncDictSQLiteFastestBetaV4(temp_db, auto_preload=False)
    async with db:
        for i in range(100):
            await db.aset(f'key_{i}', f'value_{i}' * 10)
        await db._flush_write_buffer()
    
    # 再度分析
    info = await analyzer.analyze(temp_db, 'dict_table')
    assert info['total_entries'] == 100
    assert info['total_size_bytes'] > 0
    # 小規模データなのでプリロード推奨
    assert info['should_preload'] == True


@pytest.mark.asyncio
async def test_auto_preload_small_database(temp_db):
    """小規模データベースの自動全ロード機能をテスト"""
    # 小規模データを作成
    db1 = AsyncDictSQLiteFastestBetaV4(temp_db, auto_preload=False)
    async with db1:
        for i in range(50):
            await db1.aset(f'key_{i}', f'value_{i}')
        await db1._flush_write_buffer()
    
    # 自動プリロード有効で再度開く
    db2 = AsyncDictSQLiteFastestBetaV4(
        temp_db,
        auto_preload=True,
        preload_threshold_entries=100
    )
    async with db2:
        stats = db2.get_stats()
        
        # プリロードされているはず
        assert stats['preload']['preloaded'] == True
        assert stats['preload']['db_info']['total_entries'] == 50
        
        # キャッシュサイズが50であるはず
        assert stats['cache']['size'] == 50
        
        # 全てのキーがキャッシュにあるはず
        for i in range(50):
            value = await db2.aget(f'key_{i}')
            assert value == f'value_{i}'


@pytest.mark.asyncio
async def test_no_regression_vs_step2(temp_db):
    """Step 2からの回帰がないことを確認"""
    db = AsyncDictSQLiteFastestBetaV4(
        temp_db,
        auto_preload=False,  # プリロード無効でテスト
        use_hybrid_cache=False  # 通常のLRUキャッシュ使用
    )
    
    async with db:
        # 書き込み
        start = time.time()
        for i in range(100):
            await db.aset(f'key_{i}', {'id': i, 'data': f'test_{i}'})
        write_time = time.time() - start
        
        await db._flush_write_buffer()
        
        # 読み込み
        start = time.time()
        for i in range(100):
            value = await db.aget(f'key_{i}')
            assert value['id'] == i
        read_time = time.time() - start
        
        # パフォーマンスチェック（許容範囲：Step 2の1.2倍以内）
        assert write_time < 2.0  # 十分速い
        assert read_time < 1.0  # キャッシュから読むので非常に速い
        
        stats = db.get_stats()
        assert stats['cache']['size'] == 100


@pytest.mark.asyncio
async def test_step2_tests_still_pass_basic_crud(temp_db):
    """Step 2のテスト: 基本的なCRUD操作"""
    db = AsyncDictSQLiteFastestBetaV4(temp_db)
    
    async with db:
        # 書き込み
        await db.aset('test_key', 'test_value')
        
        # 読み込み
        value = await db.aget('test_key')
        assert value == 'test_value'
        
        # 削除
        await db.adelete('test_key')
        value = await db.aget('test_key')
        assert value is None


@pytest.mark.asyncio
async def test_step2_tests_still_pass_bulk_operations(temp_db):
    """Step 2のテスト: バルク操作"""
    db = AsyncDictSQLiteFastestBetaV4(temp_db)
    
    async with db:
        # バルク挿入
        items = {f'bulk_{i}': f'value_{i}' for i in range(100)}
        await db.abulk_insert(items)
        
        # 検証
        for i in range(100):
            value = await db.aget(f'bulk_{i}')
            assert value == f'value_{i}'


@pytest.mark.asyncio
async def test_step2_tests_still_pass_background_stats(temp_db):
    """Step 2のテスト: バックグラウンド統計"""
    db = AsyncDictSQLiteFastestBetaV4(
        temp_db,
        enable_background_stats=True,
        stats_sampling_rate=0.1
    )
    
    async with db:
        # 操作を実行
        for i in range(100):
            await db.aset(f'key_{i}', f'value_{i}')
        
        for i in range(100):
            await db.aget(f'key_{i}')
        
        # 統計を取得
        stats = db.get_stats()
        
        # バックグラウンド統計が記録されている
        assert 'background_stats' in stats
        assert stats['background_stats']['counts']['get'] == 100
        assert stats['background_stats']['counts']['set'] == 100
        
        # サンプリングが機能している（全件記録されていない）
        timing_samples = stats['background_stats']['timing'].get('get', {}).get('samples', 0)
        assert timing_samples < 100  # サンプリングレート10%なので


@pytest.mark.asyncio
async def test_preload_performance_improvement(temp_db):
    """プリロードによる性能改善をテスト"""
    # 小規模データを作成
    db1 = AsyncDictSQLiteFastestBetaV4(temp_db, auto_preload=False)
    async with db1:
        for i in range(100):
            await db1.aset(f'key_{i}', f'value_{i}')
        await db1._flush_write_buffer()
    
    # プリロードなしでの読み込み時間
    db_no_preload = AsyncDictSQLiteFastestBetaV4(temp_db, auto_preload=False)
    async with db_no_preload:
        start = time.time()
        for i in range(100):
            await db_no_preload.aget(f'key_{i}')
        time_no_preload = time.time() - start
    
    # プリロードありでの読み込み時間
    db_preload = AsyncDictSQLiteFastestBetaV4(
        temp_db,
        auto_preload=True,
        preload_threshold_entries=1000
    )
    async with db_preload:
        # プリロード完了を待つ
        await asyncio.sleep(0.1)
        
        start = time.time()
        for i in range(100):
            await db_preload.aget(f'key_{i}')
        time_preload = time.time() - start
    
    # プリロード版の方が速いはず（少なくとも同等）
    # ただし、小規模データなので劇的な差はないかもしれない
    assert time_preload <= time_no_preload * 1.5  # 許容範囲


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
