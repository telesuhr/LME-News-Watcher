#!/usr/bin/env python3
"""
データベース自動検出テストスクリプト
"""

from database_detector import DatabaseDetector

def test_autodetect():
    """自動検出テスト"""
    print("=== データベース自動検出テスト ===\n")
    
    # 検出器初期化
    detector = DatabaseDetector()
    
    # 利用可能なデータベース確認
    print("1. 利用可能なデータベースを検出中...")
    available_dbs = detector.get_available_databases()
    
    print("\n検出結果:")
    for db_type, is_available in available_dbs.items():
        status = "✓ 利用可能" if is_available else "✗ 利用不可"
        print(f"  {db_type}: {status}")
    
    # 自動選択
    print("\n2. 最適なデータベースを自動選択中...")
    selected_db_type, selected_config = detector.detect_and_configure()
    
    print(f"\n選択されたデータベース: {selected_db_type}")
    print("\n設定内容:")
    for key, value in selected_config.items():
        if key != 'password' and value is not None:
            print(f"  {key}: {value}")
        elif key == 'password' and value:
            print(f"  {key}: ********")
    
    # 接続テスト
    print("\n3. 選択されたデータベースへの接続テスト...")
    if selected_db_type == 'postgresql':
        success = detector._test_postgresql(selected_config)
    else:
        success = detector._test_sqlserver(selected_config)
    
    if success:
        print("✓ 接続テスト成功！")
    else:
        print("✗ 接続テスト失敗")
    
    print("\n=== テスト完了 ===")
    
    return selected_db_type, selected_config

if __name__ == "__main__":
    test_autodetect()