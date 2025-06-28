#!/usr/bin/env python3
"""
Gemini 1.5 Pro モデルテスト
"""

import google.generativeai as genai
import json

def test_gemini_pro():
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    api_key = config['gemini_integration']['api_key']
    model_name = config['gemini_integration']['model']
    
    print(f"テスト対象モデル: {model_name}")
    
    try:
        # Gemini API設定
        genai.configure(api_key=api_key)
        
        # モデル初期化
        model = genai.GenerativeModel(model_name)
        
        # テスト用のニュース分析プロンプト
        test_prompt = """以下のLME金属市場ニュースを詳細に要約してください。価格動向、需給状況、市場への具体的影響、地政学的要因、企業動向などの重要なポイントを200文字以内で包括的にまとめてください：

【ニュース】
Copper prices rose 2.5% today on the London Metal Exchange as Chinese demand signals strengthened following new infrastructure announcements. The three-month copper contract reached $8,450 per tonne, the highest in three weeks. Market participants noted strong import data from China's customs office showing 15% month-on-month increase in copper imports. Mining companies including Freeport-McMoRan and Southern Copper saw their shares rise 3-4% in early trading. Analysts expect continued upward pressure on prices due to supply constraints in Peru and Chile.
"""
        
        print("Gemini 1.5 Pro 分析テスト中...")
        response = model.generate_content(test_prompt)
        
        print(f"✅ 分析成功!")
        print(f"要約結果: {response.text}")
        
        # コスト見積もり
        input_tokens = len(test_prompt) / 4  # 概算
        output_tokens = len(response.text) / 4
        
        # Gemini 1.5 Pro の料金: $3.50 per 1M input tokens, $10.50 per 1M output tokens
        input_cost = (input_tokens / 1_000_000) * 3.50
        output_cost = (output_tokens / 1_000_000) * 10.50
        total_cost = input_cost + output_cost
        
        print(f"コスト見積: ${total_cost:.6f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失敗: {e}")
        return False

if __name__ == "__main__":
    test_gemini_pro()