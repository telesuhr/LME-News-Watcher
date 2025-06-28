#!/usr/bin/env python3
"""
実際のニュースデータで新プロンプトテスト
"""

import asyncio
from news_collector_spec import RefinitivNewsCollector
from database_spec import SpecDatabaseManager
import json

def load_config():
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        return json.load(f)

async def test_real_news_analysis():
    config = load_config()
    
    # データベース管理とGemini分析器を初期化
    db_manager = SpecDatabaseManager(config['database'])
    collector = RefinitivNewsCollector()
    
    print('=== 実際のニュースで新プロンプトテスト ===')
    
    # 実際の未分析ニュースを3件取得
    connection = db_manager.get_connection()
    with connection as conn:
        cursor = conn.cursor()
        sql = '''
            SELECT news_id, title, body, source
            FROM news_table 
            WHERE (summary IS NULL OR summary = '' OR length(summary) < 50)
            AND is_manual = FALSE
            AND length(body) > 200
            ORDER BY publish_time DESC
            LIMIT 3
        '''
        cursor.execute(sql)
        results = cursor.fetchall()
        
        if db_manager.db_type == 'postgresql':
            columns = [desc[0] for desc in cursor.description]
            news_list = [dict(zip(columns, row)) for row in results]
        else:
            columns = [column[0] for column in cursor.description]  
            news_list = [dict(zip(columns, row)) for row in results]
    
    print(f'テスト対象: {len(news_list)} 件の実際のニュース')
    
    if not news_list:
        print('テスト対象のニュースがありません。')
        return
    
    # 各ニュースを分析
    for i, news in enumerate(news_list):
        print(f'\n--- [{i+1}/{len(news_list)}] ---')
        print(f"タイトル: {news['title']}")
        print(f"ソース: {news['source']}")
        print(f"本文(抜粋): {news['body'][:200]}...")
        
        try:
            # AI分析実行
            result = await collector.gemini_analyzer.analyze_news_item(news)
            
            if result:
                print(f"\n✅ AI分析結果:")
                print(f"要約: {result.summary}")
                print(f"センチメント: {result.sentiment}")
                print(f"キーワード: {result.keywords}")
                print(f"重要度: {result.importance_score}/10")
                
                # データベースに保存
                success = db_manager.update_news_analysis(news['news_id'], {
                    'summary': result.summary,
                    'sentiment': result.sentiment, 
                    'keywords': result.keywords,
                    'importance_score': result.importance_score
                })
                
                if success:
                    print("✅ データベース保存成功")
                else:
                    print("❌ データベース保存失敗")
            else:
                print("❌ 分析失敗（条件に合わない）")
                
        except Exception as e:
            print(f"❌ エラー: {e}")
        
        print("-" * 100)
        
        # 次の分析前に少し待機
        if i < len(news_list) - 1:
            await asyncio.sleep(3)
    
    print("\n=== テスト完了 ===")
    print("ブラウザでUIを確認して、改善された分析結果をご確認ください。")

if __name__ == "__main__":
    asyncio.run(test_real_news_analysis())