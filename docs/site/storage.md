# 保存形式と永続化

## `storage_mode`

- `pickle`: Python オブジェクトを広く扱えます。Safe Pickle 推奨です。
- `jsonb`: JSON 互換データ向けの MessagePack 系保存形式です。
- `json`: 可読性を優先する JSON 保存です。
- `bytes`: バイナリをそのまま保存します。

## `persist_mode`

- `memory`: プロセス内のみ。高速ですが終了時に消えます。
- `lazy`: バッファリングしてまとめて書き込みます。高スループット向けです。
- `writethrough`: 書き込みごとに永続化します。耐久性優先です。

## 安定化ポイント

v2.1.3 では flush 失敗時の再投入、delete/clear 後のバッファ復活防止、separate table の lazy 永続化を重点的に修正しています。
