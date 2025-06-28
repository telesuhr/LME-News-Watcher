#!/usr/bin/env python3
"""
手動AI分析機能テスト
"""

import asyncio
from database_detector import DatabaseDetector
from database_spec import SpecDatabaseManager
from news_collector_spec import RefinitivNewsCollector

async def test_manual_analysis():
    """手動AI分析テスト"""
    print("=== 手動AI分析機能テスト ===\n")
    
    # データベース自動検出
    detector = DatabaseDetector()
    db_type, db_config = detector.detect_and_configure()
    print(f"使用データベース: {db_type}\n")
    
    # マネージャー初期化
    db_manager = SpecDatabaseManager(db_config)
    collector = RefinitivNewsCollector()
    
    # 最新のニュースを1件取得
    connection = db_manager.get_connection()
    with connection as conn:
        cursor = conn.cursor()
        sql = """
            SELECT news_id, title, body, source, publish_time, 
                   summary, sentiment, keywords
            FROM news_table 
            WHERE is_manual = FALSE 
            AND (summary IS NULL OR summary = '')
            ORDER BY publish_time DESC
            LIMIT 1
        """
        cursor.execute(sql)
        result = cursor.fetchone()
        
        if not result:
            print("テスト対象のニュースがありません")
            return
        
        # 結果を辞書に変換
        if db_manager.db_type == 'postgresql':
            columns = [desc[0] for desc in cursor.description]
        else:
            columns = [column[0] for column in cursor.description]
        
        news = dict(zip(columns, result))
    
    print(f"テスト対象ニュース:")
    print(f"ID: {news['news_id']}")
    print(f"タイトル: {news['title'][:80]}...")
    print(f"既存の要約: {news['summary'][:80] if news['summary'] else 'なし'}")
    print()
    
    # AI分析実行
    print("AI分析を実行中...")
    try:
        result = await collector.gemini_analyzer.analyze_news_item(news)
        
        if result:
            print("\n✅ AI分析成功!")
            print(f"要約: {result.summary}")
            print(f"センチメント: {result.sentiment}")
            print(f"キーワード: {result.keywords}")
            print(f"重要度: {result.importance_score}/10")
            print(f"推定コスト: ${result.cost_estimate:.6f}")
            
            # データベース更新
            success = db_manager.update_news_analysis(news['news_id'], {
                'summary': result.summary,
                'sentiment': result.sentiment,
                'keywords': result.keywords,
                'importance_score': result.importance_score
            })
            
            if success:
                print("\n✅ データベース更新成功!")
            else:
                print("\n❌ データベース更新失敗")
        else:
            print("\n❌ AI分析失敗")
            
    except Exception as e:
        print(f"\n❌ エラー: {e}")
    
    print("\n=== テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_manual_analysis())