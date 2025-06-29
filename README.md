# LME News Watcher

**Professional LME (London Metal Exchange) News Monitoring System**

## 🎯 概要

Refinitiv EIKON APIとGoogle Gemini AIを活用した、LME非鉄金属市場の包括的ニュース収集・分析システム。リアルタイムニュース取得、AI分析、直感的なWeb UIを提供します。

## ✨ 主要機能

### 📰 自動ニュース収集
- **Refinitiv EIKON API連携**: リアルタイムニュース取得
- **高度フィルタリング**: LME特化キーワードシステム
- **差分取得**: 重複除去による効率的収集
- **バックグラウンド処理**: 定期自動実行

### 🤖 AI分析エンジン
- **Google Gemini AI**: 高度なニュース分析
- **自動要約**: LME市場影響に特化した要約
- **センチメント分析**: ポジティブ/ネガティブ/ニュートラル
- **重要度スコアリング**: 1-10スケールの影響度評価
- **手動分析・編集**: AI結果の手動調整機能

### 💾 マルチデータベース対応
- **SQL Server JCL**: Windows本番環境（自動検出）
- **PostgreSQL**: 開発・Mac/Linux環境
- **自動切替**: 環境に応じた自動データベース選択
- **完全スキーマ管理**: テーブル自動作成・最適化

### 🖥️ 現代的WebUI
- **タブ式インターフェース**: 最新/過去/手動/統計
- **リアルタイム検索**: 高速フィルタリング
- **レスポンシブデザイン**: モバイル対応
- **統計ダッシュボード**: システム稼働状況

## 🚀 クイックスタート

### システム要件
- **Python**: 3.8+
- **データベース**: SQL Server (JCL) / PostgreSQL 12+
- **Refinitiv**: EIKON Desktop + 有効APIキー
- **OS**: Windows 10/11, macOS, Linux

### インストール手順

```bash
# 1. リポジトリクローン
git clone https://github.com/telesuhr/LME-News-Watcher.git
cd LME-News-Watcher/NewsCollector

# 2. 依存関係インストール
pip install -r requirements.txt

# 3. 設定ファイル編集（APIキー設定）
# config_spec.json を編集

# 4. データベース初期化
python setup_database_spec.py

# 5. アプリケーション起動
python app.py
```

## 📁 プロジェクト構造

```
NewsCollector/
├── 📄 Core Application
│   ├── app.py                    # メインアプリケーション
│   ├── config_spec.json          # 設定ファイル
│   ├── requirements.txt          # 依存関係
│   └── setup_database_spec.py    # DB初期化
│
├── 🔧 Core Modules
│   ├── news_collector_spec.py    # ニュース収集エンジン
│   ├── database_spec.py          # データベース管理
│   ├── database_detector.py      # DB自動検出
│   ├── gemini_analyzer.py        # AI分析エンジン
│   └── models_spec.py            # データモデル
│
├── 🌐 Web Interface
│   └── web/
│       ├── index.html            # メインUI
│       ├── css/style.css         # スタイルシート
│       └── js/app.js             # JavaScript
│
├── 🔨 Build Tools
│   └── build/
│       ├── build_exe.py          # EXE作成スクリプト
│       └── check_build_requirements.py
│
├── 🧪 Tests
│   └── tests/
│       ├── test_database_autodetect.py
│       ├── test_jcl_connection.py
│       ├── test_manual_ai_analysis.py
│       └── test_sqlserver_connection.py
│
├── 📚 Documentation
│   └── docs/
│       ├── USER_MANUAL.md        # 室員向けマニュアル
│       ├── SETUP_GUIDE.md        # セットアップガイド
│       ├── WINDOWS_EXE_BUILD.md  # EXE作成ガイド
│       ├── WINDOWS_JCL_SETUP.md  # JCL設定ガイド
│       └── WINDOWS_SETUP.md      # Windows設定ガイド
│
├── 🔧 Utilities
│   └── scripts/
│       ├── analyze_news_data.py
│       └── migrate_to_sqlserver.py
│
└── 📝 Logs
    └── logs/                     # アプリケーションログ
```

## ⚙️ 設定ファイル例

### 開発環境 (PostgreSQL)
```json
{
  "eikon_api_key": "YOUR_EIKON_API_KEY",
  "database": {
    "database_type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "lme_reporting",
    "user": "your_user",
    "password": "your_password"
  },
  "gemini_integration": {
    "api_key": "YOUR_GEMINI_API_KEY",
    "enable_ai_analysis": true
  }
}
```

### 本番環境 (SQL Server JCL)
```json
{
  "eikon_api_key": "YOUR_EIKON_API_KEY",
  "database": {
    "database_type": "sqlserver",
    "host": "localhost",
    "database": "JCL",
    "trusted_connection": true,
    "driver": "ODBC Driver 17 for SQL Server"
  },
  "gemini_integration": {
    "api_key": "YOUR_GEMINI_API_KEY",
    "enable_ai_analysis": true
  }
}
```

## 🏗️ Windows EXE作成

```bash
# 1. 環境チェック
python build/check_build_requirements.py

# 2. EXE作成
python build/build_exe.py

# 3. 配布パッケージ確認
ls release/
# ├── LME_News_Watcher.exe
# ├── config.json
# ├── README.txt
# └── start_news_watcher.bat
```

## 🧪 テスト実行

```bash
# データベース接続テスト
python tests/test_database_autodetect.py

# JCL接続テスト (Windows)
python tests/test_jcl_connection.py

# AI分析テスト
python tests/test_manual_ai_analysis.py
```

## 🛠️ トラブルシューティング

### データベース接続エラー
- PostgreSQL/SQL Serverサービス確認
- config_spec.json接続情報確認
- ファイアウォール設定確認

### EIKON APIエラー
- EIKON Desktop起動・ログイン確認
- APIキー有効性確認
- ネットワーク接続確認

### 詳細ガイド
- **[📖 室員向けマニュアル](docs/USER_MANUAL.md)** - 日常使用方法
- **[⚙️ セットアップガイド](docs/SETUP_GUIDE.md)** - 詳細インストール手順
- [Windows JCL設定](docs/WINDOWS_JCL_SETUP.md)
- [EXE作成手順](docs/WINDOWS_EXE_BUILD.md)
- [Windows環境設定](docs/WINDOWS_SETUP.md)

## 📊 パフォーマンス

### 期待値
- **実行時間**: 2-4分（設定による）
- **収集件数**: 20-100件/回（市場状況による）
- **UI応答性**: <2秒（通常操作）
- **AI分析**: 15-40秒/記事（モデルによる）

## 🚧 将来の機能拡張

- [ ] Excel出力機能
- [ ] アラート・通知システム
- [ ] 高度な分析レポート
- [ ] モバイルアプリ対応

## 📄 技術スタック

- **Backend**: Python 3.8+, eel, pandas
- **Database**: PostgreSQL, SQL Server
- **AI**: Google Gemini API
- **Frontend**: HTML5, CSS3, JavaScript
- **APIs**: Refinitiv EIKON API
- **Build**: PyInstaller

## 📞 サポート

- **GitHub Issues**: バグ報告・機能要望
- **ドキュメント**: [docs/](docs/) フォルダ参照
- **システム管理者**: 社内サポート

---

**Version**: 1.0.0  
**Last Updated**: 2025-06-29  
**License**: 社内使用