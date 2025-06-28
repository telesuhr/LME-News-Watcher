#!/usr/bin/env python3
"""
Gemini API接続テスト
"""

import google.generativeai as genai
import json

def test_gemini_api():
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    api_key = config['gemini_integration']['api_key']
    print(f"APIキー: {api_key[:10]}...{api_key[-10:]}")
    
    try:
        # Gemini API設定
        genai.configure(api_key=api_key)
        
        # モデル初期化
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # テスト用の簡単なプロンプト
        test_prompt = "こんにちは。このメッセージに「テスト成功」と返答してください。"
        
        print("Gemini APIテスト中...")
        response = model.generate_content(test_prompt)
        
        print(f"✅ API接続成功!")
        print(f"レスポンス: {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ API接続失敗: {e}")
        return False

if __name__ == "__main__":
    test_gemini_api()