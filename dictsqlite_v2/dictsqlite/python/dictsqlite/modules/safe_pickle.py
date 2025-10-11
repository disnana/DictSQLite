"""安全なpickle復元のためのユーティリティ。

- SafePolicy: 復元許可ポリシー
- SafeUnpickler: ポリシーに基づいてグローバル解決を制限
- safe_loads: 便利関数

注意: pickleは任意コード実行の危険があるため、常に厳格なポリシーで使うこと。
"""
from __future__ import annotations

import io
import inspect
import logging
import pickle  # nosec B403 - safe unpickler
import types
from typing import Iterable

logger = logging.getLogger(__name__)

# データ構造や値型のみを許容（副作用のあるものは含めない）
DEFAULT_SAFE_BUILTINS: set[str] = {
    'object', 'bool', 'int', 'float', 'complex', 'str', 'bytes', 'bytearray',
    'tuple', 'list', 'dict', 'set', 'frozenset', 'slice',
}

# 既定の危険関数denylist（明示拒否。必要に応じて拡張）
DEFAULT_DENY: set[str] = {
    'os.system',
    'os.popen',
    'os.spawnl',
    'os.spawnle',
    'os.spawnlp',
    'os.spawnlpe',
    'os.spawnv',
    'os.spawnve',
    'os.spawnvp',
    'os.spawnvpe',
    'subprocess.Popen',
    'subprocess.call',
    'subprocess.check_call',
    'subprocess.check_output',
    'subprocess.run',
    'builtins.eval',
    'builtins.exec',
    'builtins.__import__',
    '__builtin__.__import__',
}


class SafePolicy:  # pylint: disable=too-few-public-methods
    """Unpickle許可ポリシー。

    - allowed_module_prefixes: 許可モジュール接頭辞（自前コード等）
    - allowed_builtins: 許可builtins名（厳格ホワイトリスト）
    - allowed_globals: 完全修飾名の明示許可（'pkg.mod.Name'）
    - denied_globals: 完全修飾名の明示拒否（必ず拒否）
    - allow_functions_from_prefixes: 接頭辞に一致する関数の許可可否
    - allow_classes_from_prefixes: 接頭辞に一致するクラスタイプの許可可否
    - validator: 追加検証コールバック (module, name, obj) -> bool（Trueで許可）
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        allowed_module_prefixes: Iterable[str] = (),
        allowed_builtins: Iterable[str] | None = None,
        allowed_globals: Iterable[str] = (),
        denied_globals: Iterable[str] | None = None,
        allow_functions_from_prefixes: bool = False,
        allow_classes_from_prefixes: bool = True,
        validator=None,
    ) -> None:
        self.allowed_module_prefixes = tuple(allowed_module_prefixes)
        self.allowed_builtins = set(
            DEFAULT_SAFE_BUILTINS if allowed_builtins is None else allowed_builtins
        )
        self.allowed_globals = set(allowed_globals)
        # デフォルトでDEFAULT_DENYを使用（Noneの場合）
        self.denied_globals = set(DEFAULT_DENY if denied_globals is None else denied_globals)
        self.allow_functions_from_prefixes = bool(allow_functions_from_prefixes)
        self.allow_classes_from_prefixes = bool(allow_classes_from_prefixes)
        self.validator = validator

    @staticmethod
    def for_package(pkg_prefix: str, **kwargs) -> 'SafePolicy':
        """自前パッケージ配下を主に許可する簡易ファクトリ。"""
        return SafePolicy(allowed_module_prefixes=(pkg_prefix,), **kwargs)


class SafeUnpickler(pickle.Unpickler):
    """ポリシーに基づき、pickleのグローバル解決を厳格に制御するUnpickler。"""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        file,
        *,
        policy: SafePolicy | None = None,
        allowed_module_prefixes: Iterable[str] = (),
        allowed_builtins: Iterable[str] | None = None,
        allowed_globals: Iterable[str] = (),
    ) -> None:
        super().__init__(file)
        # 後方互換: 旧引数からポリシーを合成
        if policy is None:
            policy = SafePolicy(
                allowed_module_prefixes=allowed_module_prefixes,
                allowed_builtins=allowed_builtins,
                allowed_globals=allowed_globals,
                denied_globals=DEFAULT_DENY,
            )
        self.policy = policy

    def _is_allowed_prefix(self, module: str) -> bool:
        """許可されたモジュール接頭辞かどうか。"""
        return any(
            (module == p) or module.startswith(f"{p}.")
            for p in self.policy.allowed_module_prefixes
        )

    def find_class(self, module, name):  # noqa: D401
        """pickleのグローバル解決。ポリシーで厳格に制御。"""
        fq = f"{module}.{name}"
        # denylist は常に優先
        if fq in self.policy.denied_globals:
            logger.warning("SafeUnpickler denied (denylist): %s", fq)
            raise pickle.UnpicklingError(f"forbidden global (deny): {fq}")

        # builtins は厳格にホワイトリスト
        if module == 'builtins' and name in self.policy.allowed_builtins:
            mod = __import__(module)
            obj = getattr(mod, name)
            if self.policy.validator and not self.policy.validator(module, name, obj):
                logger.warning("SafeUnpickler validator rejected: %s", fq)
                msg = f"validator rejected: {fq}"
                raise pickle.UnpicklingError(msg)
            logger.debug("SafeUnpickler allowed builtin: %s", fq)
            return obj

        # 完全修飾名での明示許可
        if fq in self.policy.allowed_globals:
            mod = __import__(module, fromlist=[name])
            obj = getattr(mod, name)
            if self.policy.validator and not self.policy.validator(module, name, obj):
                logger.warning("SafeUnpickler validator rejected: %s", fq)
                msg = f"validator rejected: {fq}"
                raise pickle.UnpicklingError(msg)
            logger.debug("SafeUnpickler allowed global: %s", fq)
            return obj

        # 指定接頭辞のモジュール（自前コードなど）を許可（型/関数を選別）
        if self._is_allowed_prefix(module):
            mod = __import__(module, fromlist=[name])
            obj = getattr(mod, name)
            is_cls = inspect.isclass(obj)
            is_func = (
                inspect.isfunction(obj)
                or isinstance(obj, (types.BuiltinFunctionType, types.MethodType))
            )
            if (
                (is_cls and self.policy.allow_classes_from_prefixes)
                or (is_func and self.policy.allow_functions_from_prefixes)
            ):
                if self.policy.validator and not self.policy.validator(module, name, obj):
                    logger.warning("SafeUnpickler validator rejected: %s", fq)
                    msg = f"validator rejected: {fq}"
                    raise pickle.UnpicklingError(msg)
                logger.debug("SafeUnpickler allowed from prefix: %s", fq)
                return obj

        # それ以外は拒否（例: os.system, subprocess.Popen 等）
        logger.warning("SafeUnpickler denied: %s", fq)
        raise pickle.UnpicklingError(f"forbidden global: {fq}")


def safe_loads(
    data: bytes,
    *,
    policy: SafePolicy | None = None,
    allowed_module_prefixes: Iterable[str] = (),
    allowed_builtins: Iterable[str] | None = None,
    allowed_globals: Iterable[str] = (),
):
    """安全なloads。policy未指定なら簡易ポリシーを構築。"""
    return SafeUnpickler(
        io.BytesIO(data),
        policy=policy,
        allowed_module_prefixes=allowed_module_prefixes,
        allowed_builtins=allowed_builtins,
        allowed_globals=allowed_globals,
    ).load()
