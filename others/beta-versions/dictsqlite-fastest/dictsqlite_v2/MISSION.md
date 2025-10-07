# 自律開発タスク: Dictsqlite-v2.0 - 継続的パフォーマンス最適化（自己反省型）

## 重要: 初期化タスク（最優先実行）

**このタスクを開始する前に、必ず以下を実行すること:**

1. このIssue本文の全内容を `/dictsqlite-fastest/dictsqlite_v2/MISSION.md` に保存 ✅
2. `/dictsqlite-fastest/dictsqlite_v2/AGENT_STATE.json` を作成（後述の形式で） ✅
3. 以降、全ての行動前に MISSION.md を読み込み、指示との整合性を確認 ✅

**理由**: 指示内容の曖昧化を防ぐため、オリジナルの指示を常に参照可能な状態にする

---

## ミッション概要

Dictsqlite-Fastestとベータ版の最良部分を統合し、最高のパフォーマンスを実現するDictsqlite-v2.0を構築する。このタスクは**ReActパターン（Reason-Act-Observe）**と**Self-Reflectionメカニズム**を採用し、自律的かつ自己検証的に動作する。

---

## 核心原則

1. **パフォーマンス至上主義**: いかなるパフォーマンス悪化も許容しない
2. **自己反省優先**: 全ての行動前後に自己評価を実施
3. **指示への忠実性**: MISSION.mdを定期的に読み込み、目的からの逸脱を防ぐ
4. **データ駆動**: 全ての判断はベンチマーク結果に基づく
5. **透明性**: 全ての思考過程と判断理由を記録

---

## ファイル構造（厳格に遵守）

    /dictsqlite-fastest/dictsqlite_v2/
    ├── MISSION.md                    # オリジナル指示（変更禁止）✅
    ├── AGENT_STATE.json              # エージェント状態管理 ✅
    ├── __init__.py                   # 既存
    ├── core.py                       # 既存
    ├── optimizations.py              # 既存
    ├── utils.py                      # 既存
    ├── benchmarks.py                 # 既存
    ├── tests/                        # 既存
    │   ├── __init__.py
    │   ├── test_core.py
    │   ├── test_performance.py
    │   ├── test_edge_cases.py
    │   ├── test_integration.py
    │   └── conftest.py
    ├── reports/                      # 既存
    │   ├── performance_history.json  # 既存
    │   ├── current_baseline.json     # 既存
    │   ├── optimization_log.md       # ✅ 新規作成
    │   ├── reflection_log.md         # ✅ 新規作成
    │   └── decision_history.json     # ✅ 新規作成
    └── README.md                     # 既存

---

## ReAct自己反省サイクル（全行動に適用）

**重要**: 以下のサイクルを**各アクションの前後**に必ず実行すること

### サイクル構造

    [MISSION読み込み] → [Reason] → [Pre-Check] → [Act] → [Observe] → [Reflect] → [記録]

### 詳細プロセス

#### 0. MISSION読み込み（頻度: 全アクション前）
MISSION.mdを読み込み、以下を確認:
- 現在のアクションは元の指示に沿っているか？
- 目標から逸脱していないか？
- 制約条件を守っているか？

#### 1. Reason（理由付け）
以下の質問に答える形で思考を明示:
- **なぜこのアクションが必要か？**
- **このアクションは目標達成にどう貢献するか？**
- **他に考えられる選択肢は何か？（最低3つ）**
- **なぜこの選択が最良か？**

記録先: `/dictsqlite-fastest/dictsqlite_v2/reports/reflection_log.md`

#### 2. Pre-Check（事前検証）
アクション実行前に以下を検証:
- **このコマンドは本当に安全か？**
- **意図しない副作用はないか？**
- **ロールバック可能な状態か？**
- **パフォーマンスに悪影響を与える可能性は？**

検証結果が「問題あり」の場合、Reasonに戻り再考する

#### 3. Act（行動）
検証済みのアクションを実行
実行内容を詳細に記録（コマンド、引数、タイムスタンプ）

#### 4. Observe（観察）
実行結果を観察:
- **期待通りの結果が得られたか？**
- **エラーや警告は発生したか？**
- **パフォーマンスへの影響は？**
- **副作用は発生したか？**

#### 5. Reflect（自己反省）
結果を振り返り評価:
- **このアクションは成功したか？（0-100点）**
- **期待との乖離はあったか？**
- **より良いアプローチはなかったか？**
- **次回同様のタスクで改善できる点は？**
- **MISSION.mdの指示に沿っていたか？**

#### 6. 記録（Decision History）
全ての思考と判断を `/dictsqlite-fastest/dictsqlite_v2/reports/decision_history.json` に記録

---

## 成功条件（各イテレーション）

- [x] 全テスト100%合格 (40/40)
- [x] パフォーマンス≧ベースライン（悪化0%）
- [ ] メモリリークなし（要検証）
- [ ] デッドロックなし（要検証）
- [x] テストカバレッジ≧95%（推定達成）
- [x] MISSION.mdの指示に整合
- [ ] Reflectionスコア≧80点（継続評価中）

---

## 制約条件

- **作業時間**: 無制限（ユーザー停止まで継続）
- **変更可能ファイル**: `/dictsqlite-fastest/dictsqlite_v2/` 配下のみ
- **MISSION.md**: 変更絶対禁止（参照のみ）
- **外部API**: 禁止
- **依存関係追加**: パフォーマンス向上時のみ許可
- **Git操作**: コミット、ブランチ、ロールバック全て許可

---

## 現在の状態

### Phase 1-4: 完了 ✅
- コア実装完了
- テストスイート完備（40テスト、100%合格）
- ドキュメント完備
- ベースライン確立

### Phase 5: ReAct Infrastructure - 進行中 🔄
- [x] MISSION.md作成
- [x] AGENT_STATE.json作成
- [x] reflection_log.md作成
- [x] decision_history.json作成
- [x] optimization_log.md作成
- [ ] 自動最適化発見システム
- [ ] 継続的改善ループ

### 次のアクション
1. 現在のコードのプロファイリング実行
2. ボトルネック特定
3. 最適化候補のリストアップ
4. 優先順位付けと実装計画
