#!/usr/bin/env python3
"""
設定値デバッグスクリプト
"""

import sys
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.config.settings import settings

print("立花証券API設定デバッグ")
print("="*50)

print(f"TACHIBANA_API_KEY: {settings.TACHIBANA_API_KEY}")
print(f"TACHIBANA_API_SECRET: {settings.TACHIBANA_API_SECRET}")
print(f"API_KEY is None: {settings.TACHIBANA_API_KEY is None}")
print(f"API_SECRET is None: {settings.TACHIBANA_API_SECRET is None}")

# 判定ロジックのテスト
if not settings.TACHIBANA_API_KEY or not settings.TACHIBANA_API_SECRET:
    print("✅ モックモードになるはずです")
    mock_mode = True
else:
    print("❌ モックモードになりません")
    mock_mode = False

print(f"予想されるモックモード: {mock_mode}")

# 実際のクライアント生成テスト
from app.services.tachibana_client import TachibanaClient

client = TachibanaClient()
print(f"実際のモックモード: {client.mock_mode}")
print(f"API Key (client): {client.api_key}")
print(f"API Secret (client): {client.api_secret}")