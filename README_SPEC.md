# LME News Watcher - Refinitivニュースモニタリングシステム

**Professional LME (London Metal Exchange) News Monitoring System**

## 🎯 概要

LME非鉄金属および市場全般のニュースをRefinitiv EIKON Data APIからリアルタイムに近い形で取得し、データベースに保存する包括的なニュースモニタリングシステムです。Web技術ベースのサーバーレスUIツールにより、非IT部門の室員でも容易にニュースの確認、検索、フィルタリング、過去ニュースの閲覧、および手動ニュース登録が可能です。

## ✨ 主要機能

### 🔄 自動ニュース収集
- **Refinitiv EIKON API連携**: 認証、ポーリング（5分間隔設定可能）
- **高度フィルタリング**: LME非鉄金属・市場関連ニュースに特化
- **差分取得**: 重複除去ロジックによる効率的データ収集
- **関連金属自動抽出**: 銅、アルミ等の金属カテゴリ自動分類

### 🖥️ デスクトップUIアプリケーション  
- **サーバーレス設計**: eel + Web技術によるデスクトップアプリ
- **リアルタイム表示**: 最新ニュース一覧、検索・フィルタリング
- **過去ニュースアクセス**: 日付範囲指定による履歴検索
- **手動ニュース登録**: 独自ニュース追加フォーム
- **統計ダッシュボード**: システム稼働状況・収集統計

### 🗄️ データベース対応
- **開発**: PostgreSQL 12+
- **本番**: SQL Server 2019+ （移行対応設計）
- **将来拡張**: Gemini API連携フィールド準備済み

### 📦 .exe配布対応
- **PyInstaller**: Windows実行可能ファイル作成
- **ワンクリック起動**: Python環境不要の単体実行
- **設定ファイル**: 外部config.jsonによる柔軟な設定

## 🚀 クイックスタート

### システム要件
- **Python**: 3.8+
- **データベース**: PostgreSQL 12+ / SQL Server 2019+
- **Refinitiv**: EIKON Desktop（実行中）+ 有効APIキー
- **OS**: Windows 10/11, macOS, Linux

### インストール手順

```bash
# 1. リポジトリクローン
git clone https://github.com/telesuhr/LME-News-Watcher.git
cd LME-News-Watcher/NewsCollector

# 2. 依存関係インストール
pip install -r requirements.txt

# 3. 設定ファイル編集
# config_spec.json でAPIキー・DB接続情報を設定

# 4. データベース初期化
python setup_database_spec.py

# 5. UIアプリケーション起動
python app.py
```

### 設定ファイル例 (config_spec.json)
```json
{
  "eikon_api_key": "YOUR_ACTUAL_EIKON_API_KEY",
  "database": {
    "database_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "lme_reporting",
    "user": "your_user",
    "password": "your_password"
  },
  "news_collection": {
    "polling_interval_minutes": 5,
    "collection_period_hours": 24,
    "lme_only_filter": false
  }
}
```

## 🏗️ システム構成

### アーキテクチャ図
```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   Refinitiv EIKON   │───▶│   News Collector     │───▶│   PostgreSQL/       │
│   Data API          │    │   (Background)       │    │   SQL Server        │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                       │                           ▲
                                       ▼                           │
┌─────────────────────┐    ┌──────────────────────┐               │
│   Desktop UI        │◀───│   eel Application    │───────────────┘
│   (Web Technologies)│    │   (Python Backend)   │
└─────────────────────┘    └──────────────────────┘
```

### 主要コンポーネント

#### 1. ニュース取得・データ処理部 (`news_collector_spec.py`)
- **RefinitivNewsCollector**: API連携・データ取得
- **NewsPollingService**: バックグラウンドポーリング
- **差分取得ロジック**: 重複除去・効率的収集
- **金属カテゴリ抽出**: 自動関連金属分類

#### 2. データベース管理 (`database_spec.py`)
- **SpecDatabaseManager**: PostgreSQL/SQL Server両対応
- **検索機能**: 高度フィルタリング・全文検索
- **統計機能**: システム稼働状況追跡

#### 3. UIアプリケーション (`app.py`)
- **eelフレームワーク**: Python-JavaScript連携
- **リアルタイム更新**: 自動リフレッシュ機能
- **レスポンシブUI**: モバイル対応デザイン

#### 4. データモデル (`models_spec.py`)
```sql
-- ニューステーブル（仕様書準拠）
CREATE TABLE news_table (
    news_id VARCHAR(255) PRIMARY KEY,     -- Refinitiv ID / システム生成ID
    title TEXT NOT NULL,                  -- ヘッドライン
    body TEXT NOT NULL,                   -- 本文
    publish_time TIMESTAMP NOT NULL,      -- 公開日時
    acquire_time TIMESTAMP NOT NULL,      -- 取得日時
    source TEXT NOT NULL,                 -- ソース
    url TEXT,                            -- 元記事URL
    sentiment TEXT,                      -- 将来Gemini用
    summary TEXT,                        -- 将来Gemini用
    keywords TEXT,                       -- 将来Gemini用
    related_metals TEXT,                 -- 関連金属
    is_manual BOOLEAN DEFAULT FALSE      -- 手動登録フラグ
);
```

## 📊 機能詳細

### ニュース一覧表示
- **時系列表示**: 最新ニュースから降順
- **ソース表示**: Refinitiv/手動登録バッジ
- **メタデータ**: 公開日時、ソース、関連金属
- **プレビュー**: 本文冒頭200文字表示

### 検索・フィルタリング
- **キーワード検索**: タイトル・本文全文検索
- **ソースフィルター**: ニュース配信元別表示
- **金属フィルター**: 銅、アルミ等の金属別表示
- **タイプフィルター**: Refinitiv/手動登録別表示
- **日付範囲**: 過去ニュース期間指定検索

### 手動ニュース登録
- **入力検証**: 必須項目チェック・文字数制限
- **自動補完**: 関連金属自動抽出
- **柔軟性**: ソース・URL・公開日時設定可能
- **即座反映**: 登録後即座にリスト更新

### 統計ダッシュボード
- **収集統計**: 総ニュース数、今日の収集数
- **ソース分析**: Refinitiv vs 手動登録比率
- **システム稼働**: 実行回数・平均実行時間
- **エラー監視**: API呼び出し失敗・データベースエラー

## 🔧 開発・カスタマイズ

### 開発環境セットアップ
```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 開発用依存関係
pip install -r requirements.txt

# データベース初期化
python setup_database_spec.py

# 開発サーバー起動
python app.py
```

### .exe配布ファイル作成
```bash
# 実行可能ファイルビルド
python build_exe.py

# 配布パッケージ確認
ls release/
# ├── LME_News_Watcher.exe
# ├── config.json
# ├── README.txt
# ├── start_news_watcher.bat
# └── start_debug.bat
```

### 設定カスタマイズ

#### ポーリング設定
```json
"news_collection": {
    "polling_interval_minutes": 5,    // 5分間隔
    "collection_period_hours": 24,    // 24時間分取得
    "max_news_per_query": 50,         // クエリあたり最大50件
    "api_rate_limit_delay": 0.3       // API制限対策0.3秒
}
```

#### フィルタリング設定
```json
"query_categories": {
    "lme_metals": ["LME copper", "LME aluminium", ...],
    "market_general": ["metal market", "commodity market", ...],
    "china_related": ["China copper", "Chinese demand", ...]
}
```

## 🛠️ トラブルシューティング

### よくある問題

#### データベース接続エラー
```
ERROR - データベース接続エラー
```
**対処法:**
- PostgreSQL/SQL Serverサービス起動確認
- config_spec.jsonの接続情報確認
- ファイアウォール・ネットワーク設定確認

#### EIKON API エラー
```
ERROR - EIKON API初期化エラー
```
**対処法:**
- EIKON Desktop起動・ログイン確認
- APIキーの有効性確認
- ネットワーク接続確認

#### UI起動エラー
```
ERROR - ポート8080は既に使用中
```
**対処法:**
- 他のアプリケーション終了
- config_spec.jsonでポート変更
- システム再起動

### ログファイル確認
```bash
# アプリケーションログ
tail -f logs/news_watcher_app_YYYYMMDD.log

# ニュース収集ログ  
tail -f logs/refinitiv_news_YYYYMMDD.log

# データベース初期化ログ
cat setup_database_spec_YYYYMMDD_HHMMSS.log
```

## 🚧 将来の機能拡張

### Gemini AI連携（準備済み）
- **sentiment**: ニュース感情分析
- **summary**: 自動要約生成
- **keywords**: キーワード自動抽出

### 設定項目
```json
"gemini_integration": {
    "enable_ai_analysis": false,      // 現在無効
    "api_key": "YOUR_GEMINI_API_KEY",
    "sentiment_analysis": false,
    "summary_generation": false,
    "keyword_extraction": false
}
```

### SQL Server移行（対応済み）
```json
"database": {
    "database_type": "sqlserver",
    "server": "localhost",
    "database": "lme_news",
    "user": "sa",
    "password": "your_password"
}
```

## 📈 パフォーマンス指標

### 期待値
- **実行時間**: 2-4分（設定・ニュース量による）
- **収集件数**: 20-100件/回（市場状況による）
- **API呼び出し**: 10-30回/実行
- **UI応答性**: <2秒（通常操作）

### 最適化のポイント
- **API制限遵守**: 0.3秒間隔での順次処理
- **効率的検索**: PostgreSQL全文検索インデックス
- **メモリ管理**: バッチサイズ制限・適切なページネーション

## 📄 ライセンス・サポート

### 使用技術
- **Python**: 3.8+ (MIT License)
- **eel**: デスクトップアプリフレームワーク (MIT License)
- **PostgreSQL**: オープンソースデータベース (PostgreSQL License)
- **Refinitiv EIKON**: 商用APIライセンス必要

### サポート
- **GitHub Issues**: バグ報告・機能要望
- **システム管理者**: 社内サポート
- **ドキュメント**: README_SPEC.md（本ファイル）

---

**Last Updated**: 2025-06-28  
**Version**: 1.0.0 (仕様書完全準拠)  
**Compatibility**: PostgreSQL/SQL Server, Windows/macOS/Linux