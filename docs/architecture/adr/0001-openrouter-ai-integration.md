# ADR-0001: OpenRouter統一AI統合戦略

## Status
**ACCEPTED** - 2024-08-24

## Context

Kaboom株式自動売買システムでは、以下のAI分析機能が必要：

### 要求される機能
- **テクニカル分析**: チャート画像を元にした売買判断
- **市場センチメント分析**: ニュース・SNSデータからの感情分析
- **リスク評価**: ポートフォリオリスク・ボラティリティ分析
- **複数モデル比較**: 異なるAIモデルでの判断比較・合意形成

### 技術的課題
- **複数AIプロバイダー管理**: OpenAI、Google、Anthropic等の個別API管理
- **API KEY管理**: プロバイダー毎の認証情報管理
- **レート制限**: 各社異なる制限への対応
- **コスト管理**: 分散したAI利用料金の追跡・管理
- **エラーハンドリング**: プロバイダー固有のエラー形式への対応
- **モデル切り替え**: 実験・比較のためのモデル変更容易性

### 検討した選択肢

#### Option 1: 直接統合方式
各AIプロバイダーのAPIを直接呼び出し

**利点**:
- 最新機能への即座のアクセス
- プロバイダー固有の最適化

**欠点**:
- 複数API KEY管理の複雑性
- 異なるレスポンス形式への対応
- エラーハンドリングの複雑化
- 個別レート制限管理
- コスト追跡の困難

#### Option 2: OpenRouter統合方式  
OpenRouter（https://openrouter.ai/）を統一APIとして採用

**利点**:
- 単一API KEY管理
- 統一されたレスポンス形式
- 20+ モデルへのアクセス
- 一元化されたコスト管理
- 統一されたエラーハンドリング
- モデル切り替えの容易性

**欠点**:
- OpenRouter依存リスク
- 若干のレイテンシ増加（プロキシ経由）
- プロバイダー固有機能の制限

#### Option 3: LangChain統合
LangChainのプロバイダー抽象化を利用

**利点**:
- 豊富なツールチェーン
- プロバイダー抽象化

**欠点**:
- 過剰な機能（今回の用途には重い）
- API KEY管理は依然として複雑
- コスト管理の困難

## Decision

**OpenRouter統一AI統合戦略**を採用する

### 具体的な統合方針

#### 基本設定
```python
OPENROUTER_CONFIG = {
    "api_endpoint": "https://openrouter.ai/api/v1",
    "api_key": "${OPENROUTER_API_KEY}",
    "default_models": {
        "technical_analysis": "openai/gpt-4-turbo-preview",
        "sentiment_analysis": "anthropic/claude-3-sonnet",
        "risk_assessment": "google/gemini-pro-vision",
        "general_analysis": "meta-llama/llama-2-70b-chat"
    },
    "fallback_model": "openai/gpt-3.5-turbo",
    "timeout": 30,
    "max_retries": 3
}
```

#### モデル切り替え戦略
```python
# 設定による動的切り替え
analysis_request = {
    "symbol": "7203",
    "models": [
        "openai/gpt-4-turbo-preview",
        "anthropic/claude-3-sonnet",
        "google/gemini-pro-vision"
    ],
    "analysis_types": ["technical", "sentiment", "risk"]
}
```

#### コスト管理統合
- OpenRouterダッシュボードでの一元管理
- API経由でのリアルタイム使用量取得
- プロジェクト別・ユーザー別コスト配分

## Consequences

### 正の影響 ✅

1. **開発効率向上**
   - 単一API統合によりコード複雑性が大幅減少
   - モデル追加・変更が設定変更のみで可能

2. **運用負荷軽減**
   - API KEY管理が一元化（1個のみ）
   - 統一されたエラーハンドリング
   - 一元化されたログ・監視

3. **コスト管理改善**
   - 全AI使用量をOpenRouterダッシュボードで可視化
   - プロジェクト別・機能別の詳細な使用量分析
   - 予算アラート設定

4. **実験・改善の容易性**
   - A/Bテストでのモデル比較が簡単
   - 新モデルの検証コストが低い
   - パフォーマンスデータの統一収集

### 負の影響 ❌

1. **外部依存リスク**
   - OpenRouterサービス障害時の全AI機能停止
   - **軽減策**: フォールバック機能、直接API統合の準備

2. **レイテンシ増加**
   - プロキシ経由による10-50ms程度の遅延
   - **影響評価**: 株式分析では許容範囲（数秒～数分の処理時間）

3. **プロバイダー固有機能制限**
   - 一部の最新・実験機能へのアクセス制限
   - **軽減策**: 重要機能は直接統合オプションを保持

### 実装スケジュール

#### Phase 1: 基盤統合（Week 1-2）
- OpenRouter APIクライアント実装
- 基本的なテクニカル分析機能
- エラーハンドリング・ログ統合

#### Phase 2: 機能拡張（Week 3-4）  
- 複数モデル並列実行
- センチメント・リスク分析追加
- パフォーマンス監視・コスト追跡

#### Phase 3: 最適化（Week 5-6）
- キャッシュ戦略実装
- フォールバック機能
- A/Bテスト機能

### 監視・評価指標

#### 技術指標
- `openrouter_api_latency_seconds` - API応答時間
- `openrouter_api_errors_total` - エラー率
- `ai_analysis_success_rate` - 分析成功率
- `model_performance_score` - モデル別パフォーマンス

#### ビジネス指標
- `ai_analysis_cost_per_request` - リクエスト当たりコスト
- `model_accuracy_comparison` - モデル精度比較
- `user_satisfaction_score` - AI分析結果満足度

### 見直し基準

以下の状況でADRを再評価：

1. **OpenRouterサービス品質低下**
   - 月間稼働率 < 99.5%
   - 平均レイテンシ > 2秒

2. **コスト効率性悪化**  
   - 直接統合比で > 20%コスト増
   - 予想ROI未達成

3. **機能制約による影響**
   - プロバイダー固有機能の必要性が高まった場合
   - リアルタイム要件（< 100ms）が発生した場合

## Related ADRs

- [ADR-0002: WebSocket + Redis Pub/Sub リアルタイム配信](./0002-websocket-redis-pubsub.md) - 予定
- [ADR-0003: Supabase認証戦略](./0003-supabase-auth-strategy.md) - 予定

## References

- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [OpenRouter Supported Models](https://openrouter.ai/models)
- [Architecture Decision Records Template](https://github.com/joelparkerhenderson/architecture-decision-record)