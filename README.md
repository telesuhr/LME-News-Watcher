# NewsCollector - Refinitiv金属市場ニュース収集システム

## 概要
Refinitiv EIKON APIを使用して金属市場のニュースを自動収集し、PostgreSQL（将来的にSQL Server）に保存する専用システムです。

## 特徴
- **専門特化**: 金属市場ニュース（LME、銅、アルミ等）に特化
- **高度フィルタリング**: 優先度スコアリング、重複除去、ソース信頼性評価
- **データベース保存**: PostgreSQL対応（SQL Server移行対応設計）
- **エラー耐性**: 包括的なエラーハンドリングとリトライ機構
- **スケジューリング対応**: 日次自動実行向け設計

## システム要件
- Python 3.8+
- PostgreSQL 12+
- Refinitiv EIKON Desktop（実行中）
- 有効なEIKON APIキー

## クイックスタート
```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. config.json でAPIキーとDB情報を設定
# 3. データベース初期化
python setup_database.py

# 4. ニュース収集実行
python collect_news.py

# 5. データ分析
python scripts/analyze_news_data.py
```

## プロジェクト構造
```
NewsCollector/
├── collect_news.py          # メインニュース収集システム
├── database.py              # データベース接続・操作
├── models.py                # データモデル定義
├── setup_database.py        # データベース初期化
├── config.json              # 設定ファイル
├── requirements.txt         # 依存関係
├── logs/                    # 実行ログ
└── scripts/                 # ユーティリティスクリプト
    ├── migrate_to_sqlserver.py
    └── analyze_news_data.py
```