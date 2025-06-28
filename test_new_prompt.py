#!/usr/bin/env python3
"""
新しいプロンプトでGemini AI分析テスト
"""

import google.generativeai as genai
import json

def test_new_prompt():
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    api_key = config['gemini_integration']['api_key']
    model_name = config['gemini_integration']['model']
    new_prompt = config['gemini_integration']['analysis_prompts']['summary']
    
    print(f"使用モデル: {model_name}")
    print(f"新プロンプト: {new_prompt}")
    
    try:
        # Gemini API設定
        genai.configure(api_key=api_key)
        
        # モデル初期化
        model = genai.GenerativeModel(model_name)
        
        # テスト用のニュースデータ
        test_news_samples = [
            {
                "title": "China's Economic Stimulus Package Announced",
                "content": "China announced a $500 billion economic stimulus package focusing on infrastructure development and manufacturing. The package includes significant investments in electric vehicle charging networks, renewable energy infrastructure, and urban development projects. This comes as China's GDP growth slowed to 4.8% in the last quarter. Market analysts expect increased demand for industrial metals including copper, aluminum, and steel. The announcement has already led to a 2% rise in Shanghai Composite Index."
            },
            {
                "title": "Major Copper Mine Strike in Chile Enters Second Week",
                "content": "Workers at Escondida, the world's largest copper mine, continue their strike for the second week over wage disputes. The mine produces approximately 5% of global copper supply. Union leaders reject the latest offer from BHP Billiton. Daily production loss is estimated at 3,400 tonnes of copper. Spot copper prices have risen 3.2% since the strike began. Other major miners including Freeport-McMoRan are monitoring the situation closely."
            },
            {
                "title": "Federal Reserve Announces Interest Rate Decision",
                "content": "The Federal Reserve announced a 0.25% interest rate cut, bringing the federal funds rate to 5.0%. Fed Chair Jerome Powell cited concerns about global economic slowdown and trade tensions. The decision was unanimous among voting members. Dollar index fell 1.1% following the announcement. Commodity markets generally react positively to lower interest rates as they reduce holding costs for non-yielding assets."
            }
        ]
        
        print("\n=== 新プロンプトテスト結果 ===")
        
        for i, sample in enumerate(test_news_samples):
            print(f"\n--- テスト {i+1}: {sample['title']} ---")
            
            # プロンプト構築
            full_prompt = f"{new_prompt}\n\n【ニュース】\nタイトル: {sample['title']}\n内容: {sample['content']}"
            
            print("分析中...")
            response = model.generate_content(full_prompt)
            
            print(f"✅ 分析結果:")
            print(f"{response.text}")
            print("-" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        return False

if __name__ == "__main__":
    test_new_prompt()