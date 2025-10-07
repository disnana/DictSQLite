"""DictSQLite v2.0 Modules - Security and utility modules."""

from .crypto import (
    derive_key,
    encrypt_aes,
    decrypt_aes,
    load_private_key,
    load_public_key,
    key_create,
    encrypt_rsa,
    decrypt_rsa,
)

from .safe_pickle import (
    SafePolicy,
    SafeUnpickler,
    safe_loads,
    DEFAULT_SAFE_BUILTINS,
    DEFAULT_DENY,
)

__all__ = [
    # Crypto functions
    'derive_key',
    'encrypt_aes',
    'decrypt_aes',
    'load_private_key',
    'load_public_key',
    'key_create',
    'encrypt_rsa',
    'decrypt_rsa',
    # Safe pickle
    'SafePolicy',
    'SafeUnpickler',
    'safe_loads',
    'DEFAULT_SAFE_BUILTINS',
    'DEFAULT_DENY',
]
