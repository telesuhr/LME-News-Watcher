#!/usr/bin/env python3
"""
安全なクエリのテスト
"""

import eikon as ek
import json
from datetime import datetime, timedelta

def test_safe_queries():
    """安全なクエリをテスト"""
    
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    ek.set_app_key(config["eikon_api_key"])
    
    # 新しい安全なクエリをテスト
    query_categories = config["news_collection"]["query_categories"]
    
    total_success = 0
    total_errors = 0
    
    for category, queries in query_categories.items():
        print(f"\n=== {category} ===")
        for query in queries:
            try:
                headlines = ek.get_news_headlines(query=query, count=5)
                count = len(headlines) if headlines is not None else 0
                print(f"✓ '{query}': {count} 件")
                total_success += 1
            except Exception as e:
                print(f"✗ '{query}': {type(e).__name__} - {str(e)[:100]}")
                total_errors += 1
    
    print(f"\n=== 結果 ===")
    print(f"成功: {total_success}")
    print(f"失敗: {total_errors}")
    print(f"成功率: {total_success/(total_success+total_errors)*100:.1f}%")

if __name__ == "__main__":
    test_safe_queries()