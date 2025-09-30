"""DictSQLite-Fastest: High-performance SQLite dictionary using APSW."""

from dictsqlite_fastest.main import DictSQLiteFastest, AsyncDictSQLiteFastest
from dictsqlite_fastest.main import DBSyncedList, DBSyncedSet, expiring_dict

__version__ = '1.0.0'

__all__ = [
    'DictSQLiteFastest', 
    'AsyncDictSQLiteFastest',
    'DBSyncedList', 
    'DBSyncedSet', 
    'expiring_dict'
]
