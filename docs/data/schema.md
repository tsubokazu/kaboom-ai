# Kaboom データベース設計書

## Overview

Kaboom株式自動売買システムのデータベーススキーマ設計書です。
Supabase (PostgreSQL) を使用し、認証はSupabase Auth、データ管理はSQLAlchemyで実装します。

## 基本方針

### データベース選択理由
- **Supabase PostgreSQL**: フロントエンドでSupabase Authを使用するため統一
- **リアルタイム機能**: Supabase Realtimeでのデータ変更通知
- **スケーラビリティ**: PostgreSQLの豊富な機能とパフォーマンス
- **開発効率**: Supabase CLIでのローカル開発環境構築

### 設計原則
1. **正規化**: 適度な正規化で整合性とパフォーマンスのバランス
2. **UUID主キー**: 分散システム対応とセキュリティ向上
3. **タイムスタンプ**: 全テーブルにcreated_at, updated_at必須
4. **論理削除**: 重要データは物理削除せず無効化フラグ
5. **インデックス戦略**: クエリパフォーマンス最適化

## テーブル設計

### 1. ユーザー管理（Supabase Auth統合）

#### users (Supabase Authの拡張)
```sql
-- Supabase Auth users テーブルは自動生成されるため、
-- 追加情報は user_profiles テーブルで管理
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL DEFAULT 'basic' 
        CHECK (tier IN ('basic', 'premium', 'enterprise')),
    display_name VARCHAR(100),
    avatar_url TEXT,
    ai_quota_monthly INTEGER DEFAULT 100,
    ai_usage_current INTEGER DEFAULT 0,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS (Row Level Security) 設定
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON user_profiles  
    FOR UPDATE USING (auth.uid() = id);
```

### 2. ポートフォリオ管理

#### portfolios
```sql
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    initial_capital DECIMAL(15,2) NOT NULL CHECK (initial_capital > 0),
    current_balance DECIMAL(15,2) NOT NULL,
    total_invested DECIMAL(15,2) DEFAULT 0,
    total_return DECIMAL(15,2) DEFAULT 0,
    return_percentage DECIMAL(8,4) DEFAULT 0,
    risk_level VARCHAR(10) DEFAULT 'medium' 
        CHECK (risk_level IN ('low', 'medium', 'high')),
    strategy_type VARCHAR(50) DEFAULT 'mixed',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, name),
    CONSTRAINT positive_balance CHECK (current_balance >= 0)
);

-- インデックス
CREATE INDEX idx_portfolios_user_active ON portfolios(user_id, is_active);
CREATE INDEX idx_portfolios_updated ON portfolios(updated_at DESC);

-- RLS設定
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own portfolios" ON portfolios
    USING (auth.uid() = user_id);
```

#### positions (ポジション管理)
```sql
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL, -- 銘柄コード (例: "7203")
    symbol_name VARCHAR(200), -- 銘柄名
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    average_price DECIMAL(10,2) NOT NULL CHECK (average_price > 0),
    current_price DECIMAL(10,2),
    market_value DECIMAL(15,2), -- quantity * current_price
    unrealized_pnl DECIMAL(15,2), -- (current_price - average_price) * quantity
    weight_percentage DECIMAL(5,2), -- ポートフォリオに占める割合
    sector VARCHAR(50),
    last_price_update TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(portfolio_id, symbol)
);

-- インデックス
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_last_update ON positions(last_price_update DESC);

-- RLS設定
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own positions" ON positions
    USING (
        portfolio_id IN (
            SELECT id FROM portfolios WHERE user_id = auth.uid()
        )
    );
```

### 3. 取引管理

#### trades
```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    symbol_name VARCHAR(200),
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price DECIMAL(10,2) NOT NULL CHECK (price > 0),
    total_amount DECIMAL(15,2) NOT NULL, -- quantity * price
    commission DECIMAL(10,2) DEFAULT 0,
    tax DECIMAL(10,2) DEFAULT 0,
    net_amount DECIMAL(15,2) NOT NULL, -- total_amount + commission + tax
    order_type VARCHAR(20) DEFAULT 'market' 
        CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    status VARCHAR(20) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'filled', 'partial', 'cancelled', 'rejected')),
    
    -- AI関連情報
    ai_analysis_id UUID REFERENCES ai_analysis_results(id),
    ai_decision VARCHAR(10) CHECK (ai_decision IN ('buy', 'sell', 'hold')),
    ai_confidence DECIMAL(3,2) CHECK (ai_confidence BETWEEN 0 AND 1),
    
    -- 実行情報
    order_id VARCHAR(100), -- 外部API (立花証券等) のオーダーID
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_price DECIMAL(10,2),
    
    -- 利益/損失計算 (売却時)
    cost_basis DECIMAL(15,2), -- 取得原価
    realized_pnl DECIMAL(15,2), -- 実現損益
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス
CREATE INDEX idx_trades_portfolio_date ON trades(portfolio_id, executed_at DESC);
CREATE INDEX idx_trades_symbol_date ON trades(symbol, executed_at DESC);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_ai_analysis ON trades(ai_analysis_id);

-- RLS設定
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own trades" ON trades
    USING (
        portfolio_id IN (
            SELECT id FROM portfolios WHERE user_id = auth.uid()
        )
    );
```

### 4. AI分析結果（OpenRouter統合）

#### ai_analysis_results
```sql
CREATE TABLE ai_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    symbol_name VARCHAR(200),
    
    -- 分析設定
    analysis_types TEXT[] NOT NULL, -- ['technical', 'sentiment', 'risk']
    models_used TEXT[] NOT NULL, -- ['openai/gpt-4-turbo-preview', 'anthropic/claude-3-sonnet']
    timeframes TEXT[], -- ['1h', '4h', '1d']
    
    -- 集約結果
    final_decision VARCHAR(10) NOT NULL CHECK (final_decision IN ('buy', 'sell', 'hold')),
    consensus_confidence DECIMAL(3,2) CHECK (consensus_confidence BETWEEN 0 AND 1),
    model_agreement DECIMAL(3,2) CHECK (model_agreement BETWEEN 0 AND 1),
    
    -- 個別モデル結果 (JSONB)
    model_results JSONB NOT NULL,
    /*
    例:
    {
      "results": [
        {
          "model": "openai/gpt-4-turbo-preview",
          "analysis_type": "technical",
          "decision": "buy",
          "confidence": 0.85,
          "reasoning": "RSI oversold, MACD bullish crossover",
          "cost_usd": 0.023,
          "processing_time": 2.34
        }
      ]
    }
    */
    
    -- 技術指標データ
    technical_indicators JSONB,
    /*
    例:
    {
      "RSI": 28.5,
      "MACD": {"signal": "bullish", "histogram": 0.12},
      "bollinger": {"position": "lower_band"}
    }
    */
    
    -- 実行メトリクス
    total_cost_usd DECIMAL(8,6) DEFAULT 0,
    processing_time_seconds DECIMAL(6,2),
    chart_image_url TEXT,
    
    -- ステータス
    status VARCHAR(20) DEFAULT 'completed'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- インデックス
CREATE INDEX idx_ai_analysis_user_symbol ON ai_analysis_results(user_id, symbol);
CREATE INDEX idx_ai_analysis_created ON ai_analysis_results(created_at DESC);
CREATE INDEX idx_ai_analysis_status ON ai_analysis_results(status);
CREATE INDEX idx_ai_analysis_decision ON ai_analysis_results(final_decision);

-- JSONB インデックス (GIN)
CREATE INDEX idx_ai_analysis_model_results ON ai_analysis_results 
    USING GIN (model_results);
CREATE INDEX idx_ai_analysis_indicators ON ai_analysis_results 
    USING GIN (technical_indicators);

-- RLS設定
ALTER TABLE ai_analysis_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own AI analysis" ON ai_analysis_results
    USING (auth.uid() = user_id);
```

### 5. バックテスト結果

#### backtest_results
```sql
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- バックテスト設定
    strategy_name VARCHAR(100) NOT NULL,
    strategy_config JSONB NOT NULL,
    /*
    例:
    {
      "name": "multi_ai_consensus",
      "ai_models": ["openai/gpt-4-turbo-preview", "anthropic/claude-3-sonnet"],
      "consensus_threshold": 0.7,
      "decision_weights": {"technical": 0.4, "sentiment": 0.3, "risk": 0.3}
    }
    */
    
    symbols TEXT[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    
    -- 実行結果
    final_capital DECIMAL(15,2),
    total_return DECIMAL(15,2),
    return_percentage DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    max_drawdown_date DATE,
    sharpe_ratio DECIMAL(6,3),
    sortino_ratio DECIMAL(6,3),
    calmar_ratio DECIMAL(6,3),
    
    -- 取引統計
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5,2),
    average_win DECIMAL(15,2),
    average_loss DECIMAL(15,2),
    profit_factor DECIMAL(6,3),
    
    -- 時系列データ (JSONB)
    equity_curve JSONB,
    /*
    例:
    [
      {"date": "2023-01-01", "value": 1000000, "drawdown": 0},
      {"date": "2023-01-02", "value": 1005000, "drawdown": 0}
    ]
    */
    
    trade_history JSONB,
    monthly_returns JSONB,
    
    -- AI使用メトリクス
    ai_total_cost_usd DECIMAL(10,6),
    ai_analysis_count INTEGER,
    average_analysis_time DECIMAL(6,2),
    
    -- 実行情報
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress_percentage DECIMAL(5,2) DEFAULT 0,
    current_date DATE,
    error_message TEXT,
    
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス
CREATE INDEX idx_backtest_user_status ON backtest_results(user_id, status);
CREATE INDEX idx_backtest_created ON backtest_results(created_at DESC);
CREATE INDEX idx_backtest_completed ON backtest_results(completed_at DESC);
CREATE INDEX idx_backtest_performance ON backtest_results(return_percentage DESC);

-- JSONB インデックス
CREATE INDEX idx_backtest_strategy_config ON backtest_results 
    USING GIN (strategy_config);

-- RLS設定
ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own backtests" ON backtest_results
    USING (auth.uid() = user_id);
```

### 6. 市場データ・価格情報

#### market_data
```sql
CREATE TABLE market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    symbol_name VARCHAR(200),
    
    -- 価格情報
    open_price DECIMAL(10,2),
    high_price DECIMAL(10,2),
    low_price DECIMAL(10,2),
    close_price DECIMAL(10,2) NOT NULL,
    volume BIGINT,
    
    -- 変動情報
    price_change DECIMAL(10,2),
    price_change_percent DECIMAL(5,2),
    
    -- 時間軸
    timeframe VARCHAR(10) NOT NULL, -- '1m', '5m', '1h', '1d' etc
    data_date DATE NOT NULL,
    data_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- データソース
    data_source VARCHAR(50) DEFAULT 'yfinance',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(symbol, timeframe, data_timestamp)
);

-- インデックス
CREATE INDEX idx_market_data_symbol_time ON market_data(symbol, timeframe, data_timestamp DESC);
CREATE INDEX idx_market_data_date ON market_data(data_date DESC);
CREATE INDEX idx_market_data_created ON market_data(created_at DESC);

-- パーティショニング (大量データ対応)
-- 月別パーティション推奨
```

### 7. ウォッチリスト・お気に入り

#### watchlists
```sql
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL DEFAULT 'デフォルトリスト',
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, name)
);

CREATE TABLE watchlist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    symbol_name VARCHAR(200),
    
    -- アラート設定
    price_alert_upper DECIMAL(10,2),
    price_alert_lower DECIMAL(10,2),
    volume_alert_threshold BIGINT,
    
    -- メモ・タグ
    notes TEXT,
    tags TEXT[],
    
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(watchlist_id, symbol)
);

-- インデックス
CREATE INDEX idx_watchlist_user ON watchlists(user_id);
CREATE INDEX idx_watchlist_items_list ON watchlist_items(watchlist_id);
CREATE INDEX idx_watchlist_items_symbol ON watchlist_items(symbol);

-- RLS設定
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own watchlists" ON watchlists
    USING (auth.uid() = user_id);

ALTER TABLE watchlist_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own watchlist items" ON watchlist_items
    USING (
        watchlist_id IN (
            SELECT id FROM watchlists WHERE user_id = auth.uid()
        )
    );
```

### 8. システム管理・監査

#### system_settings
```sql
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT false, -- ユーザーに公開するか
    
    updated_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- デフォルト設定
INSERT INTO system_settings (key, value, description, is_public) VALUES
('ai_model_config', '{"default_technical": "openai/gpt-4-turbo-preview"}', 'AI model configuration', false),
('market_hours', '{"start": "09:00", "end": "15:00", "timezone": "Asia/Tokyo"}', 'Market trading hours', true),
('commission_rates', '{"default": 0.001, "premium": 0.0005}', 'Trading commission rates', true);
```

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    action VARCHAR(100) NOT NULL, -- 'trade_executed', 'portfolio_created', etc
    resource_type VARCHAR(50), -- 'portfolio', 'trade', 'ai_analysis'
    resource_id UUID,
    
    -- 変更内容
    old_values JSONB,
    new_values JSONB,
    
    -- メタデータ
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- インデックス
CREATE INDEX idx_audit_user_created ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);

-- パーティショニング (ログデータ量対応)
-- 日別または週別パーティション推奨
```

## データベース関数・トリガー

### 1. 自動更新トリガー
```sql
-- updated_at 自動更新関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにトリガー適用
CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at 
    BEFORE UPDATE ON portfolios 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 他のテーブルも同様に設定
```

### 2. ポートフォリオ統計計算
```sql
-- ポートフォリオパフォーマンス計算関数
CREATE OR REPLACE FUNCTION calculate_portfolio_performance(portfolio_uuid UUID)
RETURNS TABLE (
    total_value DECIMAL(15,2),
    total_return DECIMAL(15,2),
    return_percentage DECIMAL(8,4),
    position_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    WITH portfolio_stats AS (
        SELECT 
            p.initial_capital,
            COALESCE(SUM(pos.market_value), 0) + p.current_balance as current_total,
            COUNT(pos.id) as pos_count
        FROM portfolios p
        LEFT JOIN positions pos ON pos.portfolio_id = p.id
        WHERE p.id = portfolio_uuid
        GROUP BY p.id, p.initial_capital, p.current_balance
    )
    SELECT 
        ps.current_total,
        ps.current_total - ps.initial_capital,
        CASE WHEN ps.initial_capital > 0 
             THEN ((ps.current_total - ps.initial_capital) / ps.initial_capital) * 100
             ELSE 0 
        END,
        ps.pos_count::INTEGER
    FROM portfolio_stats ps;
END;
$$ LANGUAGE plpgsql;
```

### 3. AI使用量追跡
```sql
-- AI使用量更新関数
CREATE OR REPLACE FUNCTION update_ai_usage(user_uuid UUID, cost_usd DECIMAL)
RETURNS void AS $$
BEGIN
    INSERT INTO user_profiles (id, ai_usage_current)
    VALUES (user_uuid, 1)
    ON CONFLICT (id) 
    DO UPDATE SET 
        ai_usage_current = user_profiles.ai_usage_current + 1,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;
```

## インデックス戦略

### 1. パフォーマンス重要インデックス
```sql
-- 複合インデックス (頻繁なクエリ用)
CREATE INDEX idx_trades_portfolio_status_date ON trades(portfolio_id, status, executed_at DESC);
CREATE INDEX idx_ai_analysis_user_symbol_created ON ai_analysis_results(user_id, symbol, created_at DESC);
CREATE INDEX idx_positions_portfolio_symbol ON positions(portfolio_id, symbol);

-- 部分インデックス (条件付き)
CREATE INDEX idx_trades_active ON trades(portfolio_id, created_at) 
    WHERE status IN ('pending', 'partial');
CREATE INDEX idx_ai_analysis_failed ON ai_analysis_results(user_id, created_at) 
    WHERE status = 'failed';
```

### 2. JSONBクエリ最適化
```sql
-- AI分析結果の特定モデル検索
CREATE INDEX idx_ai_model_openai ON ai_analysis_results 
    USING GIN ((model_results -> 'results')) 
    WHERE model_results -> 'results' @> '[{"model": "openai/gpt-4-turbo-preview"}]';

-- テクニカル指標検索
CREATE INDEX idx_technical_rsi ON ai_analysis_results 
    USING GIN ((technical_indicators -> 'RSI')) 
    WHERE technical_indicators ? 'RSI';
```

## データ整合性・制約

### 1. ビジネスルール制約
```sql
-- ポートフォリオの残高は保有ポジションの合計を超えない
-- (トリガーで実装)

-- 売却数量は保有数量以下
-- (アプリケーションレベルで制御)

-- AI分析の有効期限 (1時間)
CREATE INDEX idx_ai_analysis_fresh ON ai_analysis_results(created_at)
    WHERE created_at > NOW() - INTERVAL '1 hour';
```

### 2. データクリーンアップ
```sql
-- 古いmarket_dataの自動削除 (6ヶ月保持)
CREATE OR REPLACE FUNCTION cleanup_old_market_data()
RETURNS void AS $$
BEGIN
    DELETE FROM market_data 
    WHERE data_timestamp < NOW() - INTERVAL '6 months'
    AND timeframe IN ('1m', '5m'); -- 短期データのみ
END;
$$ LANGUAGE plpgsql;

-- 定期実行 (pg_cronまたはCeleryで)
```

## 移行戦略

### 1. マイグレーション順序
```sql
-- 1. 基本テーブル作成
-- 2. インデックス作成
-- 3. RLS設定
-- 4. 関数・トリガー作成
-- 5. 初期データ投入
-- 6. パフォーマンステスト
```

### 2. Alembic設定例
```python
# alembic/versions/001_initial_schema.py
def upgrade():
    # テーブル作成
    op.create_table('user_profiles', ...)
    
    # インデックス作成
    op.create_index('idx_portfolios_user_active', ...)
    
    # RLS有効化
    op.execute('ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY')
```

## 監視・メンテナンス

### 1. パフォーマンス監視
```sql
-- クエリパフォーマンス統計
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables 
ORDER BY seq_scan DESC;

-- インデックス使用率
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

### 2. データサイズ監視
```sql
-- テーブルサイズ確認
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size,
    pg_total_relation_size(tablename::regclass) as size_bytes
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

## 関連文書

- [API開発計画書](../api-development-plan.md)
- [OpenRouter統合設計](../ai/openrouter-integration.md)
- [エラーカタログ](../api/error-catalog.md)
- [ADR-0001: OpenRouter採用](../architecture/adr/0001-openrouter-ai-integration.md)