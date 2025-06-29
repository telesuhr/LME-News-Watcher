#!/usr/bin/env python3
"""
既読ステータス用カラム追加マイグレーションスクリプト
"""

import json
import logging
from database_spec import SpecDatabaseManager

def main():
    """既読カラムを追加"""
    
    print("既読ステータス用カラム追加スクリプト開始")
    
    try:
        # 設定読み込み
        with open('config_spec.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # データベース接続
        db_manager = SpecDatabaseManager(config)
        
        # カラム存在確認
        print("既存カラムをチェック中...")
        
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if db_manager.db_type == "postgresql":
                # PostgreSQLでカラム存在確認
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'news_table' 
                    AND column_name IN ('is_read', 'read_at')
                """)
                existing_columns = [row[0] for row in cursor.fetchall()]
                
                # カラム追加
                if 'is_read' not in existing_columns:
                    print("is_readカラムを追加中...")
                    cursor.execute("ALTER TABLE news_table ADD COLUMN is_read BOOLEAN DEFAULT FALSE")
                    print("✓ is_readカラム追加完了")
                else:
                    print("- is_readカラムは既に存在します")
                
                if 'read_at' not in existing_columns:
                    print("read_atカラムを追加中...")
                    cursor.execute("ALTER TABLE news_table ADD COLUMN read_at TIMESTAMP DEFAULT NULL")
                    print("✓ read_atカラム追加完了")
                else:
                    print("- read_atカラムは既に存在します")
                    
            else:
                # SQL Serverでカラム存在確認
                cursor.execute("""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = 'news_table' 
                    AND COLUMN_NAME IN ('is_read', 'read_at')
                """)
                existing_columns = [row[0] for row in cursor.fetchall()]
                
                # カラム追加
                if 'is_read' not in existing_columns:
                    print("is_readカラムを追加中...")
                    cursor.execute("ALTER TABLE news_table ADD is_read BIT DEFAULT 0")
                    print("✓ is_readカラム追加完了")
                else:
                    print("- is_readカラムは既に存在します")
                
                if 'read_at' not in existing_columns:
                    print("read_atカラムを追加中...")
                    cursor.execute("ALTER TABLE news_table ADD read_at DATETIME DEFAULT NULL")
                    print("✓ read_atカラム追加完了")
                else:
                    print("- read_atカラムは既に存在します")
        
        # 確認クエリ
        print("\n確認クエリ実行中...")
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if db_manager.db_type == "postgresql":
                cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN is_read = TRUE THEN 1 END) as read_count FROM news_table")
            else:
                cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN is_read = 1 THEN 1 END) as read_count FROM news_table")
            
            result = cursor.fetchone()
            total_count = result[0]
            read_count = result[1]
            unread_count = total_count - read_count
            
            print(f"✓ データベース確認完了:")
            print(f"  - 総ニュース数: {total_count}")
            print(f"  - 既読: {read_count}")
            print(f"  - 未読: {unread_count}")
        
        print("\n既読ステータス用カラム追加完了！")
        
    except Exception as e:
        print(f"エラー: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("マイグレーション成功")
    else:
        print("マイグレーション失敗")