# Windows + SQL Server セットアップガイド

## 前提条件

1. **Windows 10/11 (64bit)**
2. **SQL Server** (Express版でもOK)
   - SQL Server 2019以降推奨
3. **Python 3.8以降**
   - [Python公式サイト](https://www.python.org/downloads/)からダウンロード
4. **Refinitiv EIKON Desktop**
   - インストール済みでログイン可能な状態

## セットアップ手順

### 1. SQL Serverの準備

#### SQL Server Management Studio (SSMS) で以下を実行：

```sql
-- データベース作成
CREATE DATABASE lme_reporting;
GO

-- ユーザー作成（SQL Server認証使用の場合）
CREATE LOGIN lme_user WITH PASSWORD = 'YourSecurePassword123!';
GO

USE lme_reporting;
GO

CREATE USER lme_user FOR LOGIN lme_user;
GO

-- 権限付与
ALTER ROLE db_owner ADD MEMBER lme_user;
GO
```

### 2. プロジェクトのダウンロード

```cmd
# GitHubからクローン（Gitがインストール済みの場合）
git clone https://github.com/telesuhr/LME-News-Watcher.git
cd LME-News-Watcher\NewsCollector

# またはZIPファイルをダウンロードして解凍
```

### 3. Python環境のセットアップ

```cmd
# 仮想環境作成（推奨）
python -m venv venv

# 仮想環境有効化
venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### 4. 設定ファイルの編集

`config_spec.json` を編集して、実際の環境に合わせて設定：

#### パターン1: SQL Server認証
```json
{
  "database": {
    "database_type": "sqlserver",
    "server": "localhost",
    "database": "lme_reporting",
    "user": "lme_user",
    "password": "YourSecurePassword123!",
    "driver": "ODBC Driver 17 for SQL Server",
    "trusted_connection": false
  }
}
```

#### パターン2: Windows認証（推奨）
```json
{
  "database": {
    "database_type": "sqlserver",
    "server": "localhost",
    "database": "lme_reporting",
    "driver": "ODBC Driver 17 for SQL Server",
    "trusted_connection": true
  }
}
```

#### パターン3: SQL Server Express
```json
{
  "database": {
    "database_type": "sqlserver",
    "server": "localhost\\SQLEXPRESS",
    "database": "lme_reporting",
    "user": "sa",
    "password": "YourPassword",
    "driver": "ODBC Driver 17 for SQL Server",
    "trusted_connection": false
  }
}
```

### 5. ODBCドライバーの確認・インストール

```cmd
# インストール済みドライバー確認
python -c "import pyodbc; print(pyodbc.drivers())"
```

もし "ODBC Driver 17 for SQL Server" がない場合：
1. [Microsoft ODBC Driver 17 for SQL Server](https://www.microsoft.com/en-us/download/details.aspx?id=56567) をダウンロード
2. インストーラーを実行

### 6. データベース初期化

```cmd
# データベーステーブル作成
python setup_database_spec.py
```

### 7. アプリケーション起動

```cmd
# UIアプリケーション起動
python app.py
```

ブラウザが自動的に開き、アプリケーションが表示されます。

## トラブルシューティング

### 「pyodbc」インストールエラー
```cmd
# Visual C++ Build Toolsが必要な場合
# Microsoft C++ Build Tools をインストール
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### SQL Server接続エラー
1. **SQL Server Browser サービスが起動しているか確認**
   ```cmd
   services.msc
   # SQL Server Browser を探して起動
   ```

2. **SQL Server認証が有効か確認**
   - SSMS → サーバーのプロパティ → セキュリティ
   - 「SQL Server認証モードとWindows認証モード」を選択

3. **ファイアウォール設定**
   - SQL Server用のポート（デフォルト1433）を開放

### EIKON APIエラー
1. EIKON Desktopが起動しているか確認
2. EIKON にログインしているか確認
3. APIキーが正しいか確認

## 実行ファイル（.exe）の作成

開発環境が整ったら、配布用の実行ファイルを作成できます：

```cmd
# PyInstallerで実行ファイル作成
python build_exe.py

# releaseフォルダに以下が作成されます：
# - LME_News_Watcher.exe
# - config.json
# - start_news_watcher.bat
```

## 運用時の注意事項

1. **定期的なデータベースバックアップ**
   ```sql
   BACKUP DATABASE lme_reporting 
   TO DISK = 'C:\Backup\lme_reporting.bak'
   WITH FORMAT, INIT;
   ```

2. **ログファイルの確認**
   - `logs\` フォルダ内のログファイルで動作状況を確認

3. **自動起動設定**
   - Windows タスクスケジューラーで `start_news_watcher.bat` を登録

## サポート

問題が発生した場合は、以下の情報を準備してお問い合わせください：
- Windows バージョン
- SQL Server バージョン
- エラーメッセージのスクリーンショット
- ログファイル（logs フォルダ内）