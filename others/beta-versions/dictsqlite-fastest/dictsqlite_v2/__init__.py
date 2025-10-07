"""DictSQLite-v2.0 - 最高性能を目指す統合版

Dictsqlite-Fastest と Beta 版の最良部分を統合し、
継続的なパフォーマンス最適化を実現する自律開発システム。

v2.0.1 新機能:
- AES-256暗号化サポート (オプション)
- Safe pickleデシリアライゼーション (セキュリティ)
- モジュール化されたアーキテクチャ
"""

__version__ = '2.0.1'

try:
    from .core import DictSQLiteV2, AsyncDictSQLiteV2
except ImportError:
    # Fallback for direct script execution
    from core import DictSQLiteV2, AsyncDictSQLiteV2

# Export security modules if available
try:
    from .modules import (
        derive_key,
        encrypt_aes,
        decrypt_aes,
        load_private_key,
        load_public_key,
        key_create,
        encrypt_rsa,
        decrypt_rsa,
        SafePolicy,
        SafeUnpickler,
        safe_loads,
        DEFAULT_SAFE_BUILTINS,
        DEFAULT_DENY,
    )
    _SECURITY_AVAILABLE = True
except ImportError:
    _SECURITY_AVAILABLE = False

__all__ = [
    'DictSQLiteV2',
    'AsyncDictSQLiteV2',
]

# Add security exports if available
if _SECURITY_AVAILABLE:
    __all__.extend([
        'derive_key',
        'encrypt_aes',
        'decrypt_aes',
        'load_private_key',
        'load_public_key',
        'key_create',
        'encrypt_rsa',
        'decrypt_rsa',
        'SafePolicy',
        'SafeUnpickler',
        'safe_loads',
        'DEFAULT_SAFE_BUILTINS',
        'DEFAULT_DENY',
    ])
