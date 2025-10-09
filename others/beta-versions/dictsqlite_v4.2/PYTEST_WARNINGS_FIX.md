# Pytest Warnings Configuration Fix

## 概要 (Overview)

このドキュメントは、dictsqlite v4.2のpytestテスト実行時の警告に関する設定を説明します。

## 問題 (Issue)

pytestでテストを実行する際、警告が適切に表示されない、または将来的に警告が発生する可能性がありました。

## 対応内容 (Changes Made)

### 1. `asyncio_mode` の設定

```ini
asyncio_mode = auto
```

**理由**: pytest-asyncioプラグインが非同期テストを自動的に検出するようにします。これにより、非同期テスト関数に対して適切なイベントループが提供されます。

### 2. `asyncio_default_fixture_loop_scope` の設定

```ini
asyncio_default_fixture_loop_scope = function
```

**理由**: pytest-asyncioの新しいバージョンでは、この設定が`None`の場合に非推奨警告(DeprecationWarning)が発生します。`function`スコープに設定することで、各テスト関数ごとに新しいイベントループが作成され、テスト間の干渉を防ぎます。

### 3. `filterwarnings` の設定

```ini
filterwarnings =
    default
```

**理由**: デフォルトでは、pytestは一部の警告を抑制します。`default`を設定することで、すべての警告が表示されるようになります。これにより、潜在的な問題を早期に発見できます。

## 設定の効果 (Benefits)

1. **警告の可視化**: すべての警告がテスト実行時に表示されます
2. **非推奨機能の検出**: 将来のバージョンで削除される可能性のある機能の使用を検出できます
3. **pytest-asyncioの警告防止**: イベントループスコープの設定により、非推奨警告を防ぎます
4. **テストの独立性**: 各テスト関数が独立したイベントループで実行されます

## テスト実行方法 (How to Run Tests)

```bash
# 警告を表示してテストを実行
pytest tests -q

# より詳細な警告情報を表示
pytest tests -v -W default
```

## 参考資料 (References)

- [pytest documentation: Warnings](https://docs.pytest.org/en/stable/how-to/capture-warnings.html)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [PEP 565 – Show DeprecationWarning in __main__](https://www.python.org/dev/peps/pep-0565/)
