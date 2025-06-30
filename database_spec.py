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
        
        # データベース設定の取得（全体設定またはdatabase部分）
        if "database" in config:
            # 全体設定が渡された場合
            db_config = config["database"]
            news_config = config.get("news_collection", {})
        else:
            # database部分のみが渡された場合
            db_config = config
            news_config = {}
        
        self.db_type = db_config.get("database_type", "postgresql").lower()
        self.logger = logging.getLogger(__name__)
        
        # URLフィルタリング設定（news_collection設定から取得）
        self.filter_url_only = news_config.get("filter_url_only_news", True)
        self.min_body_length = news_config.get("min_body_length", 50)
        
        # 接続パラメータ設定
        if self.db_type == "postgresql":
            self.connection_params = {
                'host': db_config.get('host', 'localhost'),
                'port': db_config.get('port', 5432),
                'database': db_config.get('database', 'lme_reporting'),
                'user': db_config.get('user', 'postgres'),
                'password': db_config.get('password', '')
            }
        elif self.db_type == "sqlserver":
            self.connection_params = {
                'server': db_config.get('server', 'localhost'),
                'database': db_config.get('database', 'lme_reporting'),
                'user': db_config.get('user'),
                'password': db_config.get('password'),
                'driver': db_config.get('driver', 'ODBC Driver 17 for SQL Server')
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
                
                # デバッグログ：挿入前の記事情報をログ出力
                self.logger.info(f"ニュース記事挿入開始: news_id={article.news_id}, title='{article.title[:50]}...', is_manual={article.is_manual}")
                
                if self.db_type == "postgresql":
                    sql = """
                        INSERT INTO news_table (
                            news_id, title, body, publish_time, acquire_time, 
                            source, url, sentiment, summary, keywords, 
                            related_metals, is_manual, rating
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        ) ON CONFLICT (news_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            body = EXCLUDED.body,
                            source = EXCLUDED.source,
                            url = EXCLUDED.url,
                            related_metals = EXCLUDED.related_metals,
                            rating = EXCLUDED.rating
                    """
                elif self.db_type == "sqlserver":
                    sql = """
                        MERGE news_table AS target
                        USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) AS source 
                               (news_id, title, body, publish_time, acquire_time, 
                                source, url, sentiment, summary, keywords, 
                                related_metals, is_manual, rating)
                        ON target.news_id = source.news_id
                        WHEN MATCHED THEN
                            UPDATE SET title = source.title,
                                      body = source.body,
                                      source = source.source,
                                      url = source.url,
                                      related_metals = source.related_metals,
                                      rating = source.rating
                        WHEN NOT MATCHED THEN
                            INSERT (news_id, title, body, publish_time, acquire_time,
                                   source, url, sentiment, summary, keywords,
                                   related_metals, is_manual, rating)
                            VALUES (source.news_id, source.title, source.body, 
                                   source.publish_time, source.acquire_time, source.source,
                                   source.url, source.sentiment, source.summary, 
                                   source.keywords, source.related_metals, source.is_manual, source.rating);
                    """
                
                # SQL ServerのBIT型対応
                if self.db_type == "sqlserver":
                    is_manual_value = 1 if article.is_manual else 0
                else:
                    is_manual_value = article.is_manual
                
                # デバッグログ：実行予定のパラメータを出力
                params = (
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
                    is_manual_value,
                    article.rating
                )
                self.logger.debug(f"実行SQL: {sql}")
                self.logger.debug(f"パラメータ: news_id={params[0]}, title='{params[1][:30]}...', source='{params[5]}', is_manual={params[11]}")
                
                cursor.execute(sql, params)
                
                # SQL Serverでの影響行数確認
                if self.db_type == "sqlserver":
                    affected_rows = cursor.rowcount
                    self.logger.info(f"SQL Server MERGE実行完了: 影響行数={affected_rows}")
                else:
                    self.logger.info(f"PostgreSQL INSERT実行完了")
                
                # 挿入後の確認：実際にデータが保存されたかチェック
                self._verify_insertion(cursor, article.news_id)
                
                return True
                
        except Exception as e:
            self.logger.error(f"ニュース記事挿入エラー: {e}")
            self.logger.error(f"挿入失敗記事: news_id={article.news_id}, title='{article.title[:50]}...'")
            return False
    
    def _verify_insertion(self, cursor, news_id: str):
        """挿入確認のためのヘルパーメソッド"""
        try:
            if self.db_type == "postgresql":
                verify_sql = "SELECT news_id, title, is_manual FROM news_table WHERE news_id = %s"
            else:
                verify_sql = "SELECT news_id, title, is_manual FROM news_table WHERE news_id = ?"
            
            cursor.execute(verify_sql, (news_id,))
            result = cursor.fetchone()
            
            if result:
                self.logger.info(f"挿入確認成功: news_id={result[0]}, title='{result[1][:30]}...', is_manual={result[2]}")
            else:
                self.logger.warning(f"挿入確認失敗: news_id={news_id} がデータベースで見つからない")
                
        except Exception as e:
            self.logger.error(f"挿入確認エラー: {e}")
    
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
                
                # ORDER BY句生成
                order_clause = search_filter.to_sql_order_clause(self.db_type)
                
                # 本文がURLのみのものを除外する条件を追加（設定で有効な場合、手動登録は除外対象外）
                if self.filter_url_only:
                    url_only_filter = self._get_url_only_filter()
                    if where_clause == "1=1":
                        where_clause = url_only_filter
                    else:
                        where_clause = f"({where_clause}) AND {url_only_filter}"
                
                if self.db_type == "postgresql":
                    # PostgreSQL: DISTINCT ON を使用して重複を除去、カスタムソート適用
                    sql = f"""
                        SELECT * FROM (
                            SELECT DISTINCT ON (title, source) * FROM news_table 
                            WHERE {where_clause}
                            ORDER BY title, source, publish_time DESC
                        ) deduplicated
                        {order_clause}
                        LIMIT %s OFFSET %s
                    """
                    params.extend([search_filter.limit, search_filter.offset])
                else:
                    # SQL Server: ROW_NUMBER()を使用して重複除去、カスタムソート適用
                    sql = f"""
                        SELECT * FROM (
                            SELECT *, ROW_NUMBER() OVER (PARTITION BY title, source ORDER BY publish_time DESC) as rn
                            FROM news_table 
                            WHERE {where_clause}
                        ) ranked
                        WHERE rn = 1
                        {order_clause}
                        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                    """
                    params.extend([search_filter.offset, search_filter.limit])
                
                self.logger.debug(f"実行SQL: {sql}")
                self.logger.debug(f"SQLパラメータ: {params}")
                cursor.execute(sql, params)
                
                if self.db_type == "postgresql":
                    results = [dict(row) for row in cursor.fetchall()]
                else:
                    columns = [column[0] for column in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # 追加のクライアントサイドフィルタリング（念のため）
                if self.filter_url_only:
                    return self._filter_url_only_news(results)
                else:
                    return results
                
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
        """ソース一覧取得（手動登録を最上位に表示）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                sql = "SELECT DISTINCT source FROM news_table ORDER BY source"
                cursor.execute(sql)
                sources = [row[0] for row in cursor.fetchall()]
                
                # 手動登録を最上位に移動
                if '手動登録' in sources:
                    sources.remove('手動登録')
                    sources.insert(0, '手動登録')
                
                return sources
                
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
                
                # 削除前に対象ニュースの存在確認
                self.logger.info(f"ニュース削除要求: news_id={news_id}")
                
                # まず対象ニュースが存在するか確認
                if self.db_type == "postgresql":
                    check_sql = "SELECT news_id, title, is_manual FROM news_table WHERE news_id = %s"
                else:
                    check_sql = "SELECT news_id, title, is_manual FROM news_table WHERE news_id = ?"
                
                cursor.execute(check_sql, (news_id,))
                existing_news = cursor.fetchone()
                
                if not existing_news:
                    self.logger.warning(f"削除対象ニュースが見つからない: {news_id}")
                    return False
                
                self.logger.info(f"削除対象ニュース確認: news_id={existing_news[0]}, title='{existing_news[1][:30]}...', is_manual={existing_news[2]}")
                
                # 手動登録でない場合は削除拒否
                if not existing_news[2]:
                    self.logger.warning(f"手動登録ニュースではないため削除拒否: {news_id}")
                    return False
                
                # 削除実行
                if self.db_type == "postgresql":
                    sql = "DELETE FROM news_table WHERE news_id = %s AND is_manual = TRUE"
                else:
                    sql = "DELETE FROM news_table WHERE news_id = ? AND is_manual = 1"
                
                cursor.execute(sql, (news_id,))
                affected_rows = cursor.rowcount
                
                if affected_rows > 0:
                    self.logger.info(f"ニュース削除成功: {news_id} (影響行数: {affected_rows})")
                    return True
                else:
                    self.logger.warning(f"削除処理失敗: {news_id} (影響行数: {affected_rows})")
                    return False
                
        except Exception as e:
            self.logger.error(f"ニュース削除エラー: {e}")
            self.logger.error(f"削除失敗news_id: {news_id}")
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
    
    def update_news_rating(self, news_id: str, rating: Optional[int]) -> bool:
        """ニュースレーティング更新"""
        try:
            # レーティング値の検証（Noneの場合はクリア）
            if rating is not None and (rating < 1 or rating > 3):
                self.logger.error(f"無効なレーティング値: {rating}")
                return False
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = "UPDATE news_table SET rating = %s WHERE news_id = %s"
                else:
                    sql = "UPDATE news_table SET rating = ? WHERE news_id = ?"
                
                cursor.execute(sql, (rating, news_id))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"レーティング更新エラー: {e}")
            return False
    
    def mark_news_as_read(self, news_id: str) -> bool:
        """ニュースを既読にマーク"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = "UPDATE news_table SET is_read = TRUE, read_at = CURRENT_TIMESTAMP WHERE news_id = %s"
                else:
                    sql = "UPDATE news_table SET is_read = 1, read_at = GETDATE() WHERE news_id = ?"
                
                cursor.execute(sql, (news_id,))
                
                if cursor.rowcount > 0:
                    self.logger.debug(f"ニュースを既読にマーク: {news_id}")
                    return True
                else:
                    self.logger.warning(f"既読マーク失敗（ニュース未発見）: {news_id}")
                    return False
                
        except Exception as e:
            self.logger.error(f"既読マークエラー: {e}")
            return False
    
    def mark_news_as_unread(self, news_id: str) -> bool:
        """ニュースを未読にマーク"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = "UPDATE news_table SET is_read = FALSE, read_at = NULL WHERE news_id = %s"
                else:
                    sql = "UPDATE news_table SET is_read = 0, read_at = NULL WHERE news_id = ?"
                
                cursor.execute(sql, (news_id,))
                
                if cursor.rowcount > 0:
                    self.logger.debug(f"ニュースを未読にマーク: {news_id}")
                    return True
                else:
                    self.logger.warning(f"未読マーク失敗（ニュース未発見）: {news_id}")
                    return False
                
        except Exception as e:
            self.logger.error(f"未読マークエラー: {e}")
            return False
    
    def mark_all_as_read(self, filter_conditions: Optional[Dict] = None) -> int:
        """全ニュースを既読にマーク（条件付き可能）"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                base_sql = "UPDATE news_table SET is_read = {}, read_at = {}"
                if self.db_type == "postgresql":
                    sql = base_sql.format("TRUE", "CURRENT_TIMESTAMP")
                    where_clause = "WHERE is_read = FALSE"
                else:
                    sql = base_sql.format("1", "GETDATE()")
                    where_clause = "WHERE is_read = 0"
                
                # 条件があれば追加
                params = []
                if filter_conditions:
                    if filter_conditions.get('source'):
                        if self.db_type == "postgresql":
                            where_clause += " AND source ILIKE %s"
                            params.append(f"%{filter_conditions['source']}%")
                        else:
                            where_clause += " AND source LIKE ?"
                            params.append(f"%{filter_conditions['source']}%")
                
                sql += " " + where_clause
                cursor.execute(sql, params)
                
                affected_rows = cursor.rowcount
                self.logger.info(f"一括既読マーク完了: {affected_rows} 件")
                return affected_rows
                
        except Exception as e:
            self.logger.error(f"一括既読マークエラー: {e}")
            return 0
    
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

    def find_duplicate_news(self) -> List[Dict]:
        """
        タイトルとソースが同じ重複ニュースを検出
        
        Returns:
            List[Dict]: 重複ニュースのリスト
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if self.db_type == "postgresql":
                    sql = """
                        SELECT title, source, COUNT(*) as duplicate_count,
                               ARRAY_AGG(news_id ORDER BY publish_time DESC) as news_ids
                        FROM news_table 
                        GROUP BY title, source 
                        HAVING COUNT(*) > 1
                        ORDER BY duplicate_count DESC
                    """
                else:
                    sql = """
                        SELECT title, source, COUNT(*) as duplicate_count,
                               STRING_AGG(news_id, ',') as news_ids
                        FROM news_table 
                        GROUP BY title, source 
                        HAVING COUNT(*) > 1
                        ORDER BY duplicate_count DESC
                    """
                
                cursor.execute(sql)
                
                if self.db_type == "postgresql":
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    columns = [column[0] for column in cursor.description]
                    results = []
                    for row in cursor.fetchall():
                        row_dict = dict(zip(columns, row))
                        # SQL Serverの場合、カンマ区切りを配列に変換
                        if 'news_ids' in row_dict and row_dict['news_ids']:
                            row_dict['news_ids'] = row_dict['news_ids'].split(',')
                        results.append(row_dict)
                    return results
                    
        except Exception as e:
            self.logger.error(f"重複ニュース検出エラー: {e}")
            return []

    def remove_duplicate_news(self, keep_latest: bool = True) -> int:
        """
        重複ニュースを削除（最新または最古を保持）
        
        Args:
            keep_latest: True=最新を保持、False=最古を保持
            
        Returns:
            int: 削除された件数
        """
        try:
            duplicates = self.find_duplicate_news()
            deleted_count = 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for duplicate in duplicates:
                    title = duplicate['title']
                    source = duplicate['source']
                    news_ids = duplicate['news_ids']
                    
                    if len(news_ids) <= 1:
                        continue
                    
                    # 保持するニュースID（最新または最古）
                    if self.db_type == "postgresql":
                        if keep_latest:
                            keep_sql = """
                                SELECT news_id FROM news_table 
                                WHERE title = %s AND source = %s 
                                ORDER BY publish_time DESC LIMIT 1
                            """
                        else:
                            keep_sql = """
                                SELECT news_id FROM news_table 
                                WHERE title = %s AND source = %s 
                                ORDER BY publish_time ASC LIMIT 1
                            """
                        cursor.execute(keep_sql, (title, source))
                        keep_id = cursor.fetchone()[0]
                        
                        # 他を削除
                        delete_sql = """
                            DELETE FROM news_table 
                            WHERE title = %s AND source = %s AND news_id != %s
                        """
                        cursor.execute(delete_sql, (title, source, keep_id))
                        
                    else:
                        if keep_latest:
                            keep_sql = """
                                SELECT TOP 1 news_id FROM news_table 
                                WHERE title = ? AND source = ? 
                                ORDER BY publish_time DESC
                            """
                        else:
                            keep_sql = """
                                SELECT TOP 1 news_id FROM news_table 
                                WHERE title = ? AND source = ? 
                                ORDER BY publish_time ASC
                            """
                        cursor.execute(keep_sql, (title, source))
                        keep_id = cursor.fetchone()[0]
                        
                        # 他を削除
                        delete_sql = """
                            DELETE FROM news_table 
                            WHERE title = ? AND source = ? AND news_id != ?
                        """
                        cursor.execute(delete_sql, (title, source, keep_id))
                    
                    deleted_count += cursor.rowcount - 1 if cursor.rowcount > 0 else 0
                
                conn.commit()
                self.logger.info(f"重複ニュース削除完了: {deleted_count}件")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"重複ニュース削除エラー: {e}")
            return 0

    def get_duplicate_stats(self) -> Dict:
        """
        重複ニュースの統計情報を取得
        
        Returns:
            Dict: 重複統計情報
        """
        try:
            duplicates = self.find_duplicate_news()
            total_duplicates = len(duplicates)
            total_duplicate_items = sum(d['duplicate_count'] for d in duplicates)
            redundant_items = total_duplicate_items - total_duplicates  # 削除可能な件数
            
            return {
                'duplicate_groups': total_duplicates,
                'total_duplicate_items': total_duplicate_items,
                'redundant_items': redundant_items,
                'space_savings_percent': round((redundant_items / total_duplicate_items * 100), 2) if total_duplicate_items > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"重複統計取得エラー: {e}")
            return {}

    def _get_url_only_filter(self) -> str:
        """本文がURLのみの記事を除外するフィルター条件を生成（手動登録は除外対象外）"""
        if self.db_type == "postgresql":
            return f"""(
                is_manual = TRUE OR 
                (LENGTH(body) > {self.min_body_length} AND 
                 NOT (body ~ '^\\s*https?://[^\\s]+\\s*$'))
            )"""
        else:  # SQL Server - NVARCHAR(MAX)でLEN()は使えないためDATALENGTH()使用
            return f"""(
                is_manual = 1 OR 
                (DATALENGTH(body) > {self.min_body_length * 2} AND 
                 body NOT LIKE 'http://%' AND 
                 body NOT LIKE 'https://%')
            )"""
    
    def _filter_url_only_news(self, news_list: List[Dict]) -> List[Dict]:
        """クライアントサイドでURL のみの本文を除外（手動登録は除外対象外）"""
        filtered_news = []
        
        for news in news_list:
            # 手動登録ニュースは常に表示
            if news.get('is_manual'):
                filtered_news.append(news)
                continue
                
            body = news.get('body', '').strip()
            
            # 本文が空または短すぎる場合は除外
            if not body or len(body) <= self.min_body_length:
                continue
            
            # 本文がURLのみかチェック
            if self._is_url_only_body(body):
                continue
            
            filtered_news.append(news)
        
        return filtered_news
    
    def _is_url_only_body(self, body: str) -> bool:
        """本文がURLのみかどうかを判定"""
        import re
        
        body = body.strip()
        
        # 単一のURLパターンをチェック
        url_pattern = r'^https?://[^\s]+$'
        if re.match(url_pattern, body):
            return True
        
        # 複数のURLのみの場合もチェック
        urls = re.findall(r'https?://[^\s]+', body)
        non_url_text = re.sub(r'https?://[^\s]+', '', body).strip()
        
        # URLが存在し、URL以外のテキストが非常に少ない場合
        if urls and len(non_url_text) < 20:
            return True
        
        return False