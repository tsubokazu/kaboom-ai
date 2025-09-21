#!/usr/bin/env python3
"""
立花証券APIクライアントのテストスクリプト
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.tachibana_client import (
    TachibanaClient,
    TachibanaOrder,
    TachibanaOrderType,
    TachibanaOrderSide,
    TachibanaTimeInForce,
    OrderExecutionService,
    TachibanaError
)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_basic_client():
    """基本的なクライアント機能テスト"""
    print("\n" + "="*60)
    print("立花証券APIクライアント - 基本機能テスト")
    print("="*60)

    async with TachibanaClient() as client:
        print(f"クライアント初期化完了 - モックモード: {client.mock_mode}")

        # 1. 残高情報取得テスト
        print("\n1. 残高情報取得テスト")
        try:
            balance = await client.get_balance()
            print(f"   現金残高: {balance.cash_balance:,.0f}円")
            print(f"   買付余力: {balance.buying_power:,.0f}円")
            print(f"   総資産: {balance.total_equity:,.0f}円")
            print(f"   証拠金使用額: {balance.margin_used:,.0f}円")
            print(f"   ポジション数: {len(balance.positions)}件")

            for i, pos in enumerate(balance.positions[:3]):  # 最初の3件のみ表示
                print(f"   ポジション{i+1}: {pos.symbol} {pos.quantity}株 "
                      f"(平均単価: {pos.average_cost:.0f}円, 含み損益: {pos.unrealized_pnl:+.0f}円)")
        except Exception as e:
            print(f"   エラー: {e}")

        # 2. 市場価格取得テスト
        print("\n2. 市場価格取得テスト")
        test_symbols = ["7203", "6758", "9984"]
        for symbol in test_symbols:
            try:
                quote = await client.get_market_quote(symbol)
                print(f"   {symbol}: 最終価格 {quote['last']:.0f}円 "
                      f"(買気配: {quote['bid']:.0f}円, 売気配: {quote['ask']:.0f}円)")
            except Exception as e:
                print(f"   {symbol} エラー: {e}")

async def test_order_operations():
    """注文操作テスト"""
    print("\n" + "="*60)
    print("立花証券APIクライアント - 注文操作テスト")
    print("="*60)

    async with TachibanaClient() as client:
        # 3. 新規注文送信テスト
        print("\n3. 新規注文送信テスト")
        test_order = TachibanaOrder(
            symbol="7203",  # トヨタ自動車
            side=TachibanaOrderSide.BUY,
            order_type=TachibanaOrderType.LIMIT,
            quantity=100,
            price=2650.0,
            time_in_force=TachibanaTimeInForce.DAY
        )

        try:
            order_status = await client.place_order(test_order)
            print(f"   注文ID: {order_status.order_id}")
            print(f"   クライアント注文ID: {order_status.client_order_id}")
            print(f"   銘柄: {order_status.symbol}")
            print(f"   売買区分: {order_status.side}")
            print(f"   注文タイプ: {order_status.order_type}")
            print(f"   数量: {order_status.quantity}株")
            print(f"   価格: {order_status.price}円")
            print(f"   ステータス: {order_status.status}")
            print(f"   注文時刻: {order_status.timestamp}")

            # 4. 注文ステータス確認テスト
            print("\n4. 注文ステータス確認テスト")
            await asyncio.sleep(1)  # 少し待つ

            updated_status = await client.get_order_status(order_status.order_id)
            print(f"   更新後ステータス: {updated_status.status}")
            print(f"   約定数量: {updated_status.filled_quantity}株")
            print(f"   未約定数量: {updated_status.remaining_quantity}株")
            if updated_status.average_price:
                print(f"   平均約定価格: {updated_status.average_price:.0f}円")
            if updated_status.commission:
                print(f"   手数料: {updated_status.commission:.0f}円")

            # 5. 注文キャンセルテスト（約定していない場合）
            if updated_status.status not in ["filled", "cancelled"]:
                print("\n5. 注文キャンセルテスト")
                cancel_result = await client.cancel_order(order_status.order_id)
                print(f"   キャンセル結果: {'成功' if cancel_result else '失敗'}")

        except TachibanaError as e:
            print(f"   立花証券APIエラー: {e}")
        except Exception as e:
            print(f"   その他のエラー: {e}")

async def test_order_history():
    """注文履歴テスト"""
    print("\n" + "="*60)
    print("立花証券APIクライアント - 注文履歴テスト")
    print("="*60)

    async with TachibanaClient() as client:
        print("\n6. 注文履歴取得テスト")
        try:
            # 過去7日間の注文履歴を取得
            end_date = datetime.now()
            start_date = end_date.replace(day=end_date.day-7)

            order_history = await client.get_order_history(
                start_date=start_date,
                end_date=end_date,
                limit=10
            )

            print(f"   取得件数: {len(order_history)}件")

            for i, order in enumerate(order_history[:5]):  # 最新5件のみ表示
                print(f"   注文{i+1}: {order.symbol} {order.side} {order.quantity}株 "
                      f"ステータス:{order.status} ({order.timestamp.strftime('%m/%d %H:%M')})")

        except Exception as e:
            print(f"   エラー: {e}")

async def test_order_execution_service():
    """注文執行サービステスト"""
    print("\n" + "="*60)
    print("注文執行サービス - 統合テスト")
    print("="*60)

    print("\n7. 注文執行サービステスト")
    try:
        async with OrderExecutionService() as service:
            print("   注文執行サービス初期化完了")

            # テスト注文実行
            result = await service.execute_order(
                user_id="test_user_123",
                portfolio_id="test_portfolio_456",
                symbol="6758",  # ソニーグループ
                side="buy",
                order_type="limit",
                quantity=50,
                price=8200.0
            )

            print(f"   外部注文ID: {result['external_order_id']}")
            print(f"   クライアント注文ID: {result['client_order_id']}")
            print(f"   ステータス: {result['status']}")
            print(f"   銘柄: {result['symbol']}")
            print(f"   売買区分: {result['side']}")
            print(f"   数量: {result['quantity']}株")
            print(f"   価格: {result['price']}円")

            # 口座残高確認
            print("\n8. 口座残高確認")
            balance = await service.get_account_balance()
            print(f"   現金残高: {balance.cash_balance:,.0f}円")
            print(f"   総資産: {balance.total_equity:,.0f}円")

            # 短時間で注文監視をテスト
            print("\n9. 注文監視テスト（3秒間）")
            await asyncio.sleep(3)
            print("   注文監視動作確認完了")

    except Exception as e:
        print(f"   エラー: {e}")

async def test_error_scenarios():
    """エラーシナリオテスト"""
    print("\n" + "="*60)
    print("立花証券APIクライアント - エラーハンドリングテスト")
    print("="*60)

    async with TachibanaClient() as client:
        print("\n10. エラーハンドリングテスト")

        # 存在しない注文IDでステータス取得
        try:
            await client.get_order_status("invalid_order_id")
        except TachibanaError as e:
            print(f"   期待されるエラー処理: {e}")
        except Exception as e:
            print(f"   予期しないエラー: {e}")

        # 無効な銘柄コードで市場価格取得
        try:
            await client.get_market_quote("INVALID")
        except TachibanaError as e:
            print(f"   期待されるエラー処理: {e}")
        except Exception as e:
            print(f"   予期しないエラー: {e}")

async def main():
    """メインテスト実行"""
    print("立花証券API検証スクリプト開始")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 基本機能テスト
        await test_basic_client()

        # 注文操作テスト
        await test_order_operations()

        # 注文履歴テスト
        await test_order_history()

        # 注文執行サービステスト
        await test_order_execution_service()

        # エラーシナリオテスト
        await test_error_scenarios()

        print("\n" + "="*60)
        print("✅ 全てのテストが完了しました")
        print("="*60)

    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())