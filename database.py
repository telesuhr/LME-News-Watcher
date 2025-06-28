#!/usr/bin/env python3
"""
データベース接続・操作モジュール
PostgreSQL/SQL Server両対応設計
"""

import psycopg2
import pyodbc
from psycopg2.extras import DictCursor
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import json
from contextlib import contextmanager

from models import NewsItem, CollectionStats, DATABASE_SCHEMA, SQLSERVER_SCHEMA

class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初期化
        
        Args:
            config: データベース設定
        """
        self.config = config
        self.db_type = config.get("database_type", "postgresql").lower()
        self.logger = logging.getLogger(__name__)
        
        # 接続パラメータ設定
        if self.db_type == "postgresql":
            self.connection_params = {
                'host': config.get('host', 'localhost'),
                'port': config.get('port', 5432),
                'database': config.get('database', 'news_collector'),
                'user': config.get('user', 'postgres'),
                'password': config.get('password', '')
            }
        elif self.db_type == "sqlserver":
            self.connection_params = {
                'server': config.get('server', 'localhost'),
                'database': config.get('database', 'news_collector'),
                'user': config.get('user'),
                'password': config.get('password'),
                'driver': config.get('driver', 'ODBC Driver 17 for SQL Server')
            }
    
    @contextmanager
    def get_connection(self):
        """データベース接続コンテキストマネージャー"""
        connection = None
        try:
            if self.db_type == "postgresql":
                connection = psycopg2.connect(**self.connection_params)
            elif self.db_type == "sqlserver":
                conn_str = (
                    f"DRIVER={{{self.connection_params['driver']}}};"
                    f"SERVER={self.connection_params['server']};"
                    f"DATABASE={self.connection_params['database']};"
                    f"UID={self.connection_params['user']};"
                    f"PWD={self.connection_params['password']};"
                )
                connection = pyodbc.connect(conn_str)
            
            yield connection
            connection.commit()
            
        except Exception as e:
            if connection:
                connection.rollback()
            self.logger.error(f"データベース操作エラー: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def create_tables(self) -> bool:
        """テーブル作成"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # スキーマ選択
                schema = DATABASE_SCHEMA if self.db_type == "postgresql" else SQLSERVER_SCHEMA
                
                # テーブル作成
                for table_name, create_sql in schema.items():
                    if table_name != "indexes":
                        self.logger.info(f"テーブル作成中: {table_name}")
                        cursor.execute(create_sql)
                
                # インデックス作成
                for index_sql in schema["indexes"]:
                    try:
                        cursor.execute(index_sql)
                    except Exception as e:
                        self.logger.warning(f"インデックス作成警告: {e}")
                
                self.logger.info("データベーステーブル作成完了")
                return True
                
        except Exception as e:
            self.logger.error(f"テーブル作成エラー: {e}")
            return False
    
    def insert_news_item(self, news_item: NewsItem) -> bool:
        """ニュースアイテム挿入"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        INSERT INTO news_items (
                            story_id, headline, source, published_date, body, 
                            priority_score, metal_category, keywords, query_type
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (story_id) DO UPDATE SET
                            headline = EXCLUDED.headline,
                            body = EXCLUDED.body,
                            priority_score = EXCLUDED.priority_score,
                            updated_at = CURRENT_TIMESTAMP
                    """
                elif self.db_type == "sqlserver":
                    sql = """
                        MERGE news_items AS target
                        USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)) AS source 
                               (story_id, headline, source, published_date, body, 
                                priority_score, metal_category, keywords, query_type)
                        ON target.story_id = source.story_id
                        WHEN MATCHED THEN
                            UPDATE SET headline = source.headline,
                                      body = source.body,
                                      priority_score = source.priority_score,
                                      updated_at = GETDATE()
                        WHEN NOT MATCHED THEN
                            INSERT (story_id, headline, source, published_date, body,
                                   priority_score, metal_category, keywords, query_type)
                            VALUES (source.story_id, source.headline, source.source, 
                                   source.published_date, source.body, source.priority_score,
                                   source.metal_category, source.keywords, source.query_type);
                    """
                
                cursor.execute(sql, (
                    news_item.story_id,
                    news_item.headline,
                    news_item.source,
                    news_item.published_date,
                    news_item.body,
                    news_item.priority_score,
                    news_item.metal_category,
                    json.dumps(news_item.keywords) if news_item.keywords else None,
                    news_item.query_type
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"ニュースアイテム挿入エラー: {e}")
            return False
    
    def insert_news_batch(self, news_items: List[NewsItem]) -> int:
        """ニュースアイテム一括挿入"""
        successful_inserts = 0
        
        for news_item in news_items:
            if self.insert_news_item(news_item):
                successful_inserts += 1
        
        self.logger.info(f"一括挿入完了: {successful_inserts}/{len(news_items)} 件成功")
        return successful_inserts
    
    def insert_collection_stats(self, stats: CollectionStats) -> bool:
        """収集統計挿入"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        INSERT INTO collection_stats (
                            collection_date, total_collected, successful_queries, failed_queries,
                            high_priority_count, medium_priority_count, low_priority_count,
                            duplicate_removed, execution_time_seconds, api_calls_made, errors_encountered
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                elif self.db_type == "sqlserver":
                    sql = """
                        INSERT INTO collection_stats (
                            collection_date, total_collected, successful_queries, failed_queries,
                            high_priority_count, medium_priority_count, low_priority_count,
                            duplicate_removed, execution_time_seconds, api_calls_made, errors_encountered
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                
                cursor.execute(sql, (
                    stats.collection_date,
                    stats.total_collected,
                    stats.successful_queries,
                    stats.failed_queries,
                    stats.high_priority_count,
                    stats.medium_priority_count,
                    stats.low_priority_count,
                    stats.duplicate_removed,
                    stats.execution_time_seconds,
                    stats.api_calls_made,
                    stats.errors_encountered
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"統計データ挿入エラー: {e}")
            return False
    
    def get_recent_news(self, days: int = 7, limit: int = 100) -> List[Dict]:
        """最近のニュース取得"""
        try:
            with self.get_connection() as conn:
                if self.db_type == "postgresql":
                    cursor = conn.cursor(cursor_factory=DictCursor)
                    sql = """
                        SELECT * FROM news_items 
                        WHERE published_date >= NOW() - INTERVAL '%s days'
                        ORDER BY priority_score DESC, published_date DESC
                        LIMIT %s
                    """
                elif self.db_type == "sqlserver":
                    cursor = conn.cursor()
                    sql = """
                        SELECT TOP (?) * FROM news_items 
                        WHERE published_date >= DATEADD(day, -?, GETDATE())
                        ORDER BY priority_score DESC, published_date DESC
                    """
                
                if self.db_type == "postgresql":
                    cursor.execute(sql, (days, limit))
                else:
                    cursor.execute(sql, (limit, days))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"ニュース取得エラー: {e}")
            return []
    
    def get_stats_summary(self, days: int = 30) -> Dict:
        """統計サマリー取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        SELECT 
                            COUNT(*) as total_collections,
                            SUM(total_collected) as total_news,
                            AVG(execution_time_seconds) as avg_execution_time,
                            SUM(api_calls_made) as total_api_calls
                        FROM collection_stats 
                        WHERE collection_date >= NOW() - INTERVAL '%s days'
                    """
                    cursor.execute(sql, (days,))
                elif self.db_type == "sqlserver":
                    sql = """
                        SELECT 
                            COUNT(*) as total_collections,
                            SUM(total_collected) as total_news,
                            AVG(execution_time_seconds) as avg_execution_time,
                            SUM(api_calls_made) as total_api_calls
                        FROM collection_stats 
                        WHERE collection_date >= DATEADD(day, -?, GETDATE())
                    """
                    cursor.execute(sql, (days,))
                
                result = cursor.fetchone()
                return {
                    'total_collections': result[0] or 0,
                    'total_news': result[1] or 0,
                    'avg_execution_time': float(result[2] or 0),
                    'total_api_calls': result[3] or 0
                }
                
        except Exception as e:
            self.logger.error(f"統計取得エラー: {e}")
            return {}
    
    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if self.db_type == "postgresql":
                    cursor.execute("SELECT 1")
                elif self.db_type == "sqlserver":
                    cursor.execute("SELECT 1")
                
                result = cursor.fetchone()
                self.logger.info(f"{self.db_type.upper()} データベース接続成功")
                return True
                
        except Exception as e:
            self.logger.error(f"データベース接続エラー: {e}")
            return False