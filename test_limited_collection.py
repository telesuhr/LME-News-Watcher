#!/usr/bin/env python3
"""
制限されたニュース収集テスト
"""

import eikon as ek
import json
from datetime import datetime, timedelta
from news_collector_spec import RefinitivNewsCollector

def test_limited_collection():
    """制限された条件でニュース収集をテスト"""
    
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    ek.set_app_key(config["eikon_api_key"])
    
    # 少数のクエリでテスト
    test_queries = ["copper", "metals", "mining"]
    
    print("=== 制限されたニュース収集テスト ===")
    total_success = 0
    total_error = 0
    
    for query in test_queries:
        try:
            print(f"\nテスト: '{query}'")
            headlines = ek.get_news_headlines(query=query, count=20)
            count = len(headlines) if headlines is not None else 0
            print(f"✓ 成功: {count} 件")
            total_success += 1
            
            # 1秒待機
            import time
            time.sleep(1)
            
        except Exception as e:
            print(f"✗ 失敗: {type(e).__name__} - {str(e)[:100]}")
            total_error += 1
    
    print(f"\n=== 結果 ===")
    print(f"成功: {total_success}, 失敗: {total_error}")
    
    if total_success > 0:
        print("\n=== 実際のニュース収集テスト ===")
        try:
            collector = RefinitivNewsCollector()
            
            # テスト用に数を制限
            start_date = datetime.now() - timedelta(hours=1)
            end_date = datetime.now()
            
            # 1つのクエリだけテスト
            result = collector._get_news_by_query("copper", start_date, end_date)
            print(f"ニュース収集結果: {len(result)} 件")
            
            if result:
                print("✓ ニュース収集成功")
                return True
            else:
                print("- ニュースは見つかりませんでした（エラーではありません）")
                return True
                
        except Exception as e:
            print(f"✗ ニュース収集エラー: {e}")
            return False
    
    return total_success > 0

if __name__ == "__main__":
    success = test_limited_collection()
    print(f"\n最終結果: {'成功' if success else '失敗'}")