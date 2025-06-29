# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 開発コマンド

### アプリケーション実行
```bash
# デスクトップアプリケーションを起動（データベースとモードを自動検出）
python app.py

# データベースを初期化（SQL Server JCLまたはPostgreSQLを自動検出）
python setup_database_spec.py

# データベース自動検出をテスト
python tests/test_database_autodetect.py

# JCLデータベース接続をテスト（Windows）
python tests/test_jcl_connection.py
```

### ビルドと配布
```bash
# 依存関係をインストール
pip install -r requirements.txt

# Windows実行可能ファイルをビルド
python build/build_exe.py

# ビルド要件をチェック
python build/check_build_requirements.py
```

### テストと開発
```bash
# 手動ニュース収集（開発用）
python -c "from news_collector_spec import RefinitivNewsCollector; collector = RefinitivNewsCollector(); collector.collect_news()"

# データベース接続テスト
python -c "from database_spec import SpecDatabaseManager; import json; config = json.load(open('config_spec.json')); db = SpecDatabaseManager(config['database']); print('Connected:', db.test_connection())"

# 特定機能のテスト
python tests/test_manual_ai_analysis.py
python tests/test_sqlserver_connection.py
```

### 設定
- 全システム設定は `config_spec.json` を編集
- データベース資格情報は `config_spec.json["database"]` に記載
- Refinitiv APIキーは `config_spec.json["eikon_api_key"]` に記載
- Gemini AI設定は `config_spec.json["gemini_integration"]` に記載

## アーキテクチャ概要

### 適応型モードシステム

アプリケーションはRefinitiv EIKON/Workspaceの利用可能性に基づいて2つの異なるモードで動作します：

**アクティブモード（EIKON実行中）**：
- バックグラウンドポーリングによる自動ニュース収集
- リアルタイムRefinitiv API統合
- AI分析を含む全機能セット

**パッシブモード（EIKON利用不可）**：
- データベース閲覧と検索のみ
- 手動ニュース入力機能
- 適切な機能縮退を伴う読み取り専用モード

### コアシステムコンポーネント

**アプリケーションモード管理（`refinitiv_detector.py`）**
- `RefinitivDetector`: EIKON/Workspace接続を自動検出
- `ApplicationModeManager`: モード遷移（アクティブ ↔ パッシブ）を管理
- コールバックシステムによる定期的接続監視
- アプリケーション再起動なしのリアルタイムモード切替

**メインアプリケーション（`app.py`）**
- Eelフレームワークを使用したデスクトップUI のエントリーポイント
- モード対応初期化とバックグラウンドサービス管理
- WebUI通信のためのPython-JavaScriptブリッジ
- 現在のモードに基づく動的機能有効化

**データ収集（`news_collector_spec.py`）**
- `RefinitivNewsCollector`: API統合を伴うメインニュース収集エンジン
- `NewsPollingService`: 設定可能な間隔でのバックグラウンドポーリング
- Refinitiv APIのレート制限とエラー回復を実装
- テキスト処理、重複除去、金属分類を処理

**データベース層（`database_spec.py`）**
- `SpecDatabaseManager`: PostgreSQLとSQL Server操作を抽象化
- `DISTINCT ON (title, source)` を使用したコンテンツベースの重複検出
- 統計と清理ユーティリティを備えた高度な重複管理
- 接続プーリングとトランザクション管理

**データベース自動検出（`database_detector.py`）**
- `DatabaseDetector`: 利用可能なデータベースを自動検出
- SQL Server JCLデータベース（Windows本番環境）を優先、次にPostgreSQL
- SQL ServerのWindows認証をサポート
- フォールバック戦略を備えた環境ベース設定

**AI分析（`gemini_analyzer.py`）**
- `GeminiNewsAnalyzer`: ニュース分析のためのGoogle Gemini API統合
- 手動分析のための高速モデル切替（Gemini Flash vs Pro）
- 日次予算制御を伴うコスト認識レート制限
- 効率的なAPI使用のためのバッチ処理

**データモデル（`models_spec.py`）**
- `NewsArticle`: メタデータを含むコアニュース記事構造
- `NewsSearchFilter`: SQL生成を伴う検索およびフィルタリングロジック
- デュアルデータベースサポートのためのデータベーススキーマ定義
- 手動ニュース入力のための検証関数

### データフロー アーキテクチャ

```
Refinitiv EIKON API ← RefinitivDetector → アクティブ/パッシブモード決定
         ↓                                         ↓
RefinitivNewsCollector → NewsArticleモデル → データベース（重複除去付き）
         ↓                                         ↓
Web UI ← Eelブリッジ ← 検索/閲覧 ← GeminiNewsAnalyzer（非同期分析）
```

**モード依存フロー：**
1. **起動**: `RefinitivDetector` がEIKON接続性をチェック
2. **モード選択**: `ApplicationModeManager` がアクティブ/パッシブモードを決定
3. **機能アクティベーション**: バックグラウンドサービスはアクティブモードでのみ開始
4. **実行時監視**: 動的モード切替による定期的接続性チェック
5. **適切な機能縮退**: UIがリアルタイムで利用可能機能に適応

### データベース設計

**メインテーブル（`news_table`）**
- 全文検索サポート付きのコアニュースストレージ
- Refinitivエントリと手動エントリの両方をサポート
- Gemini統合のためのAI分析フィールド（センチメント、要約、キーワード）
- タイトル+ソースの一意性を使用したコンテンツベースの重複防止

**重複管理**
- `DISTINCT ON`（PostgreSQL）または `ROW_NUMBER()`（SQL Server）を使用したクエリレベルの重複除去
- 既存の重複を検出および削除するための管理ツール
- 重複分析のための統計と容量節約計算

**マルチデータベースサポート**
- PostgreSQL（開発）とSQL Server JCL（本番環境）の互換性
- 環境ベース優先度による自動データベース検出
- データベース固有の最適化を伴う一貫したスキーマ

### UIアーキテクチャ

**技術スタック**
- バックエンド: デスクトップアプリケーション用のPython + Eelフレームワーク
- フロントエンド: バニラHTML/CSS/JavaScript（フレームワーク依存なし）
- 通信: PythonとJavaScript間の双方向RPC

**設定システム**
- マルチタブ設定モーダル（システム状態、キーワード、表示）
- モードインジケーターによるリアルタイムシステム状態監視
- カテゴリ管理による動的検索キーワード設定
- 現在のモードに基づくライブ機能可用性表示

**インターフェース構造**
- タブベースナビゲーション（最新ニュース、アーカイブ、手動入力、統計）
- 詳細ビューと包括的設定のためのモーダルダイアログ
- ヘッダーのリアルタイムモード状態インジケーター
- CSS GridとFlexboxを使用したレスポンシブデザイン

### 設定システム

**中央設定（`config_spec.json`）**
- PostgreSQL/SQL Serverのデータベース接続パラメーター
- LME固有キーワードを伴うRefinitiv API設定とクエリカテゴリ
- コスト制御とモデル選択を伴うGemini AI統合
- ポーリング間隔とパフォーマンスチューニングパラメーター

**ニュース収集のクエリカテゴリ**
- LME金属: 銅、アルミニウム、亜鉛、鉛、ニッケル、スズ
- ベースメタルと工業金属の価格設定
- 中国関連金属ニュースと経済指標
- 需給要因と市場混乱イベント

### 外部統合

**Refinitiv EIKON API**
- 有効なAPIキーを持つEIKON Desktopの実行が必要
- 定期監視による自動接続性検出
- エラー回復を伴うAPIクォータ尊重のためのレート制限
- 収集サイクル間でのストーリーIDベースの重複除去

**Google Gemini AI**
- デュアルモデルサポート: Gemini Pro（包括的）とFlash（高速）
- より高速なモデルを使用した手動分析最適化（15秒 vs 40秒）
- 日次予算制限とレート制限によるコスト最適化
- 重要度スコアリングを伴うLME市場焦点の分析プロンプト

## 開発プラクティス

### モード対応開発
- 開発中は常にアクティブモードとパッシブモードの両方をテスト
- 現在の能力を決定するために `RefinitivDetector.check_refinitiv_availability()` を使用
- パッシブモードユーザーのための適切な機能縮退を実装
- 実行時モード遷移をテスト（EIKON起動/シャットダウン）

### データベース操作
- データベース接続には常にコンテキストマネージャーを使用
- トランザクション管理でエラー時の適切なロールバックを実装
- SQLインジェクション防止のためのパラメーター化クエリを使用
- 全データベース操作でPostgreSQLとSQL Serverの互換性をテスト

### 重複防止
- 新しい検索クエリは確立されたDISTINCTパターンを使用する必要あり
- コンテンツベースの重複除去はタイトル+ソースの組み合わせを考慮すべき
- メンテナンス操作には重複管理ユーティリティを使用
- 本番環境で重複統計を監視

### API統合
- 外部APIの包括的エラーハンドリングを実装
- サービスクォータ尊重のためのレート制限を使用（RefinitivとGemini）
- サービス利用不可時の適切な機能縮退を提供
- API呼び出し削減のため適切な場所でレスポンスをキャッシュ

### UI開発
- JavaScriptから呼び出されるPython関数にはEelの `@eel.expose` デコレーターを使用
- PythonとJavaScript間の日時シリアライゼーションを適切に処理
- ユーザーフィードバック付きUIコールバックでの適切なエラーハンドリングを実装
- バックグラウンド操作とモード遷移中のUI応答性をテスト

### バックグラウンド処理
- ノンブロッキングバックグラウンド操作にはスレッドを使用
- バックグラウンドスレッドの適切なシャットダウンハンドリングを実装
- 異なるアプリケーションモードでのスレッドライフサイクルを監視
- 進行インジケーター付きバックグラウンド操作のUIフィードバックを提供

## 既知の問題と回避策

### ニュース収集でのDateTime64エラー
- **問題**: Refinitiv API呼び出しで頻繁な「datetime64 values must have a unit specified」エラー
- **影響**: 一部のニュースクエリは失敗するが、他のクエリで収集は継続
- **監視**: エラーパターンについて `logs/refinitiv_news_YYYYMMDD.log` のログをチェック
- **回避策**: エラーはログに記録されるが、収集プロセスは停止しない

### モード遷移エッジケース
- **問題**: EIKON起動/シャットダウン中の短時間サービス中断
- **軽減策**: 30秒監視間隔が合理的な応答時間を提供
- **動作**: UIが遷移状態を表示し、自動的に更新

## セキュリティ考慮事項

- APIキーは設定ファイルに保存（ハードコードなし）
- インジェクション攻撃防止のための手動ニュース入力の入力検証
- Windows認証サポート付き設定でのデータベース資格情報の保護
- ログでの情報開示回避のための適切なエラーハンドリング
- API乱用防止とサービスクォータ尊重のためのレート制限

## 詳細仕様

### アプリケーション動作仕様

**起動時動作フロー**
1. 設定ファイル（`config_spec.json`）読み込み
2. データベース自動検出（SQL Server JCL → PostgreSQL の優先順位）
3. Refinitiv EIKON/Workspace接続状態チェック
4. モード決定（アクティブ/パッシブ）とUI起動（ポート8080）
5. アクティブモードの場合：バックグラウンドポーリング開始（5分間隔）

**ニュース収集仕様**
- **収集間隔**: 5分（`polling_interval_minutes`）
- **収集期間**: 過去24時間（`collection_period_hours`）
- **クエリあたり最大件数**: 50件（`max_news_per_query`）
- **API制限**: 0.3秒間隔（`api_rate_limit_delay`）
- **重複チェック期間**: 7日間（`duplicate_check_days`）

**検索カテゴリ構成**
- **LME金属**: LME copper, LME aluminium, LME zinc, LME lead, LME nickel, LME tin
- **ベースメタル**: copper price, aluminium price等の価格関連
- **一般市場**: metal market, commodity market, mining industry
- **中国関連**: China copper, China economy, Shanghai metals
- **需給要因**: metal production, mining output, industrial demand
- **市場混乱**: mining strike, supply disruption, trade war metals

**優先ソース設定**
- **高優先度**: REUTERS, BLOOMBERG, FASTMARKETS, METAL BULLETIN, S&P GLOBAL
- **除外ソース**: SPAM_SOURCE, SOCIAL_MEDIA, BLOG, FORUM

### データベース仕様

**テーブル構造**

**news_table（メインニューステーブル）**
```sql
news_id: VARCHAR(255) PRIMARY KEY        -- ユニークID
title: TEXT NOT NULL                     -- ニュースタイトル
body: TEXT NOT NULL                      -- ニュース本文
publish_time: TIMESTAMP NOT NULL         -- 公開日時
acquire_time: TIMESTAMP NOT NULL         -- 取得日時
source: TEXT NOT NULL                    -- ニュースソース
url: TEXT                                -- 元記事URL
sentiment: TEXT                          -- センチメント分析結果
summary: TEXT                            -- AI要約
keywords: TEXT                           -- 抽出キーワード
related_metals: TEXT                     -- 関連金属
is_manual: BOOLEAN                       -- 手動登録フラグ
```

**system_stats（システム統計テーブル）**
```sql
id: SERIAL PRIMARY KEY                   -- 統計ID
collection_date: TIMESTAMP               -- 収集日時
total_collected: INTEGER                 -- 総収集件数
successful_queries: INTEGER              -- 成功クエリ数
failed_queries: INTEGER                  -- 失敗クエリ数
api_calls_made: INTEGER                  -- API呼び出し回数
errors_encountered: INTEGER              -- エラー発生数
execution_time_seconds: DECIMAL          -- 実行時間
```

**最適化インデックス**
- `idx_news_publish_time`: 公開日時降順索引
- `idx_news_source`: ソース索引
- `idx_news_related_metals`: 関連金属索引
- `idx_news_title_search`: タイトル全文検索索引（PostgreSQL GIN）
- `idx_news_body_search`: 本文全文検索索引（PostgreSQL GIN）

### AI分析仕様

**Google Gemini統合設定**
- **メインモデル**: gemini-1.5-pro（詳細分析用）
- **高速モデル**: gemini-1.5-flash（手動分析用、15秒）
- **レート制限**: 15リクエスト/分、1500リクエスト/日
- **遅延設定**: 4.5秒間隔（`rate_limit_delay`）
- **最大テキスト長**: 4000文字（`max_text_length`）

**コスト最適化設定**
- **日次予算上限**: $10.00（`max_daily_cost_usd`）
- **重複分析スキップ**: 有効（`skip_duplicate_analysis`）
- **バッチサイズ**: 3件（`batch_size`）
- **リトライ設定**: 3回、10秒間隔

**分析項目**
- **要約生成**: LME市場影響特化、最大3文
- **センチメント分析**: ポジティブ/ネガティブ/ニュートラル
- **キーワード抽出**: 8個以内、金属名・価格用語・市場用語優先
- **重要度スコアリング**: 1-10スケール、価格影響・市場規模・時間的影響考慮

### UI仕様

**メインインターフェース**
- **ウィンドウサイズ**: 1400x900ピクセル
- **ポート**: 8080（localhost）
- **ナビゲーション**: 4タブ（最新/過去/手動/統計）
- **表示件数**: 50件/ページ（設定変更可能：25/50/100）

**検索・フィルタリング機能**
- **キーワード検索**: タイトル・本文対象
- **ソースフィルター**: 全ソース、個別ソース選択
- **金属フィルター**: 全金属、個別金属選択
- **タイプフィルター**: 全て、Refinitiv、手動登録
- **日付範囲検索**: 開始日〜終了日指定

**手動ニュース登録仕様**
- **必須項目**: タイトル、本文
- **任意項目**: URL、ソース、公開日時、関連金属
- **バリデーション**: タイトル500文字以内、本文10,000文字以内
- **自動抽出**: 関連金属の自動検出機能

**設定モーダル仕様**
- **システム状態タブ**: モード表示、Refinitiv状態、機能可用性
- **検索キーワードタブ**: LME/市場キーワード、カテゴリ別設定
- **表示設定タブ**: 自動更新、表示件数、UI設定

### パフォーマンス仕様

**実行時間目標**
- **ニュース収集**: 2-4分/回（市場状況により変動）
- **AI分析**: 15-40秒/記事（モデルにより変動）
- **UI応答性**: 2秒以内（通常操作）
- **検索実行**: 1秒以内（1000件まで）

**制限値設定**
- **最大検索結果**: 1000件（`max_search_results`）
- **接続プールサイズ**: 5接続（`connection_pool_size`）
- **バッチサイズ**: 100件（`batch_size`）
- **タイムアウト**: 30秒（`timeout_seconds`）
- **最大リトライ**: 3回（`max_retries`）

**アラート閾値**
- **クリティカルエラー**: 5回（`critical_error_threshold`）
- **収集失敗率**: 70%（`collection_failure_threshold`）
- **最小収集件数**: 5件（`low_collection_count_threshold`）

### ログ仕様

**ログ設定**
- **ログレベル**: INFO（DEBUG切替可能）
- **ログディレクトリ**: `logs/`
- **ファイルサイズ制限**: 10MB（`max_log_size_mb`）
- **バックアップ保持**: 5世代（`backup_count`）
- **ファイル命名**: `refinitiv_news_YYYYMMDD.log`

**ログ出力内容**
- **INFO**: 収集開始/終了、件数、API呼び出し状況
- **ERROR**: API呼び出し失敗、データベースエラー、接続問題
- **WARNING**: インデックス作成警告、設定値異常

### ビルド仕様

**Windows EXE作成**
- **ツール**: PyInstaller
- **実行ファイル名**: `LME_News_Watcher.exe`
- **パッケージング**: ワンファイル形式（`--onefile`）
- **UI**: ウィンドウモード（`--windowed`）
- **含有ファイル**: web/フォルダ一式、config_spec.json

**配布パッケージ構成**
```
release/
├── LME_News_Watcher.exe      # メイン実行ファイル
├── config.json               # サンプル設定ファイル
├── README.txt                # 利用手順
└── start_news_watcher.bat    # 起動バッチファイル
```

**必要ランタイム**
- Python 3.8+（ソース実行時）
- VC++ Redistributable（EXE実行時）
- ODBC Driver 17 for SQL Server（SQL Server使用時）

### エラーハンドリング仕様

**Refinitiv APIエラー**
- **接続エラー**: パッシブモードに自動切替
- **認証エラー**: エラーログ出力、再試行無し
- **レート制限**: 遅延後リトライ（最大3回）
- **データエラー**: 該当クエリスキップ、他クエリ継続

**データベースエラー**
- **接続失敗**: アプリケーション終了
- **クエリエラー**: ロールバック実行、エラーログ出力
- **トランザクションエラー**: 自動ロールバック、状態復旧

**UIエラー**
- **JavaScriptエラー**: コンソールログ出力、処理継続
- **通信エラー**: ユーザー通知、再試行ボタン表示
- **モーダルエラー**: モーダル閉じる、エラーメッセージ表示