# LME News Watcher - セットアップガイド

## 前提条件

### 必須環境

- **Python**: 3.8以上
- **データベース**: PostgreSQL 12+ または SQL Server 2019+
- **Refinitiv**: EIKON Desktop または Workspace
- **OS**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+

### APIキー

- **Refinitiv API Key**: EIKON/Workspace環境で取得
- **Google Gemini API Key**: Google Cloud Consoleで取得

## インストール手順

### 1. リポジトリクローン

```bash
git clone <repository_url>
cd NewsCollector
```

### 2. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 3. データベース設定

#### PostgreSQL（推奨）

```bash
# PostgreSQL インストール (Ubuntu)
sudo apt update
sudo apt install postgresql postgresql-contrib

# データベース作成
sudo -u postgres createdb lme_reporting
sudo -u postgres psql -c "CREATE USER your_username WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lme_reporting TO your_username;"
```

#### SQL Server JCL（本番環境）

Windows認証を使用する場合は、`config_spec.json`でパスワードを空文字列に設定。

### 4. 設定ファイル作成

`config_spec.json`を作成：

```json
{
  "eikon_api_key": "your_refinitiv_api_key",
  "database": {
    "database_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "lme_reporting",
    "user": "your_username",
    "password": "your_password"
  },
  "gemini_integration": {
    "api_key": "your_gemini_api_key",
    "enable_ai_analysis": true
  }
}
```

### 5. データベース初期化

```bash
python setup_database_spec.py
```

### 6. 接続テスト

```bash
# Refinitiv接続テスト
python test_eikon_connection.py

# データベース接続テスト
python -c "from database_spec import SpecDatabaseManager; import json; config = json.load(open('config_spec.json')); db = SpecDatabaseManager(config); print('Connected:', db.test_connection())"
```

### 7. アプリケーション起動

```bash
python app.py
```

ブラウザで http://localhost:8080 にアクセス

## 設定詳細

### ニュース収集設定

```json
"news_collection": {
  "polling_interval_minutes": 5,        // 自動収集間隔
  "collection_period_hours": 24,        // バックグラウンド収集期間
  "manual_collection_period_hours": 6,  // 手動収集期間
  "max_news_per_query": 30,            // クエリあたり最大件数
  "api_rate_limit_delay": 0.5,         // API呼び出し間隔
  "query_interval": 0.3                // クエリ間隔
}
```

### Gemini AI設定

```json
"gemini_integration": {
  "api_key": "your_api_key",
  "enable_ai_analysis": true,
  "model": "gemini-1.5-pro",
  "rate_limit_delay": 4.5,
  "max_daily_cost_usd": 10.0,
  "manual_analysis": {
    "use_fast_model": true,
    "model": "gemini-1.5-flash"
  }
}
```

## トラブルシューティング

### データベース接続エラー

```bash
# PostgreSQL サービス状態確認
sudo systemctl status postgresql

# 接続テスト
psql -h localhost -U your_username -d lme_reporting
```

### Refinitiv API エラー

1. EIKON Desktopが起動しているか確認
2. APIキーが有効か確認
3. ネットワーク接続確認

### ポート8080 使用中エラー

```bash
# ポート使用プロセス確認
lsof -i :8080

# 設定でポート変更
# app.py の eel.start() でport指定
```

## 本番環境デプロイ

### Windows EXE作成

```bash
cd build
python build_exe.py
```

### サービス化

#### systemd (Linux)

```bash
sudo cp scripts/news-watcher.service /etc/systemd/system/
sudo systemctl enable news-watcher
sudo systemctl start news-watcher
```

#### Windows Service

PowerShellで管理者権限：

```powershell
sc create "LME News Watcher" binPath="C:\path\to\LME_News_Watcher.exe"
sc start "LME News Watcher"
```

## 監視・保守

### ログファイル

- `logs/news_watcher_app_YYYYMMDD.log`: アプリケーションログ
- `logs/refinitiv_news_YYYYMMDD.log`: ニュース収集ログ

### データベース保守

```sql
-- 重複ニュース確認
SELECT title, source, COUNT(*) 
FROM news_table 
GROUP BY title, source 
HAVING COUNT(*) > 1;

-- 古いニュース削除（90日以前）
DELETE FROM news_table 
WHERE publish_time < NOW() - INTERVAL '90 days';
```

### パフォーマンス監視

- CPU使用率（AI分析時に高負荷）
- メモリ使用量（大量ニュース処理時）
- ディスク容量（ログとデータベース）
- ネットワーク（API呼び出し）

## セキュリティ

### API Key管理

- 設定ファイルを適切な権限で保護
- 環境変数での機密情報管理推奨
- 定期的なAPI Key更新

### ネットワーク

- ファイアウォール設定（ポート8080）
- HTTPSプロキシ対応（必要に応じて）
- VPN環境での動作確認

### データ保護

- データベース暗号化
- バックアップ暗号化
- アクセスログ監視

## 更新・メンテナンス

### アプリケーション更新

```bash
git pull origin main
pip install -r requirements.txt
python setup_database_spec.py  # 必要に応じて
```

### データベース移行

```bash
# マイグレーションスクリプト実行
python add_read_status_columns.py
```

### 設定ファイル更新

新しい設定項目は自動的にデフォルト値が適用されます。

---

**最終更新**: 2024年12月
**対象バージョン**: 1.0