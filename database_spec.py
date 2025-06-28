#!/usr/bin/env python3
"""
仕様書対応データベース管理モジュール
PostgreSQL/SQL Server両対応設計
"""

import psycopg2
import pyodbc
from psycopg2.extras import DictCursor
from typing import List, Dict, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

from models_spec import NewsArticle, SystemStats, SPEC_DATABASE_SCHEMA, SQLSERVER_SPEC_SCHEMA, NewsSearchFilter

class SpecDatabaseManager:
    """仕様書対応データベース管理クラス"""
    
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
                'database': config.get('database', 'lme_reporting'),
                'user': config.get('user', 'postgres'),
                'password': config.get('password', '')
            }
        elif self.db_type == "sqlserver":
            self.connection_params = {
                'server': config.get('server', 'localhost'),
                'database': config.get('database', 'lme_reporting'),
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
                schema = SPEC_DATABASE_SCHEMA if self.db_type == "postgresql" else SQLSERVER_SPEC_SCHEMA
                
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
    
    def insert_news_article(self, article: NewsArticle) -> bool:
        """ニュース記事挿入"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        INSERT INTO news_table (
                            news_id, title, body, publish_time, acquire_time, 
                            source, url, sentiment, summary, keywords, 
                            related_metals, is_manual
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (news_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            body = EXCLUDED.body,
                            source = EXCLUDED.source,
                            url = EXCLUDED.url,
                            related_metals = EXCLUDED.related_metals
                    """
                elif self.db_type == "sqlserver":
                    sql = """
                        MERGE news_table AS target
                        USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) AS source 
                               (news_id, title, body, publish_time, acquire_time, 
                                source, url, sentiment, summary, keywords, 
                                related_metals, is_manual)
                        ON target.news_id = source.news_id
                        WHEN MATCHED THEN
                            UPDATE SET title = source.title,
                                      body = source.body,
                                      source = source.source,
                                      url = source.url,
                                      related_metals = source.related_metals
                        WHEN NOT MATCHED THEN
                            INSERT (news_id, title, body, publish_time, acquire_time,
                                   source, url, sentiment, summary, keywords,
                                   related_metals, is_manual)
                            VALUES (source.news_id, source.title, source.body, 
                                   source.publish_time, source.acquire_time, source.source,
                                   source.url, source.sentiment, source.summary, 
                                   source.keywords, source.related_metals, source.is_manual);
                    """
                
                cursor.execute(sql, (
                    article.news_id,
                    article.title,
                    article.body,
                    article.publish_time,
                    article.acquire_time,
                    article.source,
                    article.url,
                    article.sentiment,
                    article.summary,
                    article.keywords,
                    article.related_metals,
                    article.is_manual
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"ニュース記事挿入エラー: {e}")
            return False
    
    def insert_news_batch(self, articles: List[NewsArticle]) -> int:
        """ニュース記事一括挿入"""
        successful_inserts = 0
        
        for article in articles:
            if self.insert_news_article(article):
                successful_inserts += 1
        
        self.logger.info(f"一括挿入完了: {successful_inserts}/{len(articles)} 件成功")
        return successful_inserts
    
    def insert_system_stats(self, stats: SystemStats) -> bool:
        """システム統計挿入"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        INSERT INTO system_stats (
                            collection_date, total_collected, successful_queries, failed_queries,
                            api_calls_made, errors_encountered, execution_time_seconds
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                elif self.db_type == "sqlserver":
                    sql = """
                        INSERT INTO system_stats (
                            collection_date, total_collected, successful_queries, failed_queries,
                            api_calls_made, errors_encountered, execution_time_seconds
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                
                cursor.execute(sql, (
                    stats.collection_date,
                    stats.total_collected,
                    stats.successful_queries,
                    stats.failed_queries,
                    stats.api_calls_made,
                    stats.errors_encountered,
                    stats.execution_time_seconds
                ))
                
                return True
                
        except Exception as e:
            self.logger.error(f"統計データ挿入エラー: {e}")
            return False
    
    def search_news(self, search_filter: NewsSearchFilter) -> List[Dict]:
        """ニュース検索"""
        try:
            with self.get_connection() as conn:
                if self.db_type == "postgresql":
                    cursor = conn.cursor(cursor_factory=DictCursor)
                else:
                    cursor = conn.cursor()
                
                # WHERE句とパラメータ生成
                where_clause, params = search_filter.to_sql_where_clause(self.db_type)
                
                if self.db_type == "postgresql":
                    sql = f"""
                        SELECT * FROM news_table 
                        WHERE {where_clause}
                        ORDER BY publish_time DESC
                        LIMIT %s OFFSET %s
                    """
                    params.extend([search_filter.limit, search_filter.offset])
                else:
                    sql = f"""
                        SELECT * FROM news_table 
                        WHERE {where_clause}
                        ORDER BY publish_time DESC
                        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                    """
                    params.extend([search_filter.offset, search_filter.limit])
                
                cursor.execute(sql, params)
                
                if self.db_type == "postgresql":
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"ニュース検索エラー: {e}")
            return []
    
    def get_latest_news(self, limit: int = 50) -> List[Dict]:
        """最新ニュース取得"""
        search_filter = NewsSearchFilter()
        search_filter.limit = limit
        return self.search_news(search_filter)
    
    def get_news_by_id(self, news_id: str) -> Optional[Dict]:
        """IDによるニュース取得"""
        try:
            with self.get_connection() as conn:
                if self.db_type == "postgresql":
                    cursor = conn.cursor(cursor_factory=DictCursor)
                    sql = "SELECT * FROM news_table WHERE news_id = %s"
                else:
                    cursor = conn.cursor()
                    sql = "SELECT * FROM news_table WHERE news_id = ?"
                
                cursor.execute(sql, (news_id,))
                result = cursor.fetchone()
                
                if result:
                    if self.db_type == "postgresql":
                        return dict(result)
                    else:
                        columns = [column[0] for column in cursor.description]
                        return dict(zip(columns, result))
                
                return None
                
        except Exception as e:
            self.logger.error(f"ニュース取得エラー: {e}")
            return None
    
    def get_news_count(self, search_filter: NewsSearchFilter = None) -> int:
        """ニュース件数取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if search_filter:
                    where_clause, params = search_filter.to_sql_where_clause(self.db_type)
                    sql = f"SELECT COUNT(*) FROM news_table WHERE {where_clause}"
                    cursor.execute(sql, params)
                else:
                    sql = "SELECT COUNT(*) FROM news_table"
                    cursor.execute(sql)
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            self.logger.error(f"件数取得エラー: {e}")
            return 0
    
    def get_sources_list(self) -> List[str]:
        """ソース一覧取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = "SELECT DISTINCT source FROM news_table ORDER BY source"
                cursor.execute(sql)
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"ソース一覧取得エラー: {e}")
            return []
    
    def get_related_metals_list(self) -> List[str]:
        """関連金属一覧取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = "SELECT DISTINCT related_metals FROM news_table WHERE related_metals IS NOT NULL"
                cursor.execute(sql)
                
                all_metals = set()
                for row in cursor.fetchall():
                    if row[0]:
                        metals = [metal.strip() for metal in row[0].split(',')]
                        all_metals.update(metals)
                
                return sorted(list(all_metals))
                
        except Exception as e:
            self.logger.error(f"関連金属一覧取得エラー: {e}")
            return []
    
    def delete_news_by_id(self, news_id: str) -> bool:
        """ニュース削除（手動登録のみ）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = "DELETE FROM news_table WHERE news_id = %s AND is_manual = TRUE"
                else:
                    sql = "DELETE FROM news_table WHERE news_id = ? AND is_manual = 1"
                
                cursor.execute(sql, (news_id,))
                
                if cursor.rowcount > 0:
                    self.logger.info(f"ニュース削除成功: {news_id}")
                    return True
                else:
                    self.logger.warning(f"削除対象ニュースなし: {news_id}")
                    return False
                
        except Exception as e:
            self.logger.error(f"ニュース削除エラー: {e}")
            return False
    
    def get_duplicate_news_ids(self, days_back: int = 7) -> List[str]:
        """重複ニュースID取得（過去N日間）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        SELECT news_id FROM news_table 
                        WHERE acquire_time >= NOW() - INTERVAL '%s days'
                    """
                    cursor.execute(sql, (days_back,))
                else:
                    sql = """
                        SELECT news_id FROM news_table 
                        WHERE acquire_time >= DATEADD(day, -?, GETDATE())
                    """
                    cursor.execute(sql, (days_back,))
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"重複チェックエラー: {e}")
            return []
    
    def update_news_analysis(self, news_id: str, analysis_data: Dict) -> bool:
        """ニュース分析結果更新"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 更新フィールドを動的に構築
                update_fields = []
                values = []
                
                if analysis_data.get('summary'):
                    update_fields.append('summary = %s' if self.db_type == "postgresql" else 'summary = ?')
                    values.append(analysis_data['summary'])
                
                if analysis_data.get('sentiment'):
                    update_fields.append('sentiment = %s' if self.db_type == "postgresql" else 'sentiment = ?')
                    values.append(analysis_data['sentiment'])
                
                if analysis_data.get('keywords'):
                    update_fields.append('keywords = %s' if self.db_type == "postgresql" else 'keywords = ?')
                    values.append(analysis_data['keywords'])
                
                if analysis_data.get('importance_score') is not None:
                    # importance_scoreを新しいカラムとして追加する場合
                    # まずはkeywordsフィールドに重要度情報を含める
                    current_keywords = analysis_data.get('keywords', '')
                    importance_info = f"[重要度:{analysis_data['importance_score']}/10]"
                    if current_keywords:
                        enhanced_keywords = f"{current_keywords} {importance_info}"
                    else:
                        enhanced_keywords = importance_info
                    
                    # keywordsフィールドに重要度も含める
                    if 'keywords = %s' not in ' '.join(update_fields) and 'keywords = ?' not in ' '.join(update_fields):
                        update_fields.append('keywords = %s' if self.db_type == "postgresql" else 'keywords = ?')
                        values.append(enhanced_keywords)
                    else:
                        # 既にkeywordsが設定されている場合は置き換え
                        for i, field in enumerate(update_fields):
                            if 'keywords' in field:
                                values[i] = enhanced_keywords
                                break
                
                if not update_fields:
                    return False
                
                # SQL構築
                sql = f"UPDATE news_table SET {', '.join(update_fields)} WHERE news_id = %s" if self.db_type == "postgresql" else f"UPDATE news_table SET {', '.join(update_fields)} WHERE news_id = ?"
                values.append(news_id)
                
                cursor.execute(sql, values)
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"分析結果更新エラー: {e}")
            return False
    
    def get_system_stats_summary(self, days: int = 30) -> Dict:
        """システム統計サマリー取得"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        SELECT 
                            COUNT(*) as total_runs,
                            SUM(total_collected) as total_news,
                            AVG(execution_time_seconds) as avg_execution_time,
                            SUM(api_calls_made) as total_api_calls,
                            SUM(errors_encountered) as total_errors
                        FROM system_stats 
                        WHERE collection_date >= NOW() - INTERVAL '%s days'
                    """
                    cursor.execute(sql, (days,))
                else:
                    sql = """
                        SELECT 
                            COUNT(*) as total_runs,
                            SUM(total_collected) as total_news,
                            AVG(execution_time_seconds) as avg_execution_time,
                            SUM(api_calls_made) as total_api_calls,
                            SUM(errors_encountered) as total_errors
                        FROM system_stats 
                        WHERE collection_date >= DATEADD(day, -?, GETDATE())
                    """
                    cursor.execute(sql, (days,))
                
                result = cursor.fetchone()
                return {
                    'total_runs': result[0] or 0,
                    'total_news': result[1] or 0,
                    'avg_execution_time': float(result[2] or 0),
                    'total_api_calls': result[3] or 0,
                    'total_errors': result[4] or 0
                }
                
        except Exception as e:
            self.logger.error(f"統計サマリー取得エラー: {e}")
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