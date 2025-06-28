#!/usr/bin/env python3
"""
PostgreSQLからSQL Serverへのデータ移行スクリプト
"""

import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from database import DatabaseManager

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_path: str = "../config.json"):
    """設定ファイル読み込み"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

def create_sqlserver_config(base_config: Dict[str, Any]) -> Dict[str, Any]:
    """SQL Server用設定作成"""
    sqlserver_config = base_config["database"].copy()
    sqlserver_config["database_type"] = "sqlserver"
    
    # SQL Server接続情報を設定（ユーザー入力）
    print("SQL Server接続情報を入力してください:")
    sqlserver_config["server"] = input("サーバー名 (例: localhost): ").strip() or "localhost"
    sqlserver_config["database"] = input("データベース名: ").strip()
    sqlserver_config["user"] = input("ユーザー名: ").strip()
    sqlserver_config["password"] = input("パスワード: ").strip()
    
    return sqlserver_config

def migrate_data(source_db: DatabaseManager, target_db: DatabaseManager, logger: logging.Logger) -> bool:
    """データ移行実行"""
    try:
        # ニュースデータ移行
        logger.info("ニュースデータ移行開始...")
        
        # PostgreSQLからデータ取得
        news_data = source_db.get_recent_news(days=365, limit=10000)  # 1年分
        logger.info(f"移行対象ニュース: {len(news_data)} 件")
        
        # SQL Serverに挿入
        migrated_count = 0
        for news in news_data:
            # データ変換
            from models import NewsItem
            import json
            
            news_item = NewsItem(
                story_id=news['story_id'],
                headline=news['headline'],
                source=news['source'],
                published_date=news['published_date'],
                body=news.get('body'),
                priority_score=news['priority_score'],
                metal_category=news.get('metal_category'),
                keywords=json.loads(news.get('keywords', '[]')) if news.get('keywords') else None,
                query_type=news.get('query_type'),
                created_at=news.get('created_at'),
                updated_at=news.get('updated_at')
            )
            
            if target_db.insert_news_item(news_item):
                migrated_count += 1
        
        logger.info(f"ニュースデータ移行完了: {migrated_count}/{len(news_data)} 件")
        
        # 統計データ移行
        logger.info("統計データ移行開始...")
        stats_data = source_db.get_stats_summary(days=365)
        logger.info(f"統計データ移行完了")
        
        return True
        
    except Exception as e:
        logger.error(f"データ移行エラー: {e}")
        return False

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("PostgreSQL → SQL Server データ移行開始")
    
    try:
        # 設定読み込み
        config = load_config()
        
        # PostgreSQL接続設定
        pg_config = config["database"]
        pg_config["database_type"] = "postgresql"
        
        # SQL Server接続設定作成
        sqlserver_config = create_sqlserver_config(config)
        
        # データベースマネージャー初期化
        logger.info("PostgreSQL接続確認...")
        source_db = DatabaseManager(pg_config)
        if not source_db.test_connection():
            logger.error("PostgreSQL接続失敗")
            return False
        
        logger.info("SQL Server接続確認...")
        target_db = DatabaseManager(sqlserver_config)
        if not target_db.test_connection():
            logger.error("SQL Server接続失敗")
            return False
        
        # SQL Serverにテーブル作成
        logger.info("SQL Serverテーブル作成...")
        if not target_db.create_tables():
            logger.error("SQL Serverテーブル作成失敗")
            return False
        
        # データ移行実行
        if migrate_data(source_db, target_db, logger):
            logger.info("データ移行完了!")
            
            print("\n" + "="*60)
            print("🎉 SQL Server移行完了!")
            print("="*60)
            print("移行先:")
            print(f"サーバー: {sqlserver_config['server']}")
            print(f"データベース: {sqlserver_config['database']}")
            print("\n次のステップ:")
            print("1. config.json のdatabase_typeを'sqlserver'に変更")
            print("2. SQL Server接続情報を設定")
            print("3. 動作確認")
            print("="*60)
            
            return True
        else:
            logger.error("データ移行失敗")
            return False
            
    except Exception as e:
        logger.error(f"移行処理エラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)