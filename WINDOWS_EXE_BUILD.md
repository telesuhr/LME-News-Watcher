# Windows EXEファイル作成ガイド

## 概要
このガイドでは、LME News WatcherをWindows実行可能ファイル（.exe）として作成する手順を説明します。

## 前提条件

### 1. 開発環境
- **Windows 10/11** (64bit)
- **Python 3.8+** がインストール済み
- **Git** がインストール済み

### 2. 必要なパッケージ
```bash
# 必要パッケージのインストール
pip install pyinstaller
pip install -r requirements.txt
```

## EXE作成手順

### 1. プロジェクトのクローン・準備
```bash
# GitHubからクローン
git clone https://github.com/telesuhr/LME-News-Watcher.git
cd LME-News-Watcher/NewsCollector

# 依存関係インストール
pip install -r requirements.txt
pip install pyinstaller
```

### 2. 設定ファイルの準備
本番用の設定ファイルを準備：

```json
{
  "eikon_api_key": "your_eikon_api_key_here",
  "database": {
    "database_type": "sqlserver",
    "host": "localhost",
    "database": "JCL",
    "trusted_connection": true,
    "driver": "ODBC Driver 17 for SQL Server"
  },
  "gemini_integration": {
    "api_key": "your_gemini_api_key_here",
    "enable_ai_analysis": true
  }
}
```

### 3. EXEファイル作成
```bash
# ビルドスクリプト実行
python build_exe.py
```

### 4. 出力ファイル
作成されるファイル：
- `dist/LME_News_Watcher.exe` - 実行可能ファイル
- `release/` - 配布用パッケージ
  - `LME_News_Watcher.exe`
  - `config.json` - 設定ファイルテンプレート
  - `README.txt` - 使用方法
  - `start_news_watcher.bat` - 起動スクリプト
  - `start_debug.bat` - デバッグ用起動

## 配布パッケージの内容

### 実行ファイル
- **LME_News_Watcher.exe**: メインアプリケーション
- **start_news_watcher.bat**: 推奨起動方法
- **start_debug.bat**: トラブルシューティング用

### 設定ファイル
- **config.json**: データベース・API設定

### ドキュメント
- **README.txt**: エンドユーザー向けガイド

## ビルドオプションの説明

### PyInstallerオプション
```python
pyinstaller_args = [
    'app.py',                        # メインスクリプト
    '--name', 'LME_News_Watcher',    # EXE名
    '--onefile',                     # 単一ファイル作成
    '--windowed',                    # コンソール非表示
    '--add-data', 'web;web',         # Web UIファイル組み込み
    '--add-data', 'config_spec.json;.',  # 設定ファイル組み込み
    '--hidden-import', 'eel',        # 必要モジュール明示
    '--hidden-import', 'psycopg2',   # PostgreSQL
    '--hidden-import', 'pyodbc',     # SQL Server
    '--hidden-import', 'eikon',      # Refinitiv
    '--hidden-import', 'google.generativeai',  # Gemini AI
    '--collect-all', 'eel',          # Eelの全ファイル含める
]
```

### 含まれるファイル
- **Web UI**: HTML, CSS, JavaScript
- **設定**: config_spec.json
- **依存関係**: 全必要ライブラリ
- **アイコン**: favicon.ico（存在する場合）

## トラブルシューティング

### よくある問題

#### 1. ビルドエラー: "Module not found"
```bash
# 必要なパッケージを再インストール
pip uninstall -y pyinstaller
pip install pyinstaller
pip install --upgrade setuptools
```

#### 2. EXE実行エラー: "DLL load failed"
- Microsoft Visual C++ Redistributableをインストール
- .NET Framework 4.8をインストール

#### 3. データベース接続エラー
- Microsoft ODBC Driver 17をインストール
- SQL Serverサービスが起動していることを確認

#### 4. EIKONエラー
- EIKON Desktopが起動していることを確認
- APIキーの有効性確認

### デバッグ方法

#### 1. コンソール版でテスト
```bash
# --windowedを除いてビルド
pyinstaller app.py --onefile --add-data "web;web" --add-data "config_spec.json;."
```

#### 2. ログ確認
```bash
# start_debug.batで起動してエラーメッセージ確認
start_debug.bat
```

#### 3. 依存関係確認
```bash
# 必要なDLLの確認
python -m pip check
```

## 配布前チェックリスト

### 必須確認項目
- [ ] Windows PCでEXEが起動する
- [ ] データベース接続が正常
- [ ] EIKONとの連携が動作
- [ ] Web UI表示が正常
- [ ] ニュース収集機能が動作
- [ ] AI分析機能が動作

### 設定ファイル確認
- [ ] 本番用APIキーに変更済み
- [ ] JCLデータベース設定が正しい
- [ ] セキュリティ情報が除去済み

### パッケージング確認
- [ ] 全必要ファイルが含まれている
- [ ] README.txtが最新
- [ ] 起動スクリプトが動作

## セキュリティ注意事項

### 機密情報の保護
- APIキーは設定ファイルで管理
- EXEファイルにハードコードしない
- 配布時はテンプレート設定を使用

### ファイル権限
- 実行権限の設定
- ログディレクトリの書き込み権限
- 設定ファイルの読み取り権限

## 大容量ファイル対応

### サイズ最適化
```python
# 不要なモジュールを除外
'--exclude-module', 'tkinter',
'--exclude-module', 'matplotlib',
'--exclude-module', 'scipy',
```

### UPX圧縮（オプション）
```bash
# UPXでファイルサイズ圧縮
upx --best LME_News_Watcher.exe
```

## 配布方法

### 内部配布
1. ZIP形式でパッケージング
2. 社内ファイルサーバーにアップロード
3. インストール手順書も同梱

### インストーラー作成（上級者向け）
- Inno Setup使用
- NSIS使用
- MSIパッケージ作成

## メンテナンス

### 更新手順
1. ソースコード更新
2. ビルドスクリプト実行
3. テスト実行
4. 配布パッケージ作成

### バージョン管理
```python
# build_exe.pyでバージョン情報更新
build_info = {
    "version": "1.1.0",  # 更新
    "build_date": datetime.now().isoformat()
}
```

このガイドに従って、Windows環境でLME News WatcherのEXEファイルを作成・配布してください。