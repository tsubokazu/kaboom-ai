# Phase 3A: フロントエンド詳細機能開発計画

## 📋 概要

Phase 2C完了により、企業級API基盤（65エンドポイント）とNext.js 15基本構造が完成。
Phase 3Aでは、ユーザー向け主要機能を順次実装し、完全な取引管理プラットフォームを構築する。

## 🎯 開発優先度

1. **認証ログイン画面** - Supabase統合・ユーザー管理基盤
2. **バックテスト画面** - 戦略検証・パフォーマンス分析
3. **AI分析詳細画面** - マルチモデル分析・合意形成表示
4. **取引画面** - リアルタイム取引・注文管理

## 🚀 Phase 3A 実装計画

### 1. 認証ログイン画面 (3-4日)

#### 1.1 ログイン・認証システム
- **Supabase Auth統合**
  - メール・パスワード認証
  - Google/GitHub OAuth統合
  - パスワードリセット機能
- **権限管理UI**
  - BASIC/PREMIUM/ENTERPRISE/ADMIN権限表示
  - 権限別機能制限表示
- **セッション管理**
  - 自動ログアウト機能
  - セッション有効期限表示

#### 1.2 ユーザー管理画面
- **プロフィール設定**
  - ユーザー情報編集
  - プロフィール画像アップロード
- **アカウント設定**
  - パスワード変更
  - 二段階認証設定
  - API接続設定（立花証券）

#### 1.3 実装ファイル
```typescript
// 認証関連コンポーネント
web/src/app/(auth)/login/page.tsx
web/src/app/(auth)/register/page.tsx
web/src/app/(auth)/forgot-password/page.tsx
web/src/components/auth/LoginForm.tsx
web/src/components/auth/RegisterForm.tsx
web/src/hooks/useAuth.ts
web/src/stores/authStore.ts
```

### 2. バックテスト画面 (4-5日) ⚡ 優先実装

#### 2.1 戦略設定画面
- **基本戦略選択**
  - SMA（移動平均）クロス戦略
  - RSIオーバーソール戦略
  - MACD戦略
  - カスタム戦略作成
- **パラメータ設定**
  - 期間設定（短期・中期・長期移動平均）
  - 閾値設定（RSI上限・下限）
  - リスク管理設定（ストップロス・利確）

#### 2.2 バックテスト実行
- **実行設定**
  - 対象銘柄選択（個別・ポートフォリオ）
  - 期間設定（過去1年・3年・5年・カスタム）
  - 初期資金設定
- **リアルタイム進捗表示**
  - WebSocket経由の進捗更新
  - 処理時間・完了予測表示
  - キャンセル機能

#### 2.3 結果分析画面
- **パフォーマンス指標**
  - 総収益率・シャープレシオ・最大ドローダウン
  - 勝率・平均利益・平均損失
  - リターン分布・リスク分析
- **視覚化チャート**
  - 累積リターンチャート（vs ベンチマーク）
  - ドローダウンチャート
  - 月次・年次リターン分析
  - 取引履歴テーブル

#### 2.4 戦略比較・最適化
- **複数戦略比較**
  - 並列実行・結果比較表示
  - パフォーマンスランキング
- **パラメータ最適化**
  - グリッドサーチ実行
  - 最適パラメータ提案
  - オーバーフィッティング警告

#### 2.5 実装ファイル
```typescript
// バックテスト関連コンポーネント
web/src/app/(dashboard)/backtest/page.tsx
web/src/app/(dashboard)/backtest/strategy/page.tsx
web/src/app/(dashboard)/backtest/results/[id]/page.tsx
web/src/components/backtest/StrategyBuilder.tsx
web/src/components/backtest/BacktestRunner.tsx
web/src/components/backtest/ResultsAnalysis.tsx
web/src/components/backtest/PerformanceCharts.tsx
web/src/hooks/useBacktest.ts
web/src/stores/backtestStore.ts
```

### 3. AI分析詳細画面 (3-4日)

#### 3.1 マルチモデル分析表示
- **4モデル並列分析**
  - GPT-4: テクニカル分析
  - Claude: センチメント分析
  - Gemini: リスク分析
  - 汎用モデル: 総合判断
- **合意形成プロセス**
  - 各モデルの判断表示
  - 合意戦略選択（重み付け平均・多数決・信頼度ベース）
  - 最終判断・信頼度表示

#### 3.2 分析結果詳細
- **テクニカル分析**
  - チャートパターン認識
  - 指標解析（RSI・MACD・ボリンジャーバンド）
  - サポート・レジスタンス分析
- **ファンダメンタルズ分析**
  - 企業業績分析
  - 業界比較分析
  - マクロ経済要因分析

#### 3.3 実装ファイル
```typescript
web/src/app/(dashboard)/ai-analysis/page.tsx
web/src/app/(dashboard)/ai-analysis/[symbol]/page.tsx
web/src/components/ai/MultiModelAnalysis.tsx
web/src/components/ai/ConsensusDisplay.tsx
web/src/components/ai/TechnicalAnalysis.tsx
web/src/hooks/useAIAnalysis.ts
```

### 4. 取引画面 (4-5日)

#### 4.1 注文機能
- **注文タイプ**
  - 成行注文・指値注文・逆指値注文
  - OCO注文・IFD注文
- **リアルタイム価格表示**
  - WebSocket価格更新
  - 板情報表示
  - 約定確認・通知

#### 4.2 ポートフォリオ管理
- **保有銘柄管理**
  - リアルタイム評価額
  - 損益分析・パフォーマンス表示
- **取引履歴**
  - 過去取引一覧
  - P&L分析・税務計算

#### 4.3 実装ファイル
```typescript
web/src/app/(dashboard)/trading/page.tsx
web/src/components/trading/OrderForm.tsx
web/src/components/trading/Portfolio.tsx
web/src/components/trading/TradeHistory.tsx
web/src/hooks/useTrading.ts
```

## 📊 API統合戦略

### Phase 3A対応API群
- **認証**: `/api/v1/auth/*` (4エンドポイント)
- **バックテスト**: `/api/v1/services/backtest/*` (6エンドポイント)
- **AI分析**: `/api/v1/ai/*` (8エンドポイント)
- **取引**: `/api/v1/trading/*` (9エンドポイント)

### WebSocket統合
- **リアルタイム更新**
  - `price_update`: 価格変動通知
  - `backtest_progress`: バックテスト進捗
  - `ai_analysis`: AI分析完了通知
  - `trade_execution`: 取引実行通知

## 🎨 UI/UXデザイン方針

### デザインシステム統一
- **カラーパレット**: 既存のkaboom design variables継承
- **コンポーネント**: 再利用可能なUI部品構築
- **レスポンシブ**: モバイル・タブレット対応

### アニメーション・インタラクション
- **リアルタイム更新**: 視覚的フィードバック
- **Loading状態**: Skeleton UI・Progress indicator
- **エラーハンドリング**: ユーザーフレンドリーなエラー表示

## 🧪 テスト戦略

### コンポーネントテスト
```bash
# 各機能のテスト実装
web/src/__tests__/auth/
web/src/__tests__/backtest/
web/src/__tests__/ai-analysis/
web/src/__tests__/trading/
```

### E2Eテスト
```bash
# Playwright統合テスト
web/tests/e2e/auth.spec.ts
web/tests/e2e/backtest.spec.ts
web/tests/e2e/ai-analysis.spec.ts
web/tests/e2e/trading.spec.ts
```

## ⏱️ 開発スケジュール

### Week 1: 認証システム
- Day 1-2: ログイン画面・Supabase統合
- Day 3-4: ユーザー管理・権限制御

### Week 2: バックテスト機能 ⚡
- Day 1-2: 戦略設定・実行機能
- Day 3-5: 結果分析・視覚化

### Week 3: AI分析画面
- Day 1-2: マルチモデル分析表示
- Day 3-4: 詳細分析・合意形成UI

### Week 4: 取引機能
- Day 1-3: 注文機能・ポートフォリオ管理
- Day 4-5: 取引履歴・統合テスト

## 🔧 技術的考慮事項

### パフォーマンス最適化
- **コード分割**: 機能別動的インポート
- **キャッシュ戦略**: Next.js 15 cache API活用
- **WebSocket最適化**: 必要な通知のみ受信

### セキュリティ
- **認証トークン**: 安全なJWT管理
- **HTTPS強制**: 本番環境セキュア通信
- **XSS対策**: サニタイゼーション徹底

## 📈 成功指標

### 機能完成度
- [ ] 認証ログイン: 100%動作
- [ ] バックテスト: 戦略実行・結果分析完了
- [ ] AI分析: マルチモデル表示完了
- [ ] 取引: 基本注文機能完了

### 品質指標
- テストカバレッジ: 80%以上
- Core Web Vitals: Good評価
- TypeScript: strict mode対応

---

**Phase 3A完了により、Kaboom株式自動売買システムが完全なユーザー向けプラットフォームとして完成予定**