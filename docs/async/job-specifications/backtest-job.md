# Backtest Job Specification v1.0

## Overview

OpenRouter統合AI分析を活用したバックテストジョブの詳細仕様書です。
指定した期間・銘柄・戦略で過去データをシミュレーションし、AI判断に基づく取引戦略のパフォーマンスを検証します。

## Job Purpose

以下の機能を提供する包括的なバックテストシステム：
- **戦略検証**: AI分析に基づく取引戦略の過去データでの検証
- **リスク分析**: 最大ドローダウン・シャープレシオ等のリスク指標算出
- **コスト分析**: AI使用料金を含む実際の取引コスト計算
- **比較分析**: 複数戦略・AIモデルの性能比較

## Input Schema

### JSON Input Format
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "backtest_config": {
    "name": "Multi-AI Consensus Strategy Q1 2024",
    "description": "GPT-4 + Claude + Gemini consensus trading strategy",
    "strategy_type": "ai_consensus"
  },
  "strategy_config": {
    "ai_config": {
      "models": [
        {
          "provider": "openai/gpt-4-turbo-preview",
          "analysis_types": ["technical", "risk"],
          "weight": 0.4
        },
        {
          "provider": "anthropic/claude-3-sonnet", 
          "analysis_types": ["sentiment", "technical"],
          "weight": 0.35
        },
        {
          "provider": "google/gemini-pro-vision",
          "analysis_types": ["risk", "technical"],
          "weight": 0.25
        }
      ],
      "consensus_threshold": 0.7,
      "decision_weights": {
        "technical": 0.4,
        "sentiment": 0.3,
        "risk": 0.3
      },
      "confidence_threshold": 0.6
    },
    "trading_rules": {
      "max_position_size": 0.1,
      "stop_loss": -0.05,
      "take_profit": 0.15,
      "rebalance_frequency": "weekly",
      "min_holding_period": "1d"
    }
  },
  "simulation_config": {
    "symbols": ["7203", "9984", "6758", "4063", "8058"],
    "start_date": "2023-01-01",
    "end_date": "2024-01-01", 
    "initial_capital": 10000000,
    "currency": "JPY",
    "market_impact": {
      "enabled": true,
      "impact_model": "sqrt",
      "liquidity_factor": 0.1
    },
    "costs": {
      "commission_rate": 0.001,
      "spread_bps": 5,
      "financing_rate": 0.02,
      "include_ai_costs": true
    }
  },
  "execution_config": {
    "analysis_frequency": "daily",
    "execution_delay": "1h",
    "priority": "normal",
    "save_intermediate": true,
    "generate_reports": true
  }
}
```

### Input Validation Schema
```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from enum import Enum

class StrategyType(str, Enum):
    AI_CONSENSUS = "ai_consensus"
    SINGLE_MODEL = "single_model"
    TECHNICAL_ONLY = "technical_only"
    SENTIMENT_ONLY = "sentiment_only"

class AnalysisFrequency(str, Enum):
    DAILY = "daily"
    HOURLY = "hourly"
    WEEKLY = "weekly"

class AIModelConfig(BaseModel):
    provider: str = Field(..., regex=r'^[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_\.]+$')
    analysis_types: List[str] = Field(..., min_items=1, max_items=3)
    weight: float = Field(..., ge=0.0, le=1.0)
    temperature: Optional[float] = Field(0.1, ge=0.0, le=2.0)

class AIConfig(BaseModel):
    models: List[AIModelConfig] = Field(..., min_items=1, max_items=5)
    consensus_threshold: float = Field(0.7, ge=0.5, le=1.0)
    decision_weights: Dict[str, float] = Field(...)
    confidence_threshold: float = Field(0.6, ge=0.0, le=1.0)
    
    @validator('decision_weights')
    def weights_sum_to_one(cls, v):
        if abs(sum(v.values()) - 1.0) > 0.01:
            raise ValueError('Decision weights must sum to 1.0')
        return v
    
    @validator('models')
    def model_weights_sum_to_one(cls, v):
        total_weight = sum(model.weight for model in v)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError('Model weights must sum to 1.0')
        return v

class TradingRules(BaseModel):
    max_position_size: float = Field(0.1, ge=0.01, le=1.0)
    stop_loss: Optional[float] = Field(-0.05, ge=-0.5, le=0.0)
    take_profit: Optional[float] = Field(0.15, ge=0.0, le=5.0)
    rebalance_frequency: str = Field("weekly", regex=r'^(daily|weekly|monthly)$')
    min_holding_period: str = Field("1d", regex=r'^[0-9]+(d|h)$')

class MarketImpact(BaseModel):
    enabled: bool = True
    impact_model: str = Field("sqrt", regex=r'^(linear|sqrt|log)$')
    liquidity_factor: float = Field(0.1, ge=0.0, le=1.0)

class CostConfig(BaseModel):
    commission_rate: float = Field(0.001, ge=0.0, le=0.01)
    spread_bps: float = Field(5.0, ge=0.0, le=50.0)
    financing_rate: float = Field(0.02, ge=0.0, le=0.1)
    include_ai_costs: bool = True

class SimulationConfig(BaseModel):
    symbols: List[str] = Field(..., min_items=1, max_items=20)
    start_date: date = Field(...)
    end_date: date = Field(...)
    initial_capital: float = Field(..., ge=100000, le=1000000000)
    currency: str = Field("JPY", regex=r'^(JPY|USD)$')
    market_impact: MarketImpact = MarketImpact()
    costs: CostConfig = CostConfig()
    
    @validator('symbols')
    def validate_symbols(cls, v):
        for symbol in v:
            if not re.match(r'^[0-9]{4}$', symbol):
                raise ValueError(f'Invalid symbol format: {symbol}')
        return v
    
    @validator('end_date')
    def end_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v

class ExecutionConfig(BaseModel):
    analysis_frequency: AnalysisFrequency = AnalysisFrequency.DAILY
    execution_delay: str = Field("1h", regex=r'^[0-9]+(m|h)$')
    priority: str = Field("normal", regex=r'^(low|normal|high)$')
    save_intermediate: bool = True
    generate_reports: bool = True

class BacktestJobInput(BaseModel):
    user_id: str = Field(..., regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    backtest_config: Dict[str, Any]
    strategy_config: Dict[str, Any] 
    simulation_config: SimulationConfig
    execution_config: ExecutionConfig = ExecutionConfig()
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "backtest_config": {
                    "name": "AI Consensus Strategy Test",
                    "strategy_type": "ai_consensus"
                },
                "simulation_config": {
                    "symbols": ["7203", "9984"],
                    "start_date": "2023-06-01",
                    "end_date": "2023-12-31",
                    "initial_capital": 10000000
                }
            }
        }
```

## Processing Workflow

### State Machine Definition
```
queued → data_preparation → strategy_initialization → simulation_running → 
results_generation → report_generation → completed
   ↓           ↓                ↓               ↓              ↓
 failed ←── failed ←────────  failed ←────── failed ←────── failed
                                ↓
                           cancelled (user action)
```

### Detailed Processing Steps

#### 1. Job Initialization & Data Preparation (queued → data_preparation)
```python
async def initialize_backtest_job(job_input: BacktestJobInput) -> BacktestContext:
    """バックテストジョブ初期化"""
    
    try:
        # ユーザー権限チェック
        user_tier = await get_user_tier(job_input.user_id)
        if user_tier == 'basic' and len(job_input.simulation_config.symbols) > 3:
            raise PermissionError("Basic users limited to 3 symbols per backtest")
        
        # 期間チェック
        days_span = (job_input.simulation_config.end_date - job_input.simulation_config.start_date).days
        if user_tier == 'basic' and days_span > 90:
            raise PermissionError("Basic users limited to 90-day backtests")
        
        # コンテキスト作成
        context = BacktestContext(
            job_id=str(uuid.uuid4()),
            user_id=job_input.user_id,
            config=job_input,
            status=BacktestStatus.DATA_PREPARATION,
            created_at=datetime.utcnow(),
            estimated_completion=calculate_estimated_completion(job_input)
        )
        
        # 初期状態保存
        await save_backtest_context(context)
        
        # WebSocket通知
        await notify_backtest_status(context.user_id, {
            "job_id": context.job_id,
            "status": "data_preparation",
            "message": "Preparing historical data..."
        })
        
        return context
        
    except Exception as e:
        logger.error(f"Backtest initialization failed: {e}")
        raise BacktestInitializationError(str(e))

async def prepare_historical_data(context: BacktestContext) -> HistoricalDataSet:
    """過去データの準備"""
    
    try:
        symbols = context.config.simulation_config.symbols
        start_date = context.config.simulation_config.start_date
        end_date = context.config.simulation_config.end_date
        
        historical_data = {}
        
        # 各銘柄の過去データ取得
        for symbol in symbols:
            await update_backtest_progress(context.job_id, f"Fetching data for {symbol}...")
            
            # yfinanceから日次データ取得
            stock_data = await fetch_historical_stock_data(
                symbol=f"{symbol}.T",
                start_date=start_date,
                end_date=end_date,
                timeframes=["1d"]  # バックテストは日次ベース
            )
            
            if len(stock_data) < 30:  # 最低30日分のデータが必要
                raise InsufficientDataError(f"Insufficient data for {symbol}")
            
            # テクニカル指標の事前計算
            technical_indicators = await calculate_historical_indicators(stock_data)
            
            historical_data[symbol] = {
                "price_data": stock_data,
                "indicators": technical_indicators,
                "data_quality": assess_data_quality(stock_data)
            }
        
        # ニュースデータ取得 (センチメント分析用)
        news_data = {}
        if any("sentiment" in model.analysis_types 
               for model in context.config.strategy_config.ai_config.models):
            
            for symbol in symbols:
                news_data[symbol] = await fetch_historical_news(
                    symbol, start_date, end_date
                )
        
        dataset = HistoricalDataSet(
            symbols=symbols,
            price_data=historical_data,
            news_data=news_data,
            date_range=(start_date, end_date),
            prepared_at=datetime.utcnow()
        )
        
        await update_backtest_status(context.job_id, BacktestStatus.STRATEGY_INITIALIZATION)
        return dataset
        
    except Exception as e:
        await update_backtest_status(context.job_id, BacktestStatus.FAILED, error=str(e))
        raise DataPreparationError(f"Data preparation failed: {e}")
```

#### 2. Strategy Initialization (strategy_initialization)
```python
async def initialize_trading_strategy(
    context: BacktestContext,
    historical_data: HistoricalDataSet
) -> TradingStrategy:
    """取引戦略の初期化"""
    
    try:
        strategy_config = context.config.strategy_config
        
        # AI モデル設定の検証・初期化
        ai_models = []
        for model_config in strategy_config.ai_config.models:
            # モデル接続テスト
            test_result = await test_ai_model_connection(model_config.provider)
            if not test_result.success:
                logger.warning(f"Model {model_config.provider} unavailable, using fallback")
                fallback_model = get_fallback_model(model_config.provider)
                if fallback_model:
                    model_config.provider = fallback_model
                else:
                    raise ModelUnavailableError(f"No fallback for {model_config.provider}")
            
            ai_models.append(AIModel(
                provider=model_config.provider,
                analysis_types=model_config.analysis_types,
                weight=model_config.weight,
                temperature=model_config.temperature
            ))
        
        # ポートフォリオマネージャー初期化
        portfolio_manager = PortfolioManager(
            initial_capital=context.config.simulation_config.initial_capital,
            symbols=historical_data.symbols,
            max_position_size=strategy_config.trading_rules.max_position_size,
            commission_rate=context.config.simulation_config.costs.commission_rate
        )
        
        # リスク管理システム初期化
        risk_manager = RiskManager(
            stop_loss=strategy_config.trading_rules.stop_loss,
            take_profit=strategy_config.trading_rules.take_profit,
            max_drawdown=0.2,  # 最大20%ドローダウンで停止
            position_size_limits=calculate_position_limits(historical_data)
        )
        
        # 実行エンジン初期化
        execution_engine = ExecutionEngine(
            market_impact_model=context.config.simulation_config.market_impact,
            spread_model=SpreadModel(
                base_spread=context.config.simulation_config.costs.spread_bps / 10000
            ),
            delay_model=DelayModel(
                execution_delay=parse_delay(context.config.execution_config.execution_delay)
            )
        )
        
        strategy = TradingStrategy(
            name=context.config.backtest_config.name,
            ai_models=ai_models,
            portfolio_manager=portfolio_manager,
            risk_manager=risk_manager,
            execution_engine=execution_engine,
            consensus_threshold=strategy_config.ai_config.consensus_threshold,
            confidence_threshold=strategy_config.ai_config.confidence_threshold
        )
        
        await update_backtest_status(context.job_id, BacktestStatus.SIMULATION_RUNNING)
        return strategy
        
    except Exception as e:
        await update_backtest_status(context.job_id, BacktestStatus.FAILED, error=str(e))
        raise StrategyInitializationError(f"Strategy initialization failed: {e}")
```

#### 3. Simulation Execution (simulation_running)
```python
async def execute_backtest_simulation(
    context: BacktestContext,
    strategy: TradingStrategy,
    historical_data: HistoricalDataSet
) -> BacktestResults:
    """バックテストシミュレーション実行"""
    
    simulation_state = SimulationState(
        current_date=context.config.simulation_config.start_date,
        end_date=context.config.simulation_config.end_date,
        portfolio=strategy.portfolio_manager.get_portfolio(),
        trade_log=[],
        ai_decisions=[],
        performance_metrics=PerformanceMetrics(),
        total_ai_cost=0.0
    )
    
    try:
        # 日次シミュレーションループ
        while simulation_state.current_date <= simulation_state.end_date:
            
            # キャンセルチェック
            if await check_job_cancelled(context.job_id):
                await update_backtest_status(context.job_id, BacktestStatus.CANCELLED)
                return None
            
            # 進捗更新 (10日ごと)
            if simulation_state.current_date.day % 10 == 0:
                progress = calculate_progress(simulation_state.current_date, 
                                            context.config.simulation_config.start_date,
                                            context.config.simulation_config.end_date)
                
                await update_backtest_progress(context.job_id, progress, {
                    "current_date": simulation_state.current_date.isoformat(),
                    "current_portfolio_value": simulation_state.portfolio.total_value,
                    "total_trades": len(simulation_state.trade_log),
                    "current_ai_cost": simulation_state.total_ai_cost
                })
            
            # 市場開場日チェック
            if not is_market_open(simulation_state.current_date):
                simulation_state.current_date += timedelta(days=1)
                continue
            
            # 当日の市場データ取得
            daily_market_data = extract_daily_data(historical_data, simulation_state.current_date)
            if not daily_market_data:
                simulation_state.current_date += timedelta(days=1)
                continue
            
            # AI分析実行 (設定された頻度で)
            if should_run_analysis(simulation_state.current_date, context.config.execution_config.analysis_frequency):
                
                ai_decisions = await run_historical_ai_analysis(
                    strategy=strategy,
                    market_data=daily_market_data,
                    current_date=simulation_state.current_date,
                    portfolio=simulation_state.portfolio
                )
                
                simulation_state.ai_decisions.extend(ai_decisions)
                
                # AI分析コスト累計
                for decision in ai_decisions:
                    simulation_state.total_ai_cost += decision.cost_usd
            
            # 取引判断・実行
            trades = await execute_daily_trading(
                strategy=strategy,
                ai_decisions=simulation_state.ai_decisions,
                market_data=daily_market_data,
                portfolio=simulation_state.portfolio,
                current_date=simulation_state.current_date
            )
            
            simulation_state.trade_log.extend(trades)
            
            # ポートフォリオ更新
            await update_portfolio_valuation(
                simulation_state.portfolio,
                daily_market_data,
                simulation_state.current_date
            )
            
            # パフォーマンス指標更新
            simulation_state.performance_metrics.update(
                simulation_state.portfolio,
                simulation_state.current_date
            )
            
            # リスク管理チェック
            risk_action = strategy.risk_manager.check_risk_limits(
                simulation_state.portfolio,
                simulation_state.performance_metrics
            )
            
            if risk_action == RiskAction.EMERGENCY_EXIT:
                logger.warning("Emergency exit triggered due to risk limits")
                # 全ポジション強制決済
                emergency_trades = await execute_emergency_liquidation(
                    simulation_state.portfolio,
                    daily_market_data,
                    simulation_state.current_date
                )
                simulation_state.trade_log.extend(emergency_trades)
                break
            
            simulation_state.current_date += timedelta(days=1)
        
        # 最終状態の処理
        final_results = await finalize_simulation_results(
            context=context,
            simulation_state=simulation_state,
            strategy=strategy
        )
        
        await update_backtest_status(context.job_id, BacktestStatus.RESULTS_GENERATION)
        return final_results
        
    except Exception as e:
        await update_backtest_status(context.job_id, BacktestStatus.FAILED, error=str(e))
        raise SimulationExecutionError(f"Simulation execution failed: {e}")

async def run_historical_ai_analysis(
    strategy: TradingStrategy,
    market_data: DailyMarketData,
    current_date: date,
    portfolio: Portfolio
) -> List[AIDecision]:
    """過去データでのAI分析シミュレーション"""
    
    decisions = []
    
    # 各AIモデルで並列分析
    analysis_tasks = []
    for ai_model in strategy.ai_models:
        
        # 過去データからその時点で利用可能な情報のみを使用
        available_data = create_point_in_time_data(market_data, current_date)
        
        task = simulate_ai_analysis(
            model=ai_model,
            market_data=available_data,
            analysis_date=current_date,
            portfolio=portfolio
        )
        analysis_tasks.append(task)
    
    # 並列実行
    analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
    
    # 結果統合
    valid_results = [r for r in analysis_results if not isinstance(r, Exception)]
    
    if valid_results:
        # 合意形成
        consensus_decision = form_consensus(valid_results, strategy.consensus_threshold)
        decisions.append(consensus_decision)
    
    return decisions

async def simulate_ai_analysis(
    model: AIModel,
    market_data: PointInTimeData,
    analysis_date: date,
    portfolio: Portfolio
) -> AIDecision:
    """単一AIモデルの過去時点での分析シミュレーション"""
    
    # Note: 実際のOpenRouter APIは呼び出さず、
    # 事前に計算済みの分析結果を使用するか、
    # 簡略化されたルールベース判断を実行
    
    if USE_PRECOMPUTED_AI_RESULTS:
        # 事前計算済み結果の使用
        cached_result = await get_cached_ai_decision(
            model.provider,
            market_data.symbol,
            analysis_date
        )
        if cached_result:
            return cached_result
    
    # リアルタイムAI分析 (コスト最適化のため制限的に使用)
    if should_use_live_ai_analysis(analysis_date, model.provider):
        return await call_openrouter_for_historical_analysis(
            model=model,
            market_data=market_data,
            analysis_date=analysis_date
        )
    
    # ルールベース分析 (フォールバック)
    return simulate_rule_based_decision(model, market_data, analysis_date)
```

#### 4. Results Generation & Reporting (results_generation → report_generation)
```python
async def generate_backtest_results(
    context: BacktestContext,
    simulation_results: BacktestResults
) -> ComprehensiveResults:
    """包括的なバックテスト結果生成"""
    
    try:
        # 基本パフォーマンス指標
        performance_summary = calculate_performance_summary(
            trades=simulation_results.trade_log,
            initial_capital=context.config.simulation_config.initial_capital,
            final_portfolio=simulation_results.final_portfolio
        )
        
        # リスク指標
        risk_metrics = calculate_risk_metrics(
            equity_curve=simulation_results.equity_curve,
            trades=simulation_results.trade_log,
            benchmark_data=await get_benchmark_data(
                context.config.simulation_config.start_date,
                context.config.simulation_config.end_date
            )
        )
        
        # AI分析統計
        ai_statistics = analyze_ai_performance(
            ai_decisions=simulation_results.ai_decisions,
            trades=simulation_results.trade_log,
            total_cost=simulation_results.total_ai_cost
        )
        
        # 月別・年別パフォーマンス
        periodic_performance = calculate_periodic_returns(
            equity_curve=simulation_results.equity_curve,
            frequency=['monthly', 'quarterly', 'yearly']
        )
        
        # セクター・銘柄別分析
        sector_analysis = analyze_sector_performance(
            trades=simulation_results.trade_log,
            symbols=context.config.simulation_config.symbols
        )
        
        # ドローダウン分析
        drawdown_analysis = analyze_drawdowns(
            equity_curve=simulation_results.equity_curve
        )
        
        comprehensive_results = ComprehensiveResults(
            job_id=context.job_id,
            backtest_config=context.config,
            performance_summary=performance_summary,
            risk_metrics=risk_metrics,
            ai_statistics=ai_statistics,
            periodic_performance=periodic_performance,
            sector_analysis=sector_analysis,
            drawdown_analysis=drawdown_analysis,
            trade_log=simulation_results.trade_log[:1000],  # 最初の1000件
            equity_curve=simulation_results.equity_curve,
            generated_at=datetime.utcnow()
        )
        
        # データベースに保存
        await save_backtest_results(comprehensive_results)
        
        await update_backtest_status(context.job_id, BacktestStatus.REPORT_GENERATION)
        return comprehensive_results
        
    except Exception as e:
        await update_backtest_status(context.job_id, BacktestStatus.FAILED, error=str(e))
        raise ResultsGenerationError(f"Results generation failed: {e}")

async def generate_backtest_reports(
    context: BacktestContext,
    results: ComprehensiveResults
) -> BacktestReports:
    """バックテストレポート生成"""
    
    try:
        reports = BacktestReports(job_id=context.job_id, reports=[])
        
        # 1. エクイティカーブチャート
        equity_chart = await generate_equity_curve_chart(
            equity_data=results.equity_curve,
            benchmark_data=await get_benchmark_data(
                context.config.simulation_config.start_date,
                context.config.simulation_config.end_date
            ),
            title=f"{context.config.backtest_config.name} - Equity Curve"
        )
        reports.reports.append(ChartReport(
            type="equity_curve",
            title="Portfolio Value Over Time",
            image_url=await upload_chart(equity_chart, f"{context.job_id}_equity.png"),
            description="Portfolio value progression compared to benchmark"
        ))
        
        # 2. ドローダウンチャート
        drawdown_chart = await generate_drawdown_chart(
            drawdown_data=results.drawdown_analysis.drawdown_series,
            title=f"{context.config.backtest_config.name} - Drawdown Analysis"
        )
        reports.reports.append(ChartReport(
            type="drawdown",
            title="Portfolio Drawdown",
            image_url=await upload_chart(drawdown_chart, f"{context.job_id}_drawdown.png"),
            description=f"Maximum drawdown: {results.risk_metrics.max_drawdown:.2%}"
        ))
        
        # 3. 月次リターンヒートマップ
        monthly_heatmap = await generate_monthly_returns_heatmap(
            monthly_returns=results.periodic_performance.monthly_returns,
            title=f"{context.config.backtest_config.name} - Monthly Returns"
        )
        reports.reports.append(ChartReport(
            type="monthly_heatmap",
            title="Monthly Returns Heatmap",
            image_url=await upload_chart(monthly_heatmap, f"{context.job_id}_monthly.png"),
            description="Monthly return distribution over backtest period"
        ))
        
        # 4. AI分析統計チャート
        ai_performance_chart = await generate_ai_performance_chart(
            ai_stats=results.ai_statistics,
            title=f"{context.config.backtest_config.name} - AI Model Performance"
        )
        reports.reports.append(ChartReport(
            type="ai_performance",
            title="AI Model Analysis",
            image_url=await upload_chart(ai_performance_chart, f"{context.job_id}_ai.png"),
            description=f"AI analysis accuracy: {results.ai_statistics.overall_accuracy:.1%}"
        ))
        
        # 5. 詳細レポートPDF生成
        if context.config.execution_config.generate_reports:
            pdf_report = await generate_pdf_report(context, results)
            reports.reports.append(DocumentReport(
                type="comprehensive_pdf",
                title="Comprehensive Backtest Report",
                file_url=await upload_document(pdf_report, f"{context.job_id}_report.pdf"),
                description="Complete backtest analysis with all metrics and charts"
            ))
        
        await update_backtest_status(context.job_id, BacktestStatus.COMPLETED)
        return reports
        
    except Exception as e:
        await update_backtest_status(context.job_id, BacktestStatus.FAILED, error=str(e))
        raise ReportGenerationError(f"Report generation failed: {e}")
```

## Output Schema

### Success Response
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "backtest_config": {
    "name": "Multi-AI Consensus Strategy Q1 2024",
    "strategy_type": "ai_consensus",
    "symbols": ["7203", "9984", "6758"],
    "date_range": {
      "start": "2023-01-01",
      "end": "2024-01-01"
    }
  },
  "performance_summary": {
    "initial_capital": 10000000,
    "final_capital": 12750000,
    "total_return": 2750000,
    "total_return_percentage": 27.5,
    "annualized_return": 27.5,
    "benchmark_return": 15.2,
    "excess_return": 12.3,
    "total_trades": 156,
    "winning_trades": 89,
    "losing_trades": 67,
    "win_rate": 57.1,
    "average_win": 45600,
    "average_loss": -23800,
    "profit_factor": 1.71,
    "largest_win": 234000,
    "largest_loss": -87000
  },
  "risk_metrics": {
    "volatility": 16.8,
    "sharpe_ratio": 1.64,
    "sortino_ratio": 2.31,
    "calmar_ratio": 2.45,
    "max_drawdown": -8.7,
    "max_drawdown_duration": 23,
    "var_95": -89000,
    "cvar_95": -134000,
    "beta": 0.87,
    "alpha": 12.3,
    "information_ratio": 1.42
  },
  "ai_statistics": {
    "total_analyses": 312,
    "total_ai_cost_usd": 156.78,
    "average_cost_per_analysis": 0.503,
    "cost_as_percent_of_return": 0.57,
    "model_performance": {
      "openai/gpt-4-turbo-preview": {
        "accuracy": 68.5,
        "precision": 71.2,
        "recall": 65.8,
        "total_cost": 89.34,
        "avg_confidence": 0.743
      },
      "anthropic/claude-3-sonnet": {
        "accuracy": 64.2,
        "precision": 67.1,
        "recall": 61.3,
        "total_cost": 45.67,
        "avg_confidence": 0.681
      },
      "google/gemini-pro-vision": {
        "accuracy": 61.8,
        "precision": 63.9,
        "recall": 59.7,
        "total_cost": 21.77,
        "avg_confidence": 0.657
      }
    },
    "consensus_accuracy": 73.4,
    "consensus_usage_rate": 78.2
  },
  "periodic_performance": {
    "monthly_returns": {
      "2023-01": 3.2,
      "2023-02": -1.8,
      "2023-03": 5.7,
      "2023-04": 2.1,
      "...": "..."
    },
    "quarterly_returns": {
      "2023-Q1": 7.1,
      "2023-Q2": 4.8,
      "2023-Q3": 6.3,
      "2023-Q4": 9.3
    },
    "best_month": {
      "period": "2023-11",
      "return": 8.9
    },
    "worst_month": {
      "period": "2023-08",
      "return": -4.2
    }
  },
  "execution_metrics": {
    "total_processing_time": 1847,
    "data_preparation_time": 234,
    "simulation_time": 1456,
    "report_generation_time": 157,
    "ai_analysis_time": 892,
    "peak_memory_usage": "2.4GB",
    "total_api_calls": 312,
    "cache_hit_rate": 23.4
  },
  "reports": [
    {
      "type": "equity_curve",
      "title": "Portfolio Value Over Time",
      "image_url": "https://cdn.example.com/charts/550e8400_equity.png",
      "description": "Portfolio value progression compared to Nikkei 225"
    },
    {
      "type": "comprehensive_pdf",
      "title": "Comprehensive Backtest Report", 
      "file_url": "https://cdn.example.com/reports/550e8400_report.pdf",
      "description": "Complete 24-page analysis with all metrics"
    }
  ],
  "created_at": "2024-01-15T09:00:00Z",
  "started_at": "2024-01-15T09:00:15Z",
  "completed_at": "2024-01-15T09:30:47Z"
}
```

### Progress Response (during execution)
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "simulation_running",
  "progress": {
    "completion_percentage": 45.3,
    "current_stage": "simulation_running",
    "current_date": "2023-06-15",
    "days_completed": 165,
    "days_total": 365,
    "estimated_remaining": "00:12:30"
  },
  "intermediate_results": {
    "current_portfolio_value": 10756000,
    "current_return": 7.56,
    "trades_executed": 67,
    "ai_analyses_completed": 142,
    "current_ai_cost": 71.23,
    "current_drawdown": -2.1,
    "last_significant_trade": {
      "symbol": "9984",
      "action": "buy",
      "quantity": 100,
      "price": 8950,
      "date": "2023-06-14"
    }
  },
  "performance_preview": {
    "ytd_return": 7.56,
    "win_rate": 59.7,
    "recent_trades": 8,
    "ai_accuracy": 71.2
  }
}
```

## Idempotency Strategy

### Natural Key Definition
```python
def generate_backtest_idempotency_key(job_input: BacktestJobInput) -> str:
    """バックテスト冪等性キー生成"""
    
    # 設定のハッシュ化
    config_data = {
        "symbols": sorted(job_input.simulation_config.symbols),
        "start_date": job_input.simulation_config.start_date.isoformat(),
        "end_date": job_input.simulation_config.end_date.isoformat(),
        "strategy_config": job_input.strategy_config,
        "initial_capital": job_input.simulation_config.initial_capital
    }
    
    config_hash = hashlib.sha256(
        json.dumps(config_data, sort_keys=True).encode()
    ).hexdigest()[:16]
    
    natural_key = f"{job_input.user_id}:{config_hash}"
    return natural_key

async def check_existing_backtest(idempotency_key: str) -> Optional[ComprehensiveResults]:
    """既存バックテストの確認"""
    
    # 完了済みバックテストの確認 (30日間有効)
    existing = await db.execute("""
        SELECT * FROM backtest_results 
        WHERE idempotency_key = $1 
        AND status = 'completed'
        AND completed_at > NOW() - INTERVAL '30 days'
        ORDER BY completed_at DESC
        LIMIT 1
    """, idempotency_key)
    
    if existing:
        return ComprehensiveResults.from_db_row(existing)
    
    return None
```

## SLA & Performance Targets

### Service Level Objectives
| メトリック | 目標値 | 測定方法 |
|-----------|--------|---------|
| **Small Backtest** (1-3 symbols, 90 days) | < 5分 | 完了までの時間 |
| **Medium Backtest** (4-10 symbols, 1年) | < 20分 | 完了までの時間 |
| **Large Backtest** (10+ symbols, 2年+) | < 60分 | 完了までの時間 |
| **Success Rate** | > 95% | 正常完了/全実行 |
| **AI Cost Efficiency** | < $1.00/年・銘柄 | AI API使用料 |
| **Memory Usage** | < 4GB peak | システムリソース |

### Performance Optimizations

#### 1. データ最適化
```python
# 並列データ取得
MAX_CONCURRENT_SYMBOL_FETCH = 5
SYMBOL_FETCH_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_SYMBOL_FETCH)

# データキャッシュ
HISTORICAL_DATA_CACHE_DAYS = 7
TECHNICAL_INDICATORS_CACHE_HOURS = 24
```

#### 2. AI分析最適化
```python
# AI分析頻度の動的調整
def optimize_analysis_frequency(market_volatility: float, portfolio_size: float) -> str:
    if market_volatility > 0.3:
        return "daily"
    elif portfolio_size > 50000000:  # 5000万円以上
        return "daily" 
    else:
        return "weekly"  # コスト削減

# バッチ分析
AI_BATCH_SIZE = 10  # 10銘柄まとめて分析
AI_BATCH_TIMEOUT = 180  # 3分タイムアウト
```

#### 3. メモリ管理
```python
# ストリーミング処理
EQUITY_CURVE_BATCH_SIZE = 100  # 100日分ずつ処理
TRADE_LOG_STREAMING = True  # 大量取引ログのストリーミング処理

# 中間結果の保存
SAVE_INTERMEDIATE_FREQUENCY = 30  # 30日ごと
```

## Error Handling & Recovery

### Checkpoint & Resume Strategy
```python
class BacktestCheckpoint:
    """バックテスト中断・再開機能"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
    
    async def save_checkpoint(self, simulation_state: SimulationState):
        """チェックポイント保存"""
        checkpoint_data = {
            "current_date": simulation_state.current_date.isoformat(),
            "portfolio": simulation_state.portfolio.to_dict(),
            "trade_log": [t.to_dict() for t in simulation_state.trade_log[-100:]],  # 直近100件
            "ai_decisions": [d.to_dict() for d in simulation_state.ai_decisions[-50:]],  # 直近50件
            "performance_metrics": simulation_state.performance_metrics.to_dict(),
            "total_ai_cost": simulation_state.total_ai_cost
        }
        
        await redis_client.setex(
            f"backtest_checkpoint:{self.job_id}",
            86400,  # 24時間保持
            json.dumps(checkpoint_data)
        )
    
    async def load_checkpoint(self) -> Optional[SimulationState]:
        """チェックポイント復元"""
        checkpoint_json = await redis_client.get(f"backtest_checkpoint:{self.job_id}")
        if checkpoint_json:
            data = json.loads(checkpoint_json)
            return SimulationState.from_dict(data)
        return None
    
    async def resume_from_checkpoint(self, context: BacktestContext) -> SimulationState:
        """中断から再開"""
        checkpoint = await self.load_checkpoint()
        if checkpoint:
            logger.info(f"Resuming backtest from {checkpoint.current_date}")
            return checkpoint
        else:
            logger.info("No checkpoint found, starting fresh")
            return SimulationState.create_initial(context)
```

### Resource Management
```python
class ResourceManager:
    """リソース管理・制限"""
    
    @staticmethod
    async def check_resource_limits(job_input: BacktestJobInput) -> None:
        """リソース制限チェック"""
        
        # 同時実行制限
        active_backtests = await count_active_backtests(job_input.user_id)
        user_tier = await get_user_tier(job_input.user_id)
        
        limits = {
            'basic': 1,
            'premium': 3, 
            'enterprise': 10
        }
        
        if active_backtests >= limits.get(user_tier, 1):
            raise ResourceLimitError("Maximum concurrent backtests exceeded")
        
        # メモリ使用量予測
        estimated_memory = estimate_memory_usage(job_input)
        if estimated_memory > MAX_MEMORY_PER_BACKTEST:
            raise ResourceLimitError(f"Estimated memory usage ({estimated_memory:.1f}GB) exceeds limit")
        
        # 実行時間予測
        estimated_time = estimate_execution_time(job_input)
        if estimated_time > MAX_EXECUTION_TIME:
            raise ResourceLimitError(f"Estimated execution time exceeds limit")

def estimate_memory_usage(job_input: BacktestJobInput) -> float:
    """メモリ使用量予測"""
    symbols_count = len(job_input.simulation_config.symbols)
    days_count = (job_input.simulation_config.end_date - job_input.simulation_config.start_date).days
    
    # 経験式: symbols * days * 0.001GB + base overhead
    estimated_gb = symbols_count * days_count * 0.001 + 0.5
    return min(estimated_gb, 8.0)  # 最大8GB
```

## Integration Points

### Celery Task Definition
```python
@celery_app.task(
    bind=True,
    max_retries=1,  # バックテストは基本的に1回のみ
    time_limit=7200,  # 2時間でハードタイムアウト
    soft_time_limit=6900  # 1時間55分でソフトタイムアウト
)
async def execute_backtest_task(self, job_input_json: str) -> str:
    """バックテストCeleryタスク"""
    
    job_input = BacktestJobInput.parse_raw(job_input_json)
    checkpoint_manager = BacktestCheckpoint(self.request.id)
    
    try:
        # リソース制限チェック
        await ResourceManager.check_resource_limits(job_input)
        
        # 冪等性チェック
        idempotency_key = generate_backtest_idempotency_key(job_input)
        existing_result = await check_existing_backtest(idempotency_key)
        if existing_result:
            return existing_result.json()
        
        # チェックポイントから再開または新規開始
        context = await initialize_backtest_job(job_input)
        context.job_id = self.request.id  # CeleryタスクIDを使用
        
        simulation_state = await checkpoint_manager.resume_from_checkpoint(context)
        
        # バックテスト実行
        historical_data = await prepare_historical_data(context)
        strategy = await initialize_trading_strategy(context, historical_data)
        
        # 定期的なチェックポイント保存付きでシミュレーション実行
        async def simulation_with_checkpoints():
            while simulation_state.current_date <= simulation_state.end_date:
                # 通常の1日処理
                await process_single_day(context, strategy, historical_data, simulation_state)
                
                # チェックポイント保存 (毎週)
                if simulation_state.current_date.weekday() == 6:  # 日曜日
                    await checkpoint_manager.save_checkpoint(simulation_state)
                
                simulation_state.current_date += timedelta(days=1)
            
            return simulation_state
        
        final_simulation_state = await simulation_with_checkpoints()
        results = await generate_backtest_results(context, final_simulation_state)
        
        # 成功時はチェックポイントクリーンアップ
        await checkpoint_manager.cleanup()
        
        return results.json()
        
    except Exception as e:
        logger.error(f"Backtest execution failed: {e}", exc_info=True)
        
        # 失敗時でもチェックポイント保存 (再開可能にするため)
        if 'simulation_state' in locals():
            await checkpoint_manager.save_checkpoint(simulation_state)
        
        # リトライしない（バックテストは重い処理のため）
        await update_backtest_status(self.request.id, BacktestStatus.FAILED, error=str(e))
        raise
```

### API Endpoint Integration
```python
@router.post("/backtest/run", response_model=schemas.BacktestResponse)
async def submit_backtest(
    request: schemas.BacktestRequest,
    current_user: models.User = Depends(get_current_user)
) -> schemas.BacktestResponse:
    """バックテストジョブ投入エンドポイント"""
    
    # ユーザー権限チェック
    if current_user.tier == 'basic' and len(request.simulation_config.symbols) > 3:
        raise HTTPException(
            status_code=403,
            detail="Basic plan limited to 3 symbols per backtest"
        )
    
    # バックテスト作成
    job_input = BacktestJobInput(
        user_id=str(current_user.id),
        backtest_config=request.backtest_config,
        strategy_config=request.strategy_config,
        simulation_config=request.simulation_config,
        execution_config=request.execution_config
    )
    
    # 冪等性チェック
    idempotency_key = generate_backtest_idempotency_key(job_input)
    existing_result = await check_existing_backtest(idempotency_key)
    if existing_result:
        return schemas.BacktestResponse(
            job_id=existing_result.job_id,
            status="completed",
            estimated_completion=None,
            result=existing_result
        )
    
    # リソース制限チェック
    try:
        await ResourceManager.check_resource_limits(job_input)
    except ResourceLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    
    # Celeryタスク投入
    task = execute_backtest_task.delay(job_input.json())
    
    # 実行時間予測
    estimated_duration = estimate_execution_time(job_input)
    estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_duration)
    
    return schemas.BacktestResponse(
        job_id=task.id,
        status="queued",
        estimated_completion=estimated_completion,
        estimated_duration=estimated_duration
    )

@router.get("/backtest/status/{job_id}")
async def get_backtest_status(
    job_id: str,
    current_user: models.User = Depends(get_current_user)
) -> schemas.BacktestStatusResponse:
    """バックテスト実行状況取得"""
    
    # Celeryタスク状況確認
    task_result = celery_app.AsyncResult(job_id)
    
    if task_result.state == 'PENDING':
        return schemas.BacktestStatusResponse(
            job_id=job_id,
            status="queued",
            progress=None
        )
    
    elif task_result.state == 'PROGRESS':
        progress_data = task_result.info
        return schemas.BacktestStatusResponse(
            job_id=job_id,
            status="running",
            progress=progress_data
        )
    
    elif task_result.state == 'SUCCESS':
        result_data = json.loads(task_result.result)
        return schemas.BacktestStatusResponse(
            job_id=job_id,
            status="completed",
            result=result_data
        )
    
    else:  # FAILURE
        return schemas.BacktestStatusResponse(
            job_id=job_id,
            status="failed",
            error=str(task_result.info)
        )
```

## Testing Strategy

### Unit Tests
```python
@pytest.mark.asyncio
async def test_backtest_data_preparation():
    """データ準備テスト"""
    
    job_input = BacktestJobInput(
        user_id="test-user",
        simulation_config=SimulationConfig(
            symbols=["7203"],
            start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 31),
            initial_capital=1000000
        )
    )
    
    context = await initialize_backtest_job(job_input)
    historical_data = await prepare_historical_data(context)
    
    assert len(historical_data.price_data) == 1
    assert "7203" in historical_data.price_data
    assert len(historical_data.price_data["7203"]["price_data"]) >= 60  # 約3ヶ月分

@pytest.mark.asyncio
async def test_ai_consensus_logic():
    """AI合意形成ロジックテスト"""
    
    ai_results = [
        AIDecision(model="gpt-4", decision="buy", confidence=0.8),
        AIDecision(model="claude", decision="buy", confidence=0.7),
        AIDecision(model="gemini", decision="hold", confidence=0.6)
    ]
    
    consensus = form_consensus(ai_results, consensus_threshold=0.7)
    
    assert consensus.final_decision == "buy"
    assert consensus.agreement_ratio == 2/3  # 2 out of 3 models agree
```

### Integration Tests  
```python
@pytest.mark.integration
@pytest.mark.slow
async def test_small_backtest_e2e():
    """小規模バックテストE2E"""
    
    job_input = create_test_backtest_input(
        symbols=["7203"],
        days=30,
        strategy="single_model"
    )
    
    result = await execute_backtest_workflow(job_input)
    
    assert result.status == BacktestStatus.COMPLETED
    assert result.performance_summary.total_trades > 0
    assert result.execution_metrics.total_processing_time < 300  # 5分以内
    assert result.ai_statistics.total_ai_cost_usd < 5.0  # $5以下
```

## 関連文書

- [AI分析ジョブ仕様書](./ai-analysis-job.md)
- [データベース設計書](../../data/schema.md)
- [OpenRouter統合設計書](../../ai/openrouter-integration.md)
- [エラーカタログ](../../api/error-catalog.md)
- [API開発計画書](../../api-development-plan.md)