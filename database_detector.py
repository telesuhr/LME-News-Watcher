#!/usr/bin/env python3
"""
データベース自動検出モジュール
PostgreSQLとSQL Serverを自動的に検出して接続
"""

import psycopg2
import pyodbc
import logging
import json
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class DatabaseDetector:
    """データベース自動検出クラス"""
    
    def __init__(self, config_path: str = "config_spec.json"):
        """初期化"""
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """設定ファイル読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return {}
    
    def detect_and_configure(self) -> Tuple[str, Dict]:
        """
        利用可能なデータベースを検出して設定を返す
        
        Returns:
            (db_type, db_config): データベースタイプと設定
        """
        logger.info("データベース自動検出開始...")
        
        # まずSQL ServerのJCLデータベースを試す（Windows環境用）
        sql_config = self._get_sqlserver_config()
        if self._test_sqlserver(sql_config):
            logger.info("SQL Server (JCL)が検出されました。SQL Serverを使用します。")
            return "sqlserver", sql_config
        
        # SQL Serverが使えない場合はPostgreSQLを試す
        pg_config = self._get_postgresql_config()
        if self._test_postgresql(pg_config):
            logger.info("PostgreSQLが検出されました。PostgreSQLを使用します。")
            return "postgresql", pg_config
        
        # どちらも使えない場合は設定ファイルの設定を使用
        db_config = self.config.get('database', {})
        db_type = db_config.get('database_type', 'postgresql')
        logger.warning(f"データベースが検出できませんでした。設定ファイルの設定を使用します: {db_type}")
        return db_type, db_config
    
    def _get_postgresql_config(self) -> Dict:
        """PostgreSQL用のデフォルト設定取得"""
        db_config = self.config.get('database', {})
        
        # PostgreSQL用の設定を生成
        return {
            'database_type': 'postgresql',
            'host': db_config.get('host', 'localhost'),
            'port': db_config.get('port', 5432),
            'database': db_config.get('database', 'lme_reporting'),
            'user': db_config.get('user', 'postgres'),
            'password': db_config.get('password', '')
        }
    
    def _get_sqlserver_config(self) -> Dict:
        """SQL Server用のデフォルト設定取得"""
        db_config = self.config.get('database', {})
        
        # SQL Server用の設定を生成
        config = {
            'database_type': 'sqlserver',
            'server': db_config.get('host', db_config.get('server', 'localhost')),
            'database': db_config.get('database', 'JCL'),
            'driver': db_config.get('driver', 'ODBC Driver 17 for SQL Server')
        }
        
        # Windows認証を優先的に試す
        if db_config.get('trusted_connection'):
            config['trusted_connection'] = True
        else:
            config['user'] = db_config.get('user', 'sa')
            config['password'] = db_config.get('password', '')
            config['trusted_connection'] = False
            
        return config
    
    def _test_postgresql(self, config: Dict) -> bool:
        """PostgreSQL接続テスト"""
        try:
            conn = psycopg2.connect(
                host=config.get('host'),
                port=config.get('port'),
                database=config.get('database'),
                user=config.get('user'),
                password=config.get('password')
            )
            
            # データベース存在確認
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            logger.info("PostgreSQL接続テスト成功")
            return True
            
        except Exception as e:
            logger.debug(f"PostgreSQL接続テスト失敗: {e}")
            return False
    
    def _test_sqlserver(self, config: Dict) -> bool:
        """SQL Server接続テスト"""
        try:
            # まずWindows認証を試す
            if config.get('trusted_connection'):
                conn_str = (
                    f"DRIVER={{{config.get('driver')}}};"
                    f"SERVER={config.get('server')};"
                    f"DATABASE={config.get('database')};"
                    f"Trusted_Connection=yes;"
                )
            else:
                conn_str = (
                    f"DRIVER={{{config.get('driver')}}};"
                    f"SERVER={config.get('server')};"
                    f"DATABASE={config.get('database')};"
                    f"UID={config.get('user')};"
                    f"PWD={config.get('password')};"
                )
            
            conn = pyodbc.connect(conn_str)
            
            # JCLデータベース存在確認
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sys.databases WHERE name = ?", config.get('database'))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                logger.info(f"SQL Server (JCL)接続成功: {config.get('server')}/{config.get('database')}")
                return True
            else:
                logger.warning(f"JCLデータベースが見つかりません: {config.get('server')}")
                return False
            
        except Exception as e:
            logger.debug(f"SQL Server接続テスト失敗: {e}")
            
            # Windows認証が失敗した場合、SQL Server認証を試す
            if config.get('trusted_connection') and config.get('user'):
                config['trusted_connection'] = False
                return self._test_sqlserver(config)
                
            return False
    
    def get_available_databases(self) -> Dict[str, bool]:
        """利用可能なデータベースの一覧を取得"""
        result = {
            'postgresql': False,
            'sqlserver': False
        }
        
        # PostgreSQLテスト
        pg_config = self._get_postgresql_config()
        result['postgresql'] = self._test_postgresql(pg_config)
        
        # SQL Serverテスト
        sql_config = self._get_sqlserver_config()
        result['sqlserver'] = self._test_sqlserver(sql_config)
        
        return result


def create_auto_detect_database_manager(config_path: str = "config_spec.json"):
    """
    自動検出機能付きデータベースマネージャーを作成
    
    Returns:
        SpecDatabaseManager: 設定済みのデータベースマネージャー
    """
    from database_spec import SpecDatabaseManager
    
    detector = DatabaseDetector(config_path)
    db_type, db_config = detector.detect_and_configure()
    
    # 検出結果をログ出力
    logger.info(f"使用データベース: {db_type}")
    
    # データベースマネージャーを作成
    return SpecDatabaseManager(db_config)