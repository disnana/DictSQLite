"""DictSQLite-Fastest Beta - Aggressive Memory Optimization Version.

このベータ版は、ディスクアクセスを最小限に抑え、メモリからのアクセスを最大化することで
最高のパフォーマンスを実現することを目指しています。

主な最適化戦略:
1. LRUキャッシュによるホットデータのメモリ保持
2. 書き込みバッファリング（遅延書き込み）
3. 先読みキャッシング
4. アグレッシブなメモリPRAGMA設定
5. オプションの完全メモリモード
"""

from .dictsqlite_fastest_beta import DictSQLiteFastestBeta, AsyncDictSQLiteFastestBeta

__all__ = ['DictSQLiteFastestBeta', 'AsyncDictSQLiteFastestBeta']
__version__ = '0.1.0-beta'
