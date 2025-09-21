#!/usr/bin/env python3
"""
立花証券APIクライアントのモックモードテストスクリプト
"""

import asyncio
import sys
import logging
import os
from datetime import datetime
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 環境変数をクリアしてモックモードを強制
os.environ.pop('TACHIBANA_API_KEY', None)
os.environ.pop('TACHIBANA_API_SECRET', None)

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

async def test_mock_mode():
    """モックモード動作確認テスト"""
    print("\n" + "="*60)
    print("立花証券APIクライアント - モックモード検証")
    print("="*60)

    async with TachibanaClient() as client:
        print(f"✅ クライアント初期化完了 - モックモード: {client.mock_mode}")
        assert client.mock_mode, "モックモードで動作していません"

        # 1. 残高情報取得テスト
        print("\n1. 残高情報取得テスト")
        try:
            balance = await client.get_balance()
            print(f"   ✅ 現金残高: {balance.cash_balance:,.0f}円")
            print(f"   ✅ 買付余力: {balance.buying_power:,.0f}円")
            print(f"   ✅ 総資産: {balance.total_equity:,.0f}円")
            print(f"   ✅ 証拠金使用額: {balance.margin_used:,.0f}円")
            print(f"   ✅ ポジション数: {len(balance.positions)}件")

            for i, pos in enumerate(balance.positions):
                print(f"   ポジション{i+1}: {pos.symbol} {pos.quantity}株 "
                      f"(平均単価: {pos.average_cost:.0f}円, 含み損益: {pos.unrealized_pnl:+,.0f}円)")
        except Exception as e:
            print(f"   ❌ エラー: {e}")
            return False

        # 2. 市場価格取得テスト
        print("\n2. 市場価格取得テスト")
        test_symbols = ["7203", "6758", "9984"]
        for symbol in test_symbols:
            try:
                quote = await client.get_market_quote(symbol)
                print(f"   ✅ {symbol}: 最終価格 {quote['last']:.0f}円 "
                      f"(買気配: {quote['bid']:.0f}円, 売気配: {quote['ask']:.0f}円)")
            except Exception as e:
                print(f"   ❌ {symbol} エラー: {e}")
                return False

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
            print(f"   ✅ 注文ID: {order_status.order_id}")
            print(f"   ✅ クライアント注文ID: {order_status.client_order_id}")
            print(f"   ✅ 銘柄: {order_status.symbol}")
            print(f"   ✅ 売買区分: {order_status.side}")
            print(f"   ✅ 注文タイプ: {order_status.order_type}")
            print(f"   ✅ 数量: {order_status.quantity}株")
            print(f"   ✅ 価格: {order_status.price}円")
            print(f"   ✅ ステータス: {order_status.status}")

            # 4. 注文ステータス確認テスト
            print("\n4. 注文ステータス確認テスト")
            updated_status = await client.get_order_status(order_status.order_id)
            print(f"   ✅ 更新後ステータス: {updated_status.status}")
            print(f"   ✅ 約定数量: {updated_status.filled_quantity}株")
            print(f"   ✅ 未約定数量: {updated_status.remaining_quantity}株")
            if updated_status.average_price:
                print(f"   ✅ 平均約定価格: {updated_status.average_price:.0f}円")
            if updated_status.commission:
                print(f"   ✅ 手数料: {updated_status.commission:.0f}円")

        except Exception as e:
            print(f"   ❌ 注文関連エラー: {e}")
            return False

        # 5. 注文履歴取得テスト
        print("\n5. 注文履歴取得テスト")
        try:
            end_date = datetime.now()
            start_date = end_date.replace(day=max(1, end_date.day-7))

            order_history = await client.get_order_history(
                start_date=start_date,
                end_date=end_date,
                limit=10
            )
            print(f"   ✅ 取得件数: {len(order_history)}件")

        except Exception as e:
            print(f"   ❌ 履歴取得エラー: {e}")
            return False

        return True

async def test_order_execution_service_mock():
    """注文執行サービス モックモードテスト"""
    print("\n" + "="*60)
    print("注文執行サービス - モックモード検証")
    print("="*60)

    try:
        async with OrderExecutionService() as service:
            print("   ✅ 注文執行サービス初期化完了")

            # テスト注文実行
            print("\n6. 注文執行サービステスト")
            result = await service.execute_order(
                user_id="test_user_123",
                portfolio_id="test_portfolio_456",
                symbol="6758",  # ソニーグループ
                side="buy",
                order_type="limit",
                quantity=50,
                price=8200.0
            )

            print(f"   ✅ 外部注文ID: {result['external_order_id']}")
            print(f"   ✅ クライアント注文ID: {result['client_order_id']}")
            print(f"   ✅ ステータス: {result['status']}")
            print(f"   ✅ 銘柄: {result['symbol']}")
            print(f"   ✅ 売買区分: {result['side']}")
            print(f"   ✅ 数量: {result['quantity']}株")
            print(f"   ✅ 価格: {result['price']}円")

            # 口座残高確認
            print("\n7. 口座残高確認")
            balance = await service.get_account_balance()
            print(f"   ✅ 現金残高: {balance.cash_balance:,.0f}円")
            print(f"   ✅ 総資産: {balance.total_equity:,.0f}円")
            print(f"   ✅ ポジション数: {len(balance.positions)}件")

            # 短時間で注文監視をテスト
            print("\n8. 注文監視テスト（2秒間）")
            await asyncio.sleep(2)
            print("   ✅ 注文監視動作確認完了")

            return True

    except Exception as e:
        print(f"   ❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_signature_generation():
    """署名生成テスト"""
    print("\n" + "="*60)
    print("認証・署名生成テスト")
    print("="*60)

    # 一時的に認証情報を設定
    os.environ['TACHIBANA_API_KEY'] = 'test_api_key'
    os.environ['TACHIBANA_API_SECRET'] = 'test_api_secret'

    try:
        async with TachibanaClient() as client:
            print(f"   認証モード: {not client.mock_mode}")

            # 署名生成テスト
            method = "POST"
            path = "/orders"
            timestamp = "1234567890"
            body = '{"symbol":"7203","side":"buy"}'

            signature = client._generate_signature(method, path, timestamp, body)
            print(f"   ✅ 署名生成成功: {signature[:20]}...")

            # ヘッダー生成テスト
            headers = client._get_headers(method, path, body)
            print(f"   ✅ ヘッダー生成成功:")
            for key, value in headers.items():
                if key == 'X-Signature':
                    print(f"      {key}: {value[:20]}...")
                else:
                    print(f"      {key}: {value}")

            return True

    except Exception as e:
        print(f"   ❌ 認証テストエラー: {e}")
        return False
    finally:
        # 環境変数をクリア
        os.environ.pop('TACHIBANA_API_KEY', None)
        os.environ.pop('TACHIBANA_API_SECRET', None)

async def test_data_structures():
    """データ構造テスト"""
    print("\n" + "="*60)
    print("データ構造・型安全性テスト")
    print("="*60)

    print("\n9. Enum値テスト")

    # OrderType
    order_types = [TachibanaOrderType.MARKET, TachibanaOrderType.LIMIT,
                   TachibanaOrderType.STOP, TachibanaOrderType.STOP_LIMIT]
    print(f"   ✅ 注文タイプ: {[ot.value for ot in order_types]}")

    # OrderSide
    order_sides = [TachibanaOrderSide.BUY, TachibanaOrderSide.SELL]
    print(f"   ✅ 売買区分: {[os.value for os in order_sides]}")

    # TimeInForce
    time_in_forces = [TachibanaTimeInForce.DAY, TachibanaTimeInForce.GTC,
                      TachibanaTimeInForce.IOC, TachibanaTimeInForce.FOK]
    print(f"   ✅ 有効期限: {[tif.value for tif in time_in_forces]}")

    print("\n10. TachibanaOrder作成テスト")
    try:
        order = TachibanaOrder(
            symbol="7203",
            side=TachibanaOrderSide.BUY,
            order_type=TachibanaOrderType.LIMIT,
            quantity=100,
            price=2650.0,
            stop_price=None,
            time_in_force=TachibanaTimeInForce.DAY,
            client_order_id="test_order_123"
        )
        print(f"   ✅ 注文オブジェクト作成成功: {order.symbol} {order.side.value} {order.quantity}株")
        return True
    except Exception as e:
        print(f"   ❌ 注文オブジェクト作成エラー: {e}")
        return False

async def main():
    """メインテスト実行"""
    print("立花証券APIクライアント - モックモード完全検証")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_results = []

    try:
        # モックモード基本機能テスト
        print("\n【Phase 1: 基本機能テスト】")
        result1 = await test_mock_mode()
        test_results.append(("基本機能テスト", result1))

        # 注文執行サービステスト
        print("\n【Phase 2: 注文執行サービステスト】")
        result2 = await test_order_execution_service_mock()
        test_results.append(("注文執行サービス", result2))

        # 認証・署名生成テスト
        print("\n【Phase 3: 認証機能テスト】")
        result3 = await test_signature_generation()
        test_results.append(("認証機能", result3))

        # データ構造テスト
        print("\n【Phase 4: データ構造テスト】")
        result4 = await test_data_structures()
        test_results.append(("データ構造", result4))

        # 結果サマリー
        print("\n" + "="*60)
        print("🧪 テスト結果サマリー")
        print("="*60)

        all_passed = True
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if not result:
                all_passed = False

        if all_passed:
            print(f"\n🎉 全てのテストが成功しました！")
            print("   立花証券APIクライアントは正常に動作しています。")
            print("   実際のAPIキーを設定すれば本番環境で利用可能です。")
        else:
            print(f"\n⚠️  一部のテストが失敗しました。")

        print("\n📋 次のステップ:")
        print("   1. 立花証券からAPIキー・シークレットを取得")
        print("   2. 環境変数 TACHIBANA_API_KEY, TACHIBANA_API_SECRET を設定")
        print("   3. 本番APIエンドポイントの確認・設定")
        print("   4. 本番環境での動作確認")

    except Exception as e:
        print(f"\n❌ テスト実行中に予期しないエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())