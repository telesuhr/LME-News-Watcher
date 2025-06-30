#!/usr/bin/env python3
"""
EXEビルド要件チェックスクリプト
Windows環境でのEXE作成前の環境確認
"""

import sys
import os
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Python バージョン確認"""
    print("=== Python バージョン確認 ===")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python バージョン OK")
        return True
    else:
        print("❌ Python 3.8以上が必要です")
        return False

def check_required_packages():
    """必要パッケージの確認"""
    print("\n=== 必要パッケージ確認 ===")
    
    required_packages = [
        'eel',
        'pandas',
        'numpy',
        'eikon',
        'psycopg2',
        'pyodbc',
        'google.generativeai',
        'PyInstaller'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未インストール")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n未インストールパッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print("pip install -r requirements.txt")
        return False
    else:
        print("✅ 全パッケージインストール済み")
        return True

def check_required_files():
    """必要ファイルの確認"""
    print("\n=== 必要ファイル確認 ===")
    
    required_files = [
        'app.py',
        'config_spec.json',
        'web/index.html',
        'web/css/style.css',
        'web/js/app.js',
        'build/build_exe.py'  # buildディレクトリ内に修正
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - ファイルが見つかりません")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n見つからないファイル: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 全必要ファイル存在")
        return True

def check_pyinstaller():
    """PyInstaller動作確認"""
    print("\n=== PyInstaller確認 ===")
    
    try:
        result = subprocess.run(['pyinstaller', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ PyInstaller {version}")
            return True
        else:
            print("❌ PyInstaller実行エラー")
            return False
    except subprocess.TimeoutExpired:
        print("❌ PyInstaller実行タイムアウト")
        return False
    except FileNotFoundError:
        print("❌ PyInstallerが見つかりません")
        print("pip install PyInstaller でインストールしてください")
        return False

def check_platform():
    """プラットフォーム確認"""
    print("\n=== プラットフォーム確認 ===")
    
    platform = sys.platform
    print(f"プラットフォーム: {platform}")
    
    if platform.startswith('win'):
        print("✅ Windows環境 - EXE作成可能")
        return True
    else:
        print("⚠️  非Windows環境 - EXE作成はWindows上で実行してください")
        return False

def get_build_recommendations():
    """ビルド推奨事項"""
    print("\n=== ビルド推奨事項 ===")
    
    recommendations = [
        "1. 仮想環境での実行を推奨 (venv, conda等)",
        "2. 最新のPyInstallerを使用: pip install --upgrade PyInstaller", 
        "3. Windows Defender/アンチウイルスを一時無効化",
        "4. 管理者権限でコマンドプロンプトを実行",
        "5. 十分なディスク容量を確保 (最低1GB)",
        "6. build_exe.py実行前にテスト実行: python app.py"
    ]
    
    for rec in recommendations:
        print(f"💡 {rec}")

def main():
    """メイン確認処理"""
    print("=" * 60)
    print("LME News Watcher - EXEビルド要件チェック")
    print("=" * 60)
    
    checks = [
        check_python_version,
        check_platform,
        check_required_files,
        check_required_packages,
        check_pyinstaller
    ]
    
    results = []
    for check in checks:
        results.append(check())
    
    print("\n" + "=" * 60)
    
    if all(results):
        print("🎉 ビルド要件チェック完了 - EXE作成準備OK!")
        print("\n次のステップ:")
        print("1. python build_exe.py")
        print("2. dist/LME_News_Watcher.exe を確認")
        print("3. release/ フォルダから配布パッケージ取得")
    else:
        print("❌ ビルド要件に問題があります")
        print("上記のエラーを修正してから再実行してください")
    
    get_build_recommendations()
    
    print("=" * 60)
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)