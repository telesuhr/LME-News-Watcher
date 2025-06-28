#!/usr/bin/env python3
"""
既存ニュースのGemini AI分析テストスクリプト
"""

import asyncio
from news_collector_spec import RefinitivNewsCollector
from database_spec import SpecDatabaseManager
import json

def load_config():
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        return json.load(f)

async def analyze_existing_news():
    config = load_config()
    
    # データベース管理とGemini分析器を初期化
    db_manager = SpecDatabaseManager(config['database'])
    collector = RefinitivNewsCollector()
    
    print('既存ニュースを取得中...')
    
    # 既存の全ニュースを取得（AI分析されていないもの）
    connection = db_manager.get_connection()
    with connection as conn:
        cursor = conn.cursor()
        sql = '''
            SELECT news_id, title, body, source, publish_time, related_metals
            FROM news_table 
            WHERE (summary IS NULL OR summary = '') 
            AND is_manual = FALSE
            ORDER BY publish_time DESC
            LIMIT 20
        '''
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if db_manager.db_type == 'postgresql':
            columns = [desc[0] for desc in cursor.description]
            news_list = [dict(zip(columns, row)) for row in results]
        else:
            columns = [column[0] for column in cursor.description]  
            news_list = [dict(zip(columns, row)) for row in results]
    
    print(f'AI分析対象: {len(news_list)} 件のニュース')
    
    if not news_list:
        print('分析対象のニュースがありません。')
        return
    
    # AI分析実行
    print('Gemini AI分析を開始...')
    analysis_results = await collector.gemini_analyzer.analyze_news_batch(news_list)
    
    print(f'AI分析完了: {len(analysis_results)} 件')
    
    # 分析結果をデータベースに保存
    saved_count = 0
    for news_id, result in analysis_results:
        try:
            success = db_manager.update_news_analysis(news_id, {
                'summary': result.summary,
                'sentiment': result.sentiment, 
                'keywords': result.keywords,
                'importance_score': result.importance_score
            })
            if success:
                print(f'保存完了: {news_id[:30]}... (重要度: {result.importance_score}, センチメント: {result.sentiment})')
                saved_count += 1
            else:
                print(f'保存失敗: {news_id}')
        except Exception as e:
            print(f'保存エラー {news_id}: {e}')
    
    print(f'\n=== 処理結果 ===')
    print(f'分析対象: {len(news_list)} 件')
    print(f'分析成功: {len(analysis_results)} 件')
    print(f'保存成功: {saved_count} 件')
    
    # 統計情報を表示
    stats = collector.gemini_analyzer.get_analysis_stats()
    print('\n=== Gemini分析統計 ===')
    for key, value in stats.items():
        if key != 'rate_limit_status':
            print(f'{key}: {value}')
        else:
            rate_info = value
            print(f'今分のリクエスト: {rate_info.get("requests_this_minute", 0)}')
            print(f'今日のリクエスト: {rate_info.get("requests_today", 0)}')

if __name__ == "__main__":
    # 非同期実行
    asyncio.run(analyze_existing_news())