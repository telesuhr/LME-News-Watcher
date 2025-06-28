#!/usr/bin/env python3
"""
改善されたGemini 1.5 Pro で一括AI分析
"""

import asyncio
from news_collector_spec import RefinitivNewsCollector
from database_spec import SpecDatabaseManager
import json
import time

def load_config():
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        return json.load(f)

async def bulk_analyze_news():
    config = load_config()
    
    # データベース管理とGemini分析器を初期化
    db_manager = SpecDatabaseManager(config['database'])
    collector = RefinitivNewsCollector()
    
    print('=== Gemini 1.5 Pro 一括分析 ===')
    
    # 未分析のニュースを取得
    connection = db_manager.get_connection()
    with connection as conn:
        cursor = conn.cursor()
        sql = '''
            SELECT news_id, title, body, source, publish_time, related_metals
            FROM news_table 
            WHERE (summary IS NULL OR summary = '' OR length(summary) < 30)
            AND is_manual = FALSE
            AND length(body) > 100
            ORDER BY publish_time DESC
            LIMIT 10
        '''
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if db_manager.db_type == 'postgresql':
            columns = [desc[0] for desc in cursor.description]
            news_list = [dict(zip(columns, row)) for row in results]
        else:
            columns = [column[0] for column in cursor.description]  
            news_list = [dict(zip(columns, row)) for row in results]
    
    print(f'分析対象: {len(news_list)} 件のニュース')
    
    if not news_list:
        print('分析対象のニュースがありません。')
        return
    
    total_success = 0
    total_cost = 0.0
    
    # 1件ずつ分析して結果を即座に確認
    for i, news in enumerate(news_list):
        print(f'\n--- [{i+1}/{len(news_list)}] 分析中 ---')
        print(f"タイトル: {news['title'][:100]}...")
        
        try:
            # 個別分析
            result = await collector.gemini_analyzer.analyze_news_item(news)
            
            if result:
                # データベース保存
                success = db_manager.update_news_analysis(news['news_id'], {
                    'summary': result.summary,
                    'sentiment': result.sentiment, 
                    'keywords': result.keywords,
                    'importance_score': result.importance_score
                })
                
                if success:
                    print(f"✅ 分析・保存成功")
                    print(f"   要約: {result.summary}")
                    print(f"   センチメント: {result.sentiment}")
                    print(f"   重要度: {result.importance_score}/10")
                    print(f"   コスト: ${result.cost_estimate:.6f}")
                    
                    total_success += 1
                    total_cost += result.cost_estimate or 0
                else:
                    print(f"❌ 保存失敗")
            else:
                print(f"❌ 分析失敗 - 条件に合わない")
        
        except Exception as e:
            print(f"❌ エラー: {e}")
        
        # API制限対策で少し待機
        if i < len(news_list) - 1:
            print("   (5秒待機...)")
            await asyncio.sleep(5)
    
    print(f'\n=== 最終結果 ===')
    print(f'分析対象: {len(news_list)} 件')
    print(f'成功: {total_success} 件')
    print(f'総コスト: ${total_cost:.6f}')
    
    # 統計情報
    stats = collector.gemini_analyzer.get_analysis_stats()
    print(f'累計総コスト: ${stats["total_cost"]:.6f}')
    print(f'残り予算: ${stats["remaining_daily_budget"]:.6f}')

if __name__ == "__main__":
    asyncio.run(bulk_analyze_news())