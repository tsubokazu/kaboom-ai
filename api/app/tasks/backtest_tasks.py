"""
バックテストタスク - AI戦略の過去データ検証

機能:
- AI分析結果に基づく取引戦略のバックテスト
- 長期間データでの戦略検証
- パフォーマンス指標計算・レポート生成  
- 結果の可視化チャート生成
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

from celery import Task
from app.tasks.celery_app import celery_app
from app.services.redis_client import get_redis_client
from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="backtest.strategy_backtest",
    queue="backtest", 
    soft_time_limit=600,  # 10分
    time_limit=900,       # 15分
    retry_kwargs={"max_retries": 1, "countdown": 300}
)
def strategy_backtest_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI戦略バックテストタスク
    
    Args:
        request_data: {
            "strategy_config": {...},
            "symbol": "7203",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01", 
            "initial_capital": 1000000,
            "user_id": "user123"
        }
    """
    request_id = self.request.id
    symbol = request_data.get("symbol")
    user_id = request_data.get("user_id")
    
    try:
        # タスク開始通知
        asyncio.run(_update_backtest_status(
            request_id, "running",
            {"message": f"バックテスト開始: {symbol}", "progress": 5}
        ))
        
        # 市場データ取得
        asyncio.run(_update_backtest_status(
            request_id, "running", 
            {"message": "過去データ取得中...", "progress": 15}
        ))
        
        market_data = _fetch_historical_data(symbol, request_data)
        
        # 戦略実行シミュレーション
        asyncio.run(_update_backtest_status(
            request_id, "running",
            {"message": "戦略実行シミュレーション中...", "progress": 40}
        ))
        
        simulation_result = _run_strategy_simulation(market_data, request_data)
        
        # パフォーマンス分析
        asyncio.run(_update_backtest_status(
            request_id, "running",
            {"message": "パフォーマンス分析中...", "progress": 70}
        ))
        
        performance_metrics = _calculate_performance_metrics(simulation_result)
        
        # レポート・チャート生成
        asyncio.run(_update_backtest_status(
            request_id, "running", 
            {"message": "レポート生成中...", "progress": 85}
        ))
        
        backtest_report = _generate_backtest_report(simulation_result, performance_metrics, request_data)
        
        # 結果保存・通知
        final_result = {
            "performance_metrics": performance_metrics,
            "trades": simulation_result["trades"],
            "equity_curve": simulation_result["equity_curve"],
            "report": backtest_report,
            "metadata": {
                "symbol": symbol,
                "period": f"{request_data.get('start_date')} - {request_data.get('end_date')}",
                "initial_capital": request_data.get("initial_capital", 1000000),
                "total_trades": len(simulation_result["trades"]),
                "duration": "calculated"
            }
        }
        
        asyncio.run(_save_backtest_result(request_id, final_result))
        
        if user_id:
            asyncio.run(_notify_backtest_complete(request_id, user_id, final_result))
        
        asyncio.run(_update_backtest_status(
            request_id, "completed",
            {"message": "バックテスト完了", "progress": 100}
        ))
        
        return {
            "status": "success",
            "request_id": request_id,
            "symbol": symbol,
            "result": final_result
        }
        
    except Exception as e:
        logger.error(f"Backtest task failed: {e}")
        
        # エラー通知
        asyncio.run(_update_backtest_status(
            request_id, "failed",
            {"error": str(e), "message": "バックテストに失敗しました"}
        ))
        
        raise


@celery_app.task(
    bind=True,
    name="backtest.portfolio_optimization",
    queue="backtest",
    soft_time_limit=900,  # 15分
    time_limit=1200       # 20分
)
def portfolio_optimization_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """ポートフォリオ最適化バックテストタスク"""
    request_id = self.request.id
    symbols = request_data.get("symbols", [])
    user_id = request_data.get("user_id")
    
    try:
        asyncio.run(_update_backtest_status(
            request_id, "running",
            {"message": f"ポートフォリオ最適化開始: {len(symbols)}銘柄", "progress": 10}
        ))
        
        # 複数銘柄データ取得
        multi_asset_data = {}
        for i, symbol in enumerate(symbols):
            progress = 20 + (i / len(symbols)) * 40
            asyncio.run(_update_backtest_status(
                request_id, "running",
                {"message": f"{symbol}データ取得中...", "progress": progress}
            ))
            
            multi_asset_data[symbol] = _fetch_historical_data(symbol, request_data)
        
        # ポートフォリオ最適化実行
        asyncio.run(_update_backtest_status(
            request_id, "running", 
            {"message": "最適ポートフォリオ計算中...", "progress": 70}
        ))
        
        optimization_result = _optimize_portfolio_weights(multi_asset_data, request_data)
        
        # バックテスト実行
        portfolio_backtest = _run_portfolio_backtest(multi_asset_data, optimization_result, request_data)
        
        final_result = {
            "optimal_weights": optimization_result["weights"],
            "expected_return": optimization_result["expected_return"],
            "volatility": optimization_result["volatility"],
            "sharpe_ratio": optimization_result["sharpe_ratio"],
            "backtest_result": portfolio_backtest
        }
        
        asyncio.run(_save_backtest_result(request_id, final_result))
        
        if user_id:
            asyncio.run(_notify_backtest_complete(request_id, user_id, final_result))
        
        return {
            "status": "success",
            "request_id": request_id,
            "result": final_result
        }
        
    except Exception as e:
        logger.error(f"Portfolio optimization task failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="backtest.monte_carlo_simulation", 
    queue="backtest",
    soft_time_limit=1200,  # 20分
    time_limit=1800        # 30分
)
def monte_carlo_simulation_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """モンテカルロシミュレーションタスク"""
    request_id = self.request.id
    symbol = request_data.get("symbol")
    user_id = request_data.get("user_id")
    simulations = request_data.get("simulations", 1000)
    
    try:
        asyncio.run(_update_backtest_status(
            request_id, "running",
            {"message": f"モンテカルロ開始: {simulations}回シミュレーション", "progress": 5}
        ))
        
        # 基礎データ取得
        historical_data = _fetch_historical_data(symbol, request_data)
        
        # シミュレーション実行
        simulation_results = []
        
        for i in range(simulations):
            if i % 100 == 0:  # 100回毎に進行状況更新
                progress = 20 + (i / simulations) * 70
                asyncio.run(_update_backtest_status(
                    request_id, "running",
                    {"message": f"シミュレーション実行中: {i}/{simulations}", "progress": progress}
                ))
            
            single_result = _run_monte_carlo_single_simulation(historical_data, request_data)
            simulation_results.append(single_result)
        
        # 統計分析
        asyncio.run(_update_backtest_status(
            request_id, "running",
            {"message": "統計分析実行中...", "progress": 95}
        ))
        
        statistical_analysis = _analyze_monte_carlo_results(simulation_results)
        
        final_result = {
            "simulations_count": simulations,
            "statistics": statistical_analysis,
            "percentiles": _calculate_percentiles(simulation_results),
            "risk_metrics": _calculate_risk_metrics(simulation_results)
        }
        
        asyncio.run(_save_backtest_result(request_id, final_result))
        
        if user_id:
            asyncio.run(_notify_backtest_complete(request_id, user_id, final_result))
        
        return {
            "status": "success",
            "request_id": request_id,
            "result": final_result
        }
        
    except Exception as e:
        logger.error(f"Monte Carlo simulation task failed: {e}")
        raise


# ===================================
# 内部ヘルパー関数
# ===================================

def _fetch_historical_data(symbol: str, config: Dict) -> pd.DataFrame:
    """過去データ取得（モック実装）"""
    # 実際の実装ではyfinance、Alpha Vantage等のAPIを使用
    start_date = pd.to_datetime(config.get("start_date", "2023-01-01"))
    end_date = pd.to_datetime(config.get("end_date", "2024-01-01"))
    
    # モックデータ生成
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # ランダムウォーク価格生成
    np.random.seed(42)  # 再現可能性のため
    initial_price = 1000
    returns = np.random.normal(0.001, 0.02, len(date_range))  # 日次リターン
    prices = initial_price * np.exp(np.cumsum(returns))
    
    data = pd.DataFrame({
        'date': date_range,
        'close': prices,
        'volume': np.random.randint(100000, 1000000, len(date_range))
    })
    
    return data


def _run_strategy_simulation(market_data: pd.DataFrame, config: Dict) -> Dict[str, Any]:
    """戦略実行シミュレーション"""
    initial_capital = config.get("initial_capital", 1000000)
    
    # シンプルな移動平均戦略（例）
    market_data['sma_20'] = market_data['close'].rolling(20).mean()
    market_data['sma_50'] = market_data['close'].rolling(50).mean()
    
    trades = []
    equity = [initial_capital]
    cash = initial_capital
    position = 0
    
    for i in range(50, len(market_data)):  # 50日後から開始（SMA計算のため）
        current_price = market_data.iloc[i]['close']
        sma_20 = market_data.iloc[i]['sma_20']
        sma_50 = market_data.iloc[i]['sma_50']
        
        # ゴールデンクロス（買いシグナル）
        if sma_20 > sma_50 and position == 0:
            position = cash // current_price
            cash = cash % current_price
            trades.append({
                'date': market_data.iloc[i]['date'].isoformat(),
                'action': 'buy',
                'price': current_price,
                'quantity': position,
                'cash_after': cash
            })
        
        # デッドクロス（売りシグナル）
        elif sma_20 < sma_50 and position > 0:
            cash += position * current_price
            trades.append({
                'date': market_data.iloc[i]['date'].isoformat(),
                'action': 'sell',
                'price': current_price,
                'quantity': position,
                'cash_after': cash
            })
            position = 0
        
        # 現在のポートフォリオ価値
        portfolio_value = cash + (position * current_price)
        equity.append(portfolio_value)
    
    return {
        'trades': trades,
        'equity_curve': equity,
        'final_value': equity[-1],
        'total_return': (equity[-1] / initial_capital - 1) * 100
    }


def _calculate_performance_metrics(simulation_result: Dict) -> Dict[str, Any]:
    """パフォーマンス指標計算"""
    equity_curve = simulation_result['equity_curve']
    trades = simulation_result['trades']
    
    # リターン系指標
    total_return = simulation_result['total_return']
    
    # リスク指標
    daily_returns = np.diff(equity_curve) / equity_curve[:-1]
    volatility = np.std(daily_returns) * np.sqrt(252) * 100  # 年間ボラティリティ
    
    # シャープレシオ（リスクフリーレート=0と仮定）
    sharpe_ratio = (np.mean(daily_returns) * 252) / (np.std(daily_returns) * np.sqrt(252))
    
    # 最大ドローダウン
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    max_drawdown = np.min(drawdown) * 100
    
    # 勝率計算
    profitable_trades = 0
    total_trades = len(trades) // 2  # buy/sellペアの数
    
    for i in range(0, len(trades) - 1, 2):
        if i + 1 < len(trades):
            buy_price = trades[i]['price']
            sell_price = trades[i + 1]['price']
            if sell_price > buy_price:
                profitable_trades += 1
    
    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'total_return_percent': round(total_return, 2),
        'annual_volatility_percent': round(volatility, 2),
        'sharpe_ratio': round(sharpe_ratio, 3),
        'max_drawdown_percent': round(max_drawdown, 2),
        'total_trades': total_trades,
        'win_rate_percent': round(win_rate, 2),
        'profitable_trades': profitable_trades,
        'losing_trades': total_trades - profitable_trades
    }


def _generate_backtest_report(simulation_result: Dict, metrics: Dict, config: Dict) -> Dict[str, Any]:
    """バックテストレポート生成"""
    return {
        'summary': {
            'strategy': 'SMA Cross Strategy',
            'symbol': config.get('symbol'),
            'period': f"{config.get('start_date')} - {config.get('end_date')}",
            'initial_capital': config.get('initial_capital'),
            'final_value': simulation_result['final_value'],
            'profit_loss': simulation_result['final_value'] - config.get('initial_capital', 1000000)
        },
        'performance': metrics,
        'recommendations': [
            'パラメータ調整により更なる改善の可能性',
            'リスク管理の強化を検討',
            'より長期間でのバックテストを推奨'
        ]
    }


def _optimize_portfolio_weights(multi_asset_data: Dict[str, pd.DataFrame], config: Dict) -> Dict[str, Any]:
    """ポートフォリオ重み最適化（簡易版）"""
    # モック実装：等重みポートフォリオ
    symbols = list(multi_asset_data.keys())
    equal_weight = 1.0 / len(symbols)
    
    weights = {symbol: equal_weight for symbol in symbols}
    
    return {
        'weights': weights,
        'expected_return': 0.08,  # 8% annual return
        'volatility': 0.15,       # 15% volatility
        'sharpe_ratio': 0.53      # (8% - 0%) / 15%
    }


def _run_portfolio_backtest(multi_asset_data: Dict, optimization_result: Dict, config: Dict) -> Dict[str, Any]:
    """ポートフォリオバックテスト実行"""
    # 簡易実装
    return {
        'portfolio_value': [1000000, 1050000, 1080000],  # モック値
        'individual_contributions': {
            symbol: np.random.uniform(0.95, 1.05, 3).tolist() 
            for symbol in multi_asset_data.keys()
        }
    }


def _run_monte_carlo_single_simulation(historical_data: pd.DataFrame, config: Dict) -> Dict[str, Any]:
    """単一モンテカルロシミュレーション"""
    # 簡易実装：最終値のみ返す
    initial_value = config.get('initial_capital', 1000000)
    final_value = initial_value * np.random.lognormal(0.05, 0.2)  # ランダムな最終値
    
    return {
        'final_value': final_value,
        'total_return': (final_value / initial_value - 1) * 100
    }


def _analyze_monte_carlo_results(simulation_results: List[Dict]) -> Dict[str, Any]:
    """モンテカルロ結果統計分析"""
    returns = [result['total_return'] for result in simulation_results]
    
    return {
        'mean_return': np.mean(returns),
        'median_return': np.median(returns),
        'std_return': np.std(returns),
        'min_return': np.min(returns),
        'max_return': np.max(returns)
    }


def _calculate_percentiles(simulation_results: List[Dict]) -> Dict[str, float]:
    """パーセンタイル計算"""
    returns = [result['total_return'] for result in simulation_results]
    
    return {
        '5th_percentile': np.percentile(returns, 5),
        '25th_percentile': np.percentile(returns, 25),
        '50th_percentile': np.percentile(returns, 50),
        '75th_percentile': np.percentile(returns, 75),
        '95th_percentile': np.percentile(returns, 95)
    }


def _calculate_risk_metrics(simulation_results: List[Dict]) -> Dict[str, Any]:
    """リスク指標計算"""
    returns = [result['total_return'] for result in simulation_results]
    
    # VaR (Value at Risk) 5%
    var_5 = np.percentile(returns, 5)
    
    # CVaR (Conditional Value at Risk)  
    cvar_5 = np.mean([r for r in returns if r <= var_5])
    
    return {
        'value_at_risk_5_percent': var_5,
        'conditional_var_5_percent': cvar_5,
        'probability_of_loss': len([r for r in returns if r < 0]) / len(returns) * 100
    }


# バックテスト専用ヘルパー関数

async def _update_backtest_status(task_id: str, status: str, details: Dict[str, Any]):
    """バックテストタスク状況更新"""
    try:
        redis_client = await get_redis_client()
        await redis_client.set_job_status(task_id, status, details)
        
        await websocket_manager.broadcast({
            "type": "backtest_progress",
            "payload": {
                "task_id": task_id,
                "status": status,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, "backtest_updates")
        
    except Exception as e:
        logger.warning(f"Failed to update backtest status: {e}")


async def _save_backtest_result(request_id: str, result: Dict[str, Any]):
    """バックテスト結果保存"""
    try:
        redis_client = await get_redis_client()
        await redis_client.set_cache(f"backtest_result:{request_id}", result, expire_seconds=86400)  # 24時間保持
        
    except Exception as e:
        logger.error(f"Failed to save backtest result: {e}")


async def _notify_backtest_complete(request_id: str, user_id: str, result: Dict[str, Any]):
    """バックテスト完了通知"""
    try:
        await websocket_manager.send_ai_analysis_result(request_id, user_id, {
            "type": "backtest_complete",
            "result": result
        })
        
    except Exception as e:
        logger.error(f"Failed to notify backtest completion: {e}")