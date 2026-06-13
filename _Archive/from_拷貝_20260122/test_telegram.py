#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 Telegram 連接
"""

import requests
from pathlib import Path

def load_config():
    """載入 .env 配置"""
    config = {}
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ 未找到 .env 文件")
        return None
    
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    return config

def test_telegram(token, chat_id):
    """測試 Telegram 連接"""
    print("=" * 60)
    print("測試 Telegram 連接")
    print("=" * 60)
    
    # 測試 Bot Token
    print(f"\n1. 測試 Bot Token...")
    print(f"   Token: {token[:20]}...")
    
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('ok'):
            bot_info = data.get('result', {})
            print(f"   ✅ Bot Token 有效")
            print(f"   Bot 名稱: {bot_info.get('first_name')}")
            print(f"   Bot 用戶名: @{bot_info.get('username')}")
        else:
            print(f"   ❌ Bot Token 無效")
            return False
    
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
        return False
    
    # 測試發送訊息
    print(f"\n2. 測試發送訊息...")
    print(f"   Chat ID: {chat_id}")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    test_message = """🤖 交易提醒系統測試

✅ Telegram 連接成功！

系統已準備就緒，將在以下情況發送通知：
• 所有進場條件符合時
• 提供具體的進場價、止損價、目標價

祝您交易順利！"""
    
    data = {
        'chat_id': chat_id,
        'text': test_message
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get('ok'):
            print(f"   ✅ 測試訊息已發送")
            print(f"   請檢查您的 Telegram 是否收到訊息")
            return True
        else:
            print(f"   ❌ 發送失敗: {result.get('description')}")
            return False
    
    except Exception as e:
        print(f"   ❌ 發送失敗: {e}")
        return False

def main():
    """主函數"""
    # 載入配置
    config = load_config()
    
    if not config:
        return
    
    token = config.get('TELEGRAM_BOT_TOKEN')
    chat_id = config.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ .env 文件中缺少 Telegram 配置")
        print("   需要: TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
        return
    
    # 測試連接
    success = test_telegram(token, chat_id)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 測試完成！系統已準備就緒")
        print("\n下一步：運行 python3 trading_alert_system.py")
    else:
        print("❌ 測試失敗，請檢查配置")
    print("=" * 60)

if __name__ == '__main__':
    main()
