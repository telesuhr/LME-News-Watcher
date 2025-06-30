#!/usr/bin/env python3
"""
LME News Watcher - 実行可能ファイル(.exe)ビルドスクリプト
PyInstallerを使用してWindows実行可能ファイルを作成
"""

import PyInstaller.__main__
import os
import shutil
import sys
import json
from pathlib import Path

def build_executable():
    """実行可能ファイルビルド"""
    
    # ビルド設定
    app_name = "LME_News_Watcher"
    main_script = "app.py"
    
    # PyInstallerのオプション
    pyinstaller_args = [
        main_script,
        '--name', app_name,
        '--onefile',                    # 単一ファイル
        '--windowed',                   # コンソールウィンドウを非表示
        '--add-data', 'web;web',        # Webファイルを含める
        '--add-data', 'config_spec.json;.',  # 設定ファイルを含める
        '--hidden-import', 'eel',
        '--hidden-import', 'psycopg2',
        '--hidden-import', 'pyodbc',
        '--hidden-import', 'eikon',
        '--hidden-import', 'pandas',
        '--hidden-import', 'numpy',
        '--hidden-import', 'google.generativeai',
        '--collect-all', 'eel',
        '--noconfirm',                  # 確認なしで実行
        '--clean',                      # クリーンビルド
    ]
    
    # アイコンファイルの存在確認（存在する場合のみ追加）
    icon_path = Path('web/favicon.ico')
    if icon_path.exists():
        pyinstaller_args.insert(-3, '--icon=web/favicon.ico')  # cleanの前に挿入
        print(f"アイコンファイル使用: {icon_path}")
    else:
        print("アイコンファイルが見つからないため、デフォルトアイコンを使用します")
    
    print("PyInstallerによる実行可能ファイル作成開始...")
    print(f"アプリケーション名: {app_name}")
    print(f"メインスクリプト: {main_script}")
    
    try:
        # PyInstaller実行
        PyInstaller.__main__.run(pyinstaller_args)
        
        print("\n✅ 実行可能ファイル作成完了！")
        print(f"📁 出力ディレクトリ: {Path.cwd() / 'dist'}")
        print(f"🚀 実行ファイル: {Path.cwd() / 'dist' / f'{app_name}.exe'}")
        
        # 配布用ファイルの準備
        prepare_distribution()
        
    except Exception as e:
        print(f"❌ ビルドエラー: {e}")
        sys.exit(1)

def prepare_distribution():
    """配布用ファイル準備"""
    
    dist_dir = Path("dist")
    release_dir = Path("release")
    
    # リリースディレクトリ作成
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # 実行ファイルコピー
    exe_file = dist_dir / "LME_News_Watcher.exe"
    if exe_file.exists():
        shutil.copy2(exe_file, release_dir)
        print(f"✅ 実行ファイルコピー: {exe_file} -> {release_dir}")
    
    # 設定ファイルテンプレートコピー
    config_template = Path("config_spec.json")
    if config_template.exists():
        target_config = release_dir / "config.json"
        shutil.copy2(config_template, target_config)
        print(f"✅ 設定ファイルコピー: {config_template} -> {target_config}")
    
    # READMEファイル作成
    create_distribution_readme(release_dir)
    
    # バッチファイル作成
    create_launch_scripts(release_dir)
    
    print(f"\n📦 配布パッケージ準備完了: {release_dir}")

def create_distribution_readme(release_dir: Path):
    """配布用README作成"""
    
    readme_content = """# LME News Watcher - 実行ガイド

## システム要件
- Windows 10/11 (64bit)
- SQL Server 2019+ (JCLデータベース) または PostgreSQL 12+
- Microsoft ODBC Driver 17 for SQL Server
- Refinitiv EIKON Desktop (実行中)
- インターネット接続

## 初回セットアップ

### 1. データベース準備
既存のSQL Server JCLデータベースまたはPostgreSQLデータベースを使用。
JCLデータベースが推奨（Windows環境）。

### 2. 設定ファイル編集
`config.json`を編集して以下を設定：
- EIKON APIキー
- データベース接続情報（JCL用設定例あり）
- Gemini AI APIキー（AI分析用）

### 3. 初回実行
`LME_News_Watcher.exe`をダブルクリックして実行。
初回実行時に自動的にデータベーステーブルが作成されます。

## 使用方法

### 基本操作
1. アプリケーション起動
2. 最新ニュースタブで自動取得されたニュースを確認
3. 検索・フィルター機能で特定のニュースを探索
4. 手動登録タブで独自のニュースを追加

### バックグラウンド動作
アプリケーションが起動している間、設定された間隔で自動的にニュースを取得します。

## トラブルシューティング

### データベース接続エラー
- PostgreSQL/SQL Serverが起動しているか確認
- config.jsonの接続情報を確認
- ファイアウォール設定を確認

### EIKON APIエラー
- EIKON Desktopが起動しているか確認
- APIキーが正しいか確認
- ネットワーク接続を確認

## サポート
システム管理者にお問い合わせください。

---
Generated by LME News Watcher Build System
"""
    
    readme_file = release_dir / "README.txt"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README作成: {readme_file}")

def create_launch_scripts(release_dir: Path):
    """起動用バッチファイル作成"""
    
    # 通常起動バッチ
    launch_bat = release_dir / "start_news_watcher.bat"
    with open(launch_bat, 'w', encoding='shift_jis') as f:
        f.write("""@echo off
title LME News Watcher
echo LME News Watcher を起動しています...
echo.
echo データベースとEIKON Desktopの準備ができていることを確認してください。
echo.
pause
LME_News_Watcher.exe
pause
""")
    
    # デバッグ起動バッチ
    debug_bat = release_dir / "start_debug.bat"
    with open(debug_bat, 'w', encoding='shift_jis') as f:
        f.write("""@echo off
title LME News Watcher (Debug Mode)
echo LME News Watcher (デバッグモード) を起動しています...
echo エラーメッセージが表示される場合があります。
echo.
LME_News_Watcher.exe
echo.
echo アプリケーションが終了しました。
pause
""")
    
    print(f"✅ 起動スクリプト作成: {launch_bat}, {debug_bat}")

def create_build_info():
    """ビルド情報ファイル作成"""
    from datetime import datetime
    
    build_info = {
        "app_name": "LME News Watcher",
        "version": "1.0.0",
        "build_date": datetime.now().isoformat(),
        "python_version": sys.version,
        "platform": sys.platform
    }
    
    build_info_file = Path("build_info.json")
    with open(build_info_file, 'w', encoding='utf-8') as f:
        json.dump(build_info, f, indent=2, ensure_ascii=False)
    
    print(f"✅ ビルド情報作成: {build_info_file}")

if __name__ == "__main__":
    print("=" * 60)
    print("LME News Watcher - 実行可能ファイル作成")
    print("=" * 60)
    
    # 必要ファイルの存在確認
    required_files = ["app.py", "config_spec.json", "web/index.html"]
    for file_path in required_files:
        if not Path(file_path).exists():
            print(f"❌ 必要ファイルが見つかりません: {file_path}")
            sys.exit(1)
    
    # ビルド情報作成
    create_build_info()
    
    # 実行可能ファイル作成
    build_executable()
    
    print("\n" + "=" * 60)
    print("🎉 ビルド完了！")
    print("📁 release/ ディレクトリから配布可能なファイルを取得してください。")
    print("=" * 60)