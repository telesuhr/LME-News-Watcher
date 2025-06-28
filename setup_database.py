#!/usr/bin/env python3
"""
データベース初期化スクリプト
PostgreSQL/SQL Server両対応
"""

import json
import logging
import sys
from pathlib import Path

from database import DatabaseManager

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('setup_database.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_path: str = "config.json"):
    """設定ファイル読み込み"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"設定ファイル読み込みエラー: {e}")

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("データベース初期化開始")
    
    try:
        # 設定読み込み
        config = load_config()
        db_config = config["database"]
        
        logger.info(f"データベースタイプ: {db_config['database_type']}")
        logger.info(f"ホスト: {db_config['host']}")
        logger.info(f"データベース: {db_config['database']}")
        
        # データベースマネージャー初期化
        db_manager = DatabaseManager(db_config)
        
        # 接続テスト
        logger.info("データベース接続テスト中...")
        if not db_manager.test_connection():
            logger.error("データベース接続失敗")
            logger.error("以下を確認してください:")
            logger.error("1. データベースサーバーが起動している")
            logger.error("2. 接続情報（ホスト、ポート、ユーザー名、パスワード）が正しい")
            logger.error("3. データベースが存在する")
            logger.error("4. ユーザーに適切な権限がある")
            return False
        
        logger.info("データベース接続成功")
        
        # テーブル作成
        logger.info("テーブル作成中...")
        if db_manager.create_tables():
            logger.info("データベース初期化完了")
            
            # 初期化完了メッセージ
            print("\n" + "="*60)
            print("🎉 NewsCollector データベース初期化完了!")
            print("="*60)
            print(f"データベースタイプ: {db_config['database_type'].upper()}")
            print(f"データベース名: {db_config['database']}")
            print(f"ホスト: {db_config['host']}")
            print("\n作成されたテーブル:")
            print("✅ news_items - ニュースデータ")
            print("✅ collection_stats - 収集統計")
            print("\n次のステップ:")
            print("1. config.json でEIKON APIキーを設定")
            print("2. python collect_news.py でニュース収集実行")
            print("="*60)
            
            return True
        else:
            logger.error("テーブル作成失敗")
            return False
            
    except Exception as e:
        logger.error(f"初期化エラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)