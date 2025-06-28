#!/usr/bin/env python3
"""
SQL Server接続テストスクリプト
Windows環境でSQL Server接続を確認
"""

import json
import pyodbc
import sys

def test_connection():
    """SQL Server接続テスト"""
    
    print("=== SQL Server 接続テスト ===\n")
    
    # 設定ファイル読み込み
    try:
        with open('config_spec.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        db_config = config['database']
        print(f"✓ 設定ファイル読み込み成功")
        print(f"  データベースタイプ: {db_config.get('database_type')}")
        print(f"  サーバー: {db_config.get('server')}")
        print(f"  データベース: {db_config.get('database')}")
        print()
    except Exception as e:
        print(f"✗ 設定ファイル読み込みエラー: {e}")
        return False
    
    # 利用可能なODBCドライバー確認
    print("利用可能なODBCドライバー:")
    drivers = pyodbc.drivers()
    for driver in drivers:
        print(f"  - {driver}")
    print()
    
    # 接続テスト
    try:
        if db_config.get('trusted_connection'):
            # Windows認証
            conn_str = (
                f"DRIVER={{{db_config.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
                f"SERVER={db_config.get('server')};"
                f"DATABASE={db_config.get('database')};"
                f"Trusted_Connection=yes;"
            )
            print("Windows認証で接続を試みています...")
        else:
            # SQL Server認証
            conn_str = (
                f"DRIVER={{{db_config.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
                f"SERVER={db_config.get('server')};"
                f"DATABASE={db_config.get('database')};"
                f"UID={db_config.get('user')};"
                f"PWD={db_config.get('password')};"
            )
            print("SQL Server認証で接続を試みています...")
        
        # 接続
        connection = pyodbc.connect(conn_str)
        cursor = connection.cursor()
        
        # バージョン確認
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"\n✓ 接続成功!")
        print(f"SQL Serverバージョン:\n{version.split('\\n')[0]}")
        
        # データベース確認
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"\n現在のデータベース: {db_name}")
        
        # テーブル存在確認
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'news_table'
        """)
        table_exists = cursor.fetchone()[0] > 0
        
        if table_exists:
            print("\n✓ news_tableテーブルが存在します")
            
            # レコード数確認
            cursor.execute("SELECT COUNT(*) FROM news_table")
            count = cursor.fetchone()[0]
            print(f"  現在のニュース件数: {count}")
        else:
            print("\n✗ news_tableテーブルがまだ作成されていません")
            print("  → setup_database_spec.py を実行してテーブルを作成してください")
        
        connection.close()
        return True
        
    except pyodbc.Error as e:
        print(f"\n✗ SQL Server接続エラー: {e}")
        print("\n考えられる原因:")
        print("1. SQL Serverサービスが起動していない")
        print("2. サーバー名またはインスタンス名が間違っている")
        print("3. 認証情報（ユーザー名/パスワード）が間違っている")
        print("4. ファイアウォールでブロックされている")
        print("5. SQL Server認証が無効になっている（SQL Server認証使用時）")
        return False
    except Exception as e:
        print(f"\n✗ 予期しないエラー: {e}")
        return False

if __name__ == "__main__":
    print("SQL Server接続テストを開始します...\n")
    
    # pyodbcインストール確認
    try:
        import pyodbc
        print("✓ pyodbcモジュールが正しくインストールされています")
    except ImportError:
        print("✗ pyodbcがインストールされていません")
        print("  以下のコマンドでインストールしてください:")
        print("  pip install pyodbc")
        sys.exit(1)
    
    # 接続テスト実行
    success = test_connection()
    
    if success:
        print("\n=== テスト完了: 成功 ===")
        print("SQL Serverへの接続が正常に確立できました。")
        print("アプリケーションを起動できます: python app.py")
    else:
        print("\n=== テスト完了: 失敗 ===")
        print("上記のエラーを解決してから再度実行してください。")
        sys.exit(1)