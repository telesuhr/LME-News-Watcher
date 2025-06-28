#!/usr/bin/env python3
"""
JCLデータベース接続テスト
Windows SQL Server環境でのJCLデータベース接続を確認
"""

import pyodbc
import json
import sys
from pathlib import Path

def test_jcl_connection():
    """JCLデータベース接続テスト"""
    print("=== JCLデータベース接続テスト ===\n")
    
    # 設定ファイル読み込み
    try:
        with open('config_spec.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        db_config = config.get('database', {})
        print(f"設定ファイル読み込み成功")
        print(f"データベース: {db_config.get('database')}")
        print(f"サーバー: {db_config.get('host')}")
        print()
    except Exception as e:
        print(f"❌ 設定ファイル読み込みエラー: {e}")
        return False
    
    # 接続文字列構築
    try:
        if db_config.get('trusted_connection'):
            conn_str = (
                f"DRIVER={{{db_config.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
                f"SERVER={db_config.get('host', 'localhost')};"
                f"DATABASE={db_config.get('database', 'JCL')};"
                f"Trusted_Connection=yes;"
            )
            print("Windows認証で接続テスト中...")
        else:
            conn_str = (
                f"DRIVER={{{db_config.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
                f"SERVER={db_config.get('host', 'localhost')};"
                f"DATABASE={db_config.get('database', 'JCL')};"
                f"UID={db_config.get('user')};"
                f"PWD={db_config.get('password')};"
            )
            print("SQL Server認証で接続テスト中...")
        
        print(f"接続文字列: {conn_str.replace('PWD=.*;', 'PWD=***;')}")
        print()
        
    except Exception as e:
        print(f"❌ 接続文字列構築エラー: {e}")
        return False
    
    # データベース接続テスト
    try:
        print("データベース接続中...")
        conn = pyodbc.connect(conn_str)
        print("✅ データベース接続成功")
        
        # JCLデータベース存在確認
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.databases WHERE name = ?", db_config.get('database', 'JCL'))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ {db_config.get('database', 'JCL')}データベース確認成功")
        else:
            print(f"❌ {db_config.get('database', 'JCL')}データベースが見つかりません")
            cursor.close()
            conn.close()
            return False
        
        # 現在のユーザー確認
        cursor.execute("SELECT SUSER_NAME() as CurrentUser")
        user_result = cursor.fetchone()
        if user_result:
            print(f"接続ユーザー: {user_result[0]}")
        
        # 権限確認
        cursor.execute("SELECT HAS_PERMS_BY_NAME(?, 'DATABASE', 'CONNECT') as CanConnect", db_config.get('database', 'JCL'))
        perm_result = cursor.fetchone()
        if perm_result and perm_result[0]:
            print("✅ データベース接続権限あり")
        else:
            print("❌ データベース接続権限なし")
        
        # テーブル作成権限確認
        try:
            cursor.execute("SELECT HAS_PERMS_BY_NAME(?, 'DATABASE', 'CREATE TABLE') as CanCreateTable", db_config.get('database', 'JCL'))
            create_result = cursor.fetchone()
            if create_result and create_result[0]:
                print("✅ テーブル作成権限あり")
            else:
                print("⚠️  テーブル作成権限なし（初回セットアップ時に問題の可能性）")
        except:
            print("⚠️  権限確認でエラー（権限が限定的な可能性）")
        
        cursor.close()
        conn.close()
        
        print("\n=== 接続テスト完了 ===")
        print("✅ JCLデータベースへの接続が正常に確認されました")
        return True
        
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        
        # よくあるエラーの対処法を表示
        error_msg = str(e).lower()
        print("\n=== トラブルシューティング ===")
        
        if "driver" in error_msg:
            print("- Microsoft ODBC Driver 17 for SQL Serverがインストールされているか確認してください")
            print("- https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
        
        if "login failed" in error_msg:
            print("- Windows認証の場合：現在のユーザーにデータベースアクセス権限があるか確認")
            print("- SQL Server認証の場合：ユーザー名とパスワードを確認")
        
        if "server" in error_msg or "network" in error_msg:
            print("- SQL Serverサービスが起動しているか確認")
            print("- サーバー名が正しいか確認（名前付きインスタンスの場合は\\\\INSTANCE_NAME）")
            print("- ファイアウォール設定を確認")
        
        if "database" in error_msg:
            print("- JCLデータベースが存在するか確認")
            print("- データベース名の大文字小文字を確認")
        
        return False

def main():
    """メイン実行"""
    success = test_jcl_connection()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()