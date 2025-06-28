# Windows JCLデータベース設定ガイド

## 概要
このガイドでは、Windows PC上の既存SQL ServerのJCLデータベースを使用してLME News Watcherを設定する方法を説明します。

## 前提条件

### 1. SQL Server環境
- **SQL Server**: 既にインストール済み
- **JCLデータベース**: 既に存在する
- **認証方式**: Windows認証またはSQL Server認証

### 2. 必要なドライバー
```bash
# Microsoft ODBC Driver 17 for SQL Serverが必要
# 以下のURLからダウンロード・インストール:
# https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
```

## 設定手順

### 1. データベース設定の確認
`config_spec.json`の設定が正しく更新されていることを確認：

```json
{
  "database": {
    "database_type": "sqlserver",
    "host": "localhost",
    "port": 1433,
    "database": "JCL",
    "user": "",
    "password": "",
    "trusted_connection": true,
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

### 2. 接続設定オプション

#### オプション1: Windows認証（推奨）
```json
{
  "database": {
    "database_type": "sqlserver",
    "host": "localhost",
    "database": "JCL",
    "trusted_connection": true,
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

#### オプション2: SQL Server認証
```json
{
  "database": {
    "database_type": "sqlserver",
    "host": "localhost",
    "database": "JCL",
    "user": "your_username",
    "password": "your_password",
    "trusted_connection": false,
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

#### オプション3: 名前付きインスタンス
```json
{
  "database": {
    "database_type": "sqlserver",
    "host": "localhost\\SQLEXPRESS",
    "database": "JCL",
    "trusted_connection": true,
    "driver": "ODBC Driver 17 for SQL Server"
  }
}
```

### 3. テーブル作成
アプリケーション初回起動時に、JCLデータベース内に必要なテーブルが自動作成されます：

- `news_table`: ニュース記事の保存
- `system_stats`: システム統計情報
- `gemini_stats`: AI分析統計

### 4. 権限設定
JCLデータベースに対して以下の権限が必要です：

```sql
-- Windows認証ユーザーまたはSQL Serverユーザーに必要な権限
GRANT CREATE TABLE TO [your_user];
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO [your_user];
```

## 接続テスト

### 1. 手動テスト
```python
# test_jcl_connection.py
import pyodbc

try:
    conn_str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=JCL;"
        "Trusted_Connection=yes;"
    )
    
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE name = 'JCL'")
    result = cursor.fetchone()
    
    if result:
        print("✅ JCLデータベース接続成功")
    else:
        print("❌ JCLデータベースが見つかりません")
        
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 接続エラー: {e}")
```

### 2. アプリケーションテスト
```bash
# データベース自動検出テスト
python test_database_autodetect.py
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. 「JCLデータベースが見つかりません」
- JCLデータベースが存在することを確認
- SQL Server Management Studioで接続確認
- データベース名の大文字小文字を確認

#### 2. 「ODBC Driver not found」
- Microsoft ODBC Driver 17をインストール
- 32bit/64bit版の確認

#### 3. 「Login failed」
- Windows認証の場合：現在のユーザーにJCLデータベースへのアクセス権限があるか確認
- SQL Server認証の場合：ユーザー名とパスワードを確認

#### 4. 「Named pipe provider error」
- SQL Serverサービスが起動しているか確認
- TCP/IPプロトコルが有効になっているか確認
- ファイアウォール設定を確認

### SQL Server設定確認
```sql
-- SQL Serverでの確認クエリ
SELECT name FROM sys.databases WHERE name = 'JCL';
SELECT SUSER_NAME() as CurrentUser;
SELECT HAS_PERMS_BY_NAME('JCL', 'DATABASE', 'CONNECT') as CanConnect;
```

## 起動手順

1. **設定確認**: `config_spec.json`でJCL設定を確認
2. **アプリケーション起動**: `python app.py`
3. **自動検出**: SQL Server (JCL)が自動的に検出・選択される
4. **テーブル作成**: 初回起動時に必要なテーブルが作成される

## 注意事項

- **バックアップ**: 重要なJCLデータベースのバックアップを事前に取得
- **権限**: 最小限の権限でアクセス（読み取り専用テーブルには影響しません）
- **パフォーマンス**: 大量のニュースデータ収集時のパフォーマンス影響を監視

## サポート

問題が発生した場合：
1. ログファイル（`logs/`フォルダ）を確認
2. SQL Serverのエラーログを確認
3. 接続テストスクリプトを実行