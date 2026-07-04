---
layout: home

hero:
  name: "DictSQLite"
  text: "高速・安全な Python 辞書型 SQLite ストア"
  tagline: "Rust/PyO3 実装、非同期 API、暗号化、Safe Pickle、テーブル機能、ベンチマークを備えた永続化辞書です。"
  actions:
- theme: brand
  text: はじめる
  link: ./guide
- theme: alt
  text: API
  link: ./api
- theme: alt
  text: Benchmark
  link: ./performance

features:
  - title: "dict として使える"
details: "get/set/delete/batch 操作を Python の辞書に近い感覚で扱えます。"
  - title: "安全性と永続化"
details: "AES-256-GCM、Safe Pickle、lazy/writethrough/memory モードを選べます。"
  - title: "非同期とテーブル"
details: "AsyncDictSQLite と TableProxy で asyncio や名前空間分離に対応します。"
  - title: "測定しやすい"
details: "サイズ、件数、バッチ、保存形式、永続化モード別に性能を比較できます。"
---
