#!/usr/bin/env python3
"""
EIKON API接続テストスクリプト
400 Bad Requestエラーの診断用
"""

import eikon as ek
import json
import sys
from datetime import datetime

def test_eikon_connection():
    """EIKON API接続をテスト"""
    
    # 設定ファイル読み込み
    try:
        with open('config_spec.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        api_key = config["eikon_api_key"]
        print(f"APIキー: {api_key[:10]}...")
    except Exception as e:
        print(f"設定ファイル読み込みエラー: {e}")
        return False
    
    # EIKON初期化
    try:
        ek.set_app_key(api_key)
        print("✓ EIKON APIキー設定完了")
    except Exception as e:
        print(f"✗ EIKON APIキー設定エラー: {e}")
        return False
    
    # 1. 基本的な接続テスト
    print("\n=== 基本接続テスト ===")
    try:
        # 最もシンプルなAPI呼び出し
        symbols = ek.get_symbology(['AAPL.O'], from_symbol_type='RIC', to_symbol_type='ISIN')
        print("✓ 基本API呼び出し成功")
        print(f"レスポンス: {symbols}")
    except Exception as e:
        print(f"✗ 基本API呼び出し失敗: {e}")
        return False
    
    # 2. ニュースヘッドライン取得テスト（最小パラメータ）
    print("\n=== ニュースAPI基本テスト ===")
    try:
        # 最もシンプルなニュース取得
        headlines = ek.get_news_headlines(count=5)
        print(f"✓ ニュースヘッドライン取得成功: {len(headlines)} 件")
        if not headlines.empty:
            print(f"カラム: {list(headlines.columns)}")
            print(f"最初の記事: {headlines.iloc[0]['text'] if 'text' in headlines.columns else 'N/A'}")
    except Exception as e:
        print(f"✗ ニュースヘッドライン取得失敗: {e}")
        return False
    
    # 3. 特定クエリテスト
    print("\n=== 特定クエリテスト ===")
    test_queries = [
        "copper",
        "metals", 
        "LME",
        "mining"
    ]
    
    for query in test_queries:
        try:
            headlines = ek.get_news_headlines(query=query, count=3)
            print(f"✓ クエリ '{query}': {len(headlines)} 件")
        except Exception as e:
            print(f"✗ クエリ '{query}' 失敗: {e}")
    
    # 4. 詳細なエラー情報収集
    print("\n=== 詳細診断 ===")
    try:
        # 問題のあったクエリを再テスト
        print("問題クエリのテスト:")
        problematic_queries = ["London Metal Exchange", "LME prices"]
        for query in problematic_queries:
            try:
                result = ek.get_news_headlines(query=query, count=1)
                print(f"✓ '{query}': 成功")
            except Exception as e:
                print(f"✗ '{query}': {type(e).__name__} - {e}")
                
                # より詳細なエラー情報
                if hasattr(e, 'code'):
                    print(f"   エラーコード: {e.code}")
                if hasattr(e, 'message'):
                    print(f"   メッセージ: {e.message}")
                    
    except Exception as e:
        print(f"詳細診断エラー: {e}")
    
    return True

if __name__ == "__main__":
    print("EIKON API接続テスト開始")
    print(f"実行時刻: {datetime.now()}")
    print("=" * 50)
    
    success = test_eikon_connection()
    
    print("=" * 50)
    if success:
        print("✓ テスト完了")
    else:
        print("✗ テスト失敗")