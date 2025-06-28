#!/usr/bin/env python3
"""
改善されたGemini AI分析テストスクリプト
"""

import asyncio
from news_collector_spec import RefinitivNewsCollector
from database_spec import SpecDatabaseManager
import json

def load_config():
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        return json.load(f)

async def test_improved_analysis():
    config = load_config()
    
    # データベース管理とGemini分析器を初期化
    db_manager = SpecDatabaseManager(config['database'])
    collector = RefinitivNewsCollector()
    
    print('=== Gemini 1.5 Pro テスト ===')
    print(f"使用モデル: {config['gemini_integration']['model']}")
    print(f"フォールバックモデル: {config['gemini_integration']['fallback_model']}")
    print(f"重要度閾値: {config['gemini_integration']['cost_optimization']['importance_threshold']}")
    print(f"日次予算: ${config['gemini_integration']['cost_optimization']['max_daily_cost_usd']}")
    
    print('\n既存ニュースを取得中...')
    
    # 既存の全ニュースを取得（AI分析されていないか品質の低いもの）
    connection = db_manager.get_connection()
    with connection as conn:
        cursor = conn.cursor()
        sql = '''
            SELECT news_id, title, body, source, publish_time, related_metals
            FROM news_table 
            WHERE (summary IS NULL OR summary = '' OR length(summary) < 50)
            AND is_manual = FALSE
            ORDER BY publish_time DESC
            LIMIT 15
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
    
    # 各ニュースのタイトルを表示
    print('\n--- 分析対象ニュース ---')
    for i, news in enumerate(news_list[:5]):
        print(f"{i+1}. {news['title'][:80]}...")
    
    # AI分析実行
    print('\nGemini 1.5 Pro AI分析を開始...')
    analysis_results = await collector.gemini_analyzer.analyze_news_batch(news_list)
    
    print(f'\nAI分析完了: {len(analysis_results)} 件')
    
    # 分析結果をデータベースに保存＆表示
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
                print(f'\n✅ 保存完了: {news_id[:30]}...')
                print(f"   要約: {result.summary}")
                print(f"   センチメント: {result.sentiment}")
                print(f"   キーワード: {result.keywords}")
                print(f"   重要度: {result.importance_score}/10")
                print(f"   コスト見積: ${result.cost_estimate:.6f}")
                saved_count += 1
            else:
                print(f'❌ 保存失敗: {news_id}')
        except Exception as e:
            print(f'❌ 保存エラー {news_id}: {e}')
    
    print(f'\n=== 処理結果 ===')
    print(f'分析対象: {len(news_list)} 件')
    print(f'分析成功: {len(analysis_results)} 件')
    print(f'保存成功: {saved_count} 件')
    
    # 統計情報を表示
    stats = collector.gemini_analyzer.get_analysis_stats()
    print('\n=== Gemini分析統計 ===')
    print(f'総分析数: {stats["total_analyzed"]}')
    print(f'成功: {stats["successful_analyses"]}')
    print(f'失敗: {stats["failed_analyses"]}')
    print(f'API呼び出し: {stats["api_calls_made"]}')
    print(f'総コスト: ${stats["total_cost"]:.6f}')
    print(f'日次コスト: ${stats["daily_cost"]:.6f}')
    print(f'残り予算: ${stats["remaining_daily_budget"]:.6f}')

if __name__ == "__main__":
    # 非同期実行
    asyncio.run(test_improved_analysis())