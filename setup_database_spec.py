#!/usr/bin/env python3
"""
仕様書対応データベース初期化スクリプト
PostgreSQL/SQL Server/Azure SQL Database対応
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from database_spec import SpecDatabaseManager

def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'setup_database_spec_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_path: str = "config_spec.json"):
    """設定ファイル読み込み"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"設定ファイル読み込みエラー: {e}")

def test_database_connection(db_manager, logger):
    """データベース接続テスト"""
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
    return True

def create_database_tables(db_manager, logger):
    """データベーステーブル作成"""
    logger.info("データベーステーブル作成中...")
    
    if db_manager.create_tables():
        logger.info("データベーステーブル作成完了")
        return True
    else:
        logger.error("データベーステーブル作成失敗")
        return False

def verify_tables(db_manager, logger):
    """テーブル作成確認"""
    try:
        logger.info("テーブル作成確認中...")
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if db_manager.db_type == "postgresql":
                # PostgreSQLのテーブル確認
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('news_table', 'system_stats')
                """)
            else:
                # SQL Serverのテーブル確認
                cursor.execute("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE' 
                    AND TABLE_NAME IN ('news_table', 'system_stats')
                """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['news_table', 'system_stats']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                logger.warning(f"作成されていないテーブル: {missing_tables}")
                return False
            else:
                logger.info(f"作成確認済みテーブル: {tables}")
                return True
                
    except Exception as e:
        logger.error(f"テーブル確認エラー: {e}")
        return False

def insert_sample_data(db_manager, logger):
    """サンプルデータ挿入（オプション）"""
    try:
        logger.info("サンプルデータ挿入中...")
        
        from models_spec import NewsArticle
        
        sample_news = NewsArticle(
            title="LME News Watcher システム初期化完了",
            body="LME News Watcher システムが正常に初期化されました。Refinitiv EIKON APIからの自動ニュース取得と手動ニュース登録が利用可能です。",
            publish_time=datetime.now(),
            acquire_time=datetime.now(),
            source="System",
            related_metals="Copper, Aluminium",
            is_manual=True
        )
        
        success = db_manager.insert_news_article(sample_news)
        
        if success:
            logger.info("サンプルデータ挿入完了")
            return True
        else:
            logger.warning("サンプルデータ挿入失敗")
            return False
            
    except Exception as e:
        logger.warning(f"サンプルデータ挿入エラー: {e}")
        return False

def display_setup_summary(config, logger):
    """セットアップサマリー表示"""
    db_config = config["database"]
    
    print("\n" + "="*70)
    print("🎉 LME News Watcher データベース初期化完了!")
    print("="*70)
    print(f"データベースタイプ: {db_config['database_type'].upper()}")
    print(f"データベース名: {db_config['database']}")
    
    if db_config['database_type'] == 'postgresql':
        print(f"ホスト: {db_config['host']}")
        print(f"ポート: {db_config['port']}")
        print(f"ユーザー: {db_config['user']}")
    else:  # SQL Server / Azure SQL Database
        print(f"サーバー: {db_config['server']}")
        if db_config.get('trusted_connection'):
            print(f"認証方式: Windows認証")
        else:
            print(f"認証方式: SQL Server認証")
            print(f"ユーザー: {db_config['user']}")
        
        # Azure SQL Database検出
        if 'database.windows.net' in db_config.get('server', ''):
            print("🌐 Azure SQL Database環境を検出")
    
    print("\n📋 作成されたテーブル:")
    print("✅ news_table - ニュースデータ（Refinitiv + 手動登録）")
    print("✅ system_stats - システム統計・実行履歴")
    
    print("\n🚀 次のステップ:")
    print("1. config_spec.json でEIKON APIキーを設定")
    print("   - eikon_api_key: 'YOUR_ACTUAL_API_KEY'")
    print("2. ニュース収集テスト実行:")
    print("   python news_collector_spec.py")
    print("3. UIアプリケーション起動:")
    print("   python app.py")
    print("4. 実行可能ファイル作成（オプション）:")
    print("   python build_exe.py")
    
    print("\n⚙️ 仕様対応機能:")
    print("• Refinitiv EIKON APIからの自動ニュース取得")
    print("• ポーリング（5分間隔設定可能）")
    print("• LME非鉄金属関連フィルタリング")
    print("• 差分取得（重複除去）")
    print("• 手動ニュース登録機能")
    print("• 過去ニュース検索・閲覧")
    print("• Web技術ベースのUIツール")
    print("• PyInstaller対応（.exe作成）")
    print("• PostgreSQL/SQL Server/Azure SQL Database対応")
    
    print("\n📞 サポート:")
    print("• ログファイル: logs/")
    print("• 設定ファイル: config_spec.json")
    print("• システム管理者にお問い合わせください")
    print("="*70)

def main():
    """メイン処理"""
    logger = setup_logging()
    logger.info("LME News Watcher データベース初期化開始")
    
    try:
        # 設定読み込み
        config = load_config()
        
        # データベース設定を直接使用（検出機能をバイパス）
        print("\nデータベース接続設定確認中...")
        db_config = config["database"]
        db_type = db_config["database_type"]
        
        print(f"設定ファイルから読み込み:")
        print(f"  データベースタイプ: {db_type}")
        print(f"  サーバー: {db_config.get('server', 'N/A')}")
        print(f"  データベース: {db_config.get('database', 'N/A')}")
        
        print(f"\n使用するデータベース: {db_type}")
        
        logger.info(f"データベースタイプ: {db_config['database_type']}")
        if db_config['database_type'] == 'postgresql':
            logger.info(f"ホスト: {db_config.get('host', 'N/A')}")
            logger.info(f"ポート: {db_config.get('port', 'N/A')}")
        else:
            logger.info(f"サーバー: {db_config.get('server', 'N/A')}")
        logger.info(f"データベース: {db_config['database']}")
        
        # データベースマネージャー初期化（全体設定を渡す）
        try:
            db_manager = SpecDatabaseManager(config)
        except KeyError as e:
            logger.error(f"設定ファイルに必要なキーが不足しています: {e}")
            logger.error("config_spec.jsonの'database'セクションを確認してください")
            return False
        except Exception as e:
            logger.error(f"データベースマネージャー初期化エラー: {e}")
            return False
        
        # 接続テスト
        if not test_database_connection(db_manager, logger):
            return False
        
        # テーブル作成
        if not create_database_tables(db_manager, logger):
            return False
        
        # テーブル作成確認
        if not verify_tables(db_manager, logger):
            logger.warning("一部のテーブルが作成されていない可能性があります")
        
        # サンプルデータ挿入（オプション）
        insert_sample_data(db_manager, logger)
        
        # セットアップサマリー表示
        display_setup_summary(config, logger)
        
        logger.info("データベース初期化完了")
        return True
        
    except Exception as e:
        logger.error(f"初期化エラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)