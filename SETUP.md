# NewsCollector セットアップガイド

## 前提条件

### 1. システム要件
- **Python**: 3.8以上
- **PostgreSQL**: 12以上（将来的にSQL Server対応）
- **Refinitiv EIKON Desktop**: 実行中であること
- **EIKON APIキー**: 有効なAPIキー

### 2. PostgreSQL準備
```sql
-- データベース作成
CREATE DATABASE news_collector;

-- ユーザー作成（オプション）
CREATE USER news_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE news_collector TO news_user;
```

## インストール手順

### Step 1: 依存関係インストール
```bash
# Python仮想環境作成（推奨）
python -m venv venv

# 仮想環境有効化
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# パッケージインストール
pip install -r requirements.txt
```

### Step 2: 設定ファイル編集
`config.json` を編集してください：

```json
{
  "eikon_api_key": "YOUR_ACTUAL_EIKON_API_KEY",
  
  "database": {
    "database_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "news_collector",
    "user": "news_user",
    "password": "your_secure_password"
  }
}
```

### Step 3: データベース初期化
```bash
python setup_database.py
```

成功すると以下のメッセージが表示されます：
```
🎉 NewsCollector データベース初期化完了!
```

### Step 4: 動作確認
```bash
# ニュース収集テスト実行
python collect_news.py
```

## 使用方法

### 基本的な実行
```bash
# ニュース収集実行
python collect_news.py
```

### データ分析
```bash
# 収集データ分析
python scripts/analyze_news_data.py
```

### SQL Server移行（将来）
```bash
# PostgreSQL → SQL Server移行
python scripts/migrate_to_sqlserver.py
```

## 設定カスタマイズ

### ニュース収集設定
`config.json` の `news_settings` セクション：

- **収集対象**: `target_metals` で金属種類を指定
- **優先度フィルタ**: `minimum_priority_score` で最小スコア設定
- **API制限**: `api_rate_limit_delay` で呼び出し間隔調整
- **除外ソース**: `excluded_sources` で不要なソースを除外

### パフォーマンス調整
```json
"performance": {
  "max_retries": 3,
  "timeout_seconds": 30,
  "batch_size": 100
}
```

## トラブルシューティング

### 1. データベース接続エラー
```
ERROR - データベース接続エラー
```

**対処法:**
- PostgreSQLサーバーが起動しているか確認
- `config.json` の接続情報を確認
- ユーザー権限を確認

### 2. EIKON API エラー
```
ERROR - EIKON API初期化エラー
```

**対処法:**
- EIKON Desktopが起動しているか確認
- APIキーが正しいか確認
- ネットワーク接続を確認

### 3. API制限エラー
```
WARNING - API制限に達しました
```

**対処法:**
- `api_rate_limit_delay` を増加（例: 0.5秒）
- `max_news_per_query` を減少（例: 30）

## 定期実行設定

### Windows タスクスケジューラ
```xml
<!-- task_scheduler.xml として保存 -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2025-01-01T09:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>collect_news.py</Arguments>
      <WorkingDirectory>C:\path\to\NewsCollector</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

### Linux cron
```bash
# crontab -e で編集
# 平日午前9時に実行
0 9 * * 1-5 cd /path/to/NewsCollector && python collect_news.py
```

## データベーススキーマ

### news_items テーブル
```sql
-- ニュースアイテム
CREATE TABLE news_items (
    id SERIAL PRIMARY KEY,
    story_id VARCHAR(255) UNIQUE NOT NULL,  -- Refinitive Story ID
    headline TEXT NOT NULL,                 -- ヘッドライン
    source VARCHAR(100) NOT NULL,           -- ニュースソース
    published_date TIMESTAMP NOT NULL,      -- 公開日時
    body TEXT,                             -- 本文
    priority_score INTEGER DEFAULT 0,      -- 優先度スコア
    metal_category VARCHAR(50),            -- 金属カテゴリ
    keywords TEXT,                         -- キーワード（JSON）
    query_type VARCHAR(50),                -- 検索クエリタイプ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### collection_stats テーブル
```sql
-- 収集統計
CREATE TABLE collection_stats (
    id SERIAL PRIMARY KEY,
    collection_date TIMESTAMP NOT NULL,    -- 収集日時
    total_collected INTEGER DEFAULT 0,     -- 総収集件数
    successful_queries INTEGER DEFAULT 0,  -- 成功クエリ数
    failed_queries INTEGER DEFAULT 0,      -- 失敗クエリ数
    high_priority_count INTEGER DEFAULT 0, -- 高優先度件数
    medium_priority_count INTEGER DEFAULT 0, -- 中優先度件数
    low_priority_count INTEGER DEFAULT 0,  -- 低優先度件数
    duplicate_removed INTEGER DEFAULT 0,   -- 重複除去件数
    execution_time_seconds DECIMAL(10,3),  -- 実行時間
    api_calls_made INTEGER DEFAULT 0,      -- API呼び出し回数
    errors_encountered INTEGER DEFAULT 0,  -- エラー発生数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## パフォーマンス指標

### 期待値
- **実行時間**: 3-5分（設定による）
- **収集件数**: 50-200件/日（市場状況による）
- **API呼び出し**: 20-50回/実行
- **データ品質**: 95%以上の成功率

### 最適化のポイント
1. **API制限遵守**: 呼び出し間隔の適切な設定
2. **重複除去**: 効率的な重複チェック
3. **優先度フィルタ**: 不要データの除外
4. **エラー処理**: 堅牢なエラーハンドリング

## サポート

### ログファイル
- `logs/news_collector_YYYYMMDD.log` - 日次実行ログ
- `setup_database.log` - セットアップログ

### 連絡先
- GitHub Issues
- システム管理者