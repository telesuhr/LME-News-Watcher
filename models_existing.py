#!/usr/bin/env python3
"""
既存のlme_reportingデータベースとの統合用データモデル
既存のnews_dataテーブル構造に合わせた設計
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List
import json

@dataclass
class ExistingNewsItem:
    """既存news_dataテーブル用ニュースアイテム"""
    headline: str
    date: date
    category: str
    body_text: Optional[str] = None
    source_code: Optional[str] = None
    story_id: Optional[str] = None
    published_at: Optional[datetime] = None
    priority_score: int = 0
    language: str = "en"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'date': self.date,
            'category': self.category,
            'headline': self.headline,
            'body_text': self.body_text,
            'source_code': self.source_code,
            'story_id': self.story_id,
            'published_at': self.published_at,
            'priority_score': self.priority_score,
            'language': self.language
        }

# 既存テーブル対応のスキーマ
EXISTING_TABLE_SCHEMA = {
    "news_collector_stats": """
        CREATE TABLE IF NOT EXISTS news_collector_stats (
            id SERIAL PRIMARY KEY,
            collection_date TIMESTAMP NOT NULL,
            total_collected INTEGER DEFAULT 0,
            successful_queries INTEGER DEFAULT 0,
            failed_queries INTEGER DEFAULT 0,
            high_priority_count INTEGER DEFAULT 0,
            medium_priority_count INTEGER DEFAULT 0,
            low_priority_count INTEGER DEFAULT 0,
            duplicate_removed INTEGER DEFAULT 0,
            execution_time_seconds DECIMAL(10,3) DEFAULT 0,
            api_calls_made INTEGER DEFAULT 0,
            errors_encountered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    
    "indexes": [
        "CREATE INDEX IF NOT EXISTS idx_news_collector_stats_date ON news_collector_stats(collection_date);"
    ]
}

class ExistingDatabaseManager:
    """既存データベース統合管理クラス"""
    
    def __init__(self, db_manager):
        """
        初期化
        
        Args:
            db_manager: 既存のDatabaseManagerインスタンス
        """
        self.db_manager = db_manager
        self.logger = db_manager.logger
    
    def create_collector_tables(self) -> bool:
        """NewsCollector専用テーブル作成"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 統計テーブル作成
                cursor.execute(EXISTING_TABLE_SCHEMA["news_collector_stats"])
                
                # インデックス作成
                for index_sql in EXISTING_TABLE_SCHEMA["indexes"]:
                    try:
                        cursor.execute(index_sql)
                    except Exception as e:
                        self.logger.warning(f"インデックス作成警告: {e}")
                
                self.logger.info("NewsCollector専用テーブル作成完了")
                return True
                
        except Exception as e:
            self.logger.error(f"テーブル作成エラー: {e}")
            return False
    
    def insert_existing_news_item(self, news_item: ExistingNewsItem) -> bool:
        """既存news_dataテーブルにニュース挿入"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                    INSERT INTO news_data (
                        date, category, headline, body_text, source_code, 
                        story_id, published_at, priority_score, language
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT DO NOTHING
                """
                
                cursor.execute(sql, (
                    news_item.date,
                    news_item.category,
                    news_item.headline,
                    news_item.body_text,
                    news_item.source_code,
                    news_item.story_id,
                    news_item.published_at,
                    news_item.priority_score,
                    news_item.language
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"既存ニュースアイテム挿入エラー: {e}")
            return False
    
    def insert_news_batch_existing(self, news_items: List[ExistingNewsItem]) -> int:
        """既存テーブルへの一括挿入"""
        successful_inserts = 0
        
        for news_item in news_items:
            if self.insert_existing_news_item(news_item):
                successful_inserts += 1
        
        self.logger.info(f"既存テーブル一括挿入完了: {successful_inserts}/{len(news_items)} 件成功")
        return successful_inserts
    
    def insert_collector_stats(self, stats_data: dict) -> bool:
        """NewsCollector統計挿入"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                sql = """
                    INSERT INTO news_collector_stats (
                        collection_date, total_collected, successful_queries, failed_queries,
                        high_priority_count, medium_priority_count, low_priority_count,
                        duplicate_removed, execution_time_seconds, api_calls_made, errors_encountered
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql, (
                    stats_data['collection_date'],
                    stats_data['total_collected'],
                    stats_data['successful_queries'],
                    stats_data['failed_queries'],
                    stats_data['high_priority_count'],
                    stats_data['medium_priority_count'],
                    stats_data['low_priority_count'],
                    stats_data['duplicate_removed'],
                    stats_data['execution_time_seconds'],
                    stats_data['api_calls_made'],
                    stats_data['errors_encountered']
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"統計データ挿入エラー: {e}")
            return False