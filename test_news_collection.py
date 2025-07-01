#!/usr/bin/env python3
"""
ニュース収集テスト・検証スクリプト
"""

import eikon as ek
import json
import pandas as pd
from datetime import datetime, timedelta

def test_basic_api():
    """基本的なAPI動作テスト"""
    print("🔍 Refinitiv API基本テスト")
    
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # APIキー設定
    ek.set_app_key(config["eikon_api_key"])
    
    # 1. 基本的なニュース取得テスト
    print("\n1. 基本ニュース取得テスト (件数指定なし)")
    try:
        headlines = ek.get_news_headlines("copper")
        print(f"   結果: {len(headlines) if headlines is not None else 0}件")
        if headlines is not None and not headlines.empty:
            print(f"   カラム: {list(headlines.columns)}")
            print(f"   最新記事: {headlines.iloc[0]['text'][:50]}...")
    except Exception as e:
        print(f"   エラー: {e}")
    
    # 2. 件数指定テスト
    print("\n2. 件数指定テスト (100件)")
    try:
        headlines = ek.get_news_headlines("copper", count=100)
        print(f"   結果: {len(headlines) if headlines is not None else 0}件")
        if headlines is not None and not headlines.empty:
            # 日時の範囲確認
            if 'versionCreated' in headlines.columns:
                dates = pd.to_datetime(headlines['versionCreated'], errors='coerce')
                print(f"   最新記事: {dates.max()}")
                print(f"   最古記事: {dates.min()}")
    except Exception as e:
        print(f"   エラー: {e}")
    
    # 3. 複数クエリテスト
    print("\n3. 複数クエリテスト")
    queries = ["copper", "aluminium", "zinc", "LME", "base metals"]
    for query in queries:
        try:
            headlines = ek.get_news_headlines(query, count=20)
            count = len(headlines) if headlines is not None else 0
            print(f"   '{query}': {count}件")
        except Exception as e:
            print(f"   '{query}': エラー - {e}")

def test_date_filtering():
    """日付フィルタリングテスト"""
    print("\n🔍 日付フィルタリングテスト")
    
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    ek.set_app_key(config["eikon_api_key"])
    
    # 期間設定（過去6時間）
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=6)
    
    print(f"対象期間: {start_date.strftime('%Y-%m-%d %H:%M')} ～ {end_date.strftime('%Y-%m-%d %H:%M')}")
    
    try:
        headlines = ek.get_news_headlines("copper", count=100)
        print(f"API取得件数: {len(headlines) if headlines is not None else 0}件")
        
        if headlines is not None and not headlines.empty:
            # 日付カラム確認
            print(f"利用可能カラム: {list(headlines.columns)}")
            
            if 'versionCreated' in headlines.columns:
                # 日付変換とフィルタリング
                headlines['created_dt'] = pd.to_datetime(headlines['versionCreated'], errors='coerce')
                
                # 全記事の日時範囲
                all_dates = headlines['created_dt'].dropna()
                if not all_dates.empty:
                    print(f"全記事日時範囲: {all_dates.min()} ～ {all_dates.max()}")
                
                # 期間内フィルタリング
                filtered = headlines[
                    (headlines['created_dt'] >= start_date) & 
                    (headlines['created_dt'] <= end_date)
                ]
                
                print(f"期間内記事: {len(filtered)}件")
                
                # フィルタリング結果の詳細
                if not filtered.empty:
                    print("期間内記事のサンプル:")
                    for i, (idx, row) in enumerate(filtered.head(3).iterrows()):
                        title = str(row['text'])[:50]
                        created = row['created_dt']
                        print(f"  [{i+1}] {created}: {title}...")
                else:
                    print("⚠️  期間内の記事が見つかりませんでした")
                    
                    # 最新記事がいつのものかチェック
                    if not all_dates.empty:
                        latest_article = all_dates.max()
                        hours_ago = (end_date - latest_article).total_seconds() / 3600
                        print(f"最新記事は {hours_ago:.1f} 時間前")
                        
    except Exception as e:
        print(f"エラー: {e}")

def test_query_variations():
    """クエリバリエーションテスト"""
    print("\n🔍 クエリバリエーションテスト")
    
    # 設定読み込み
    with open('config_spec.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    ek.set_app_key(config["eikon_api_key"])
    
    # LME関連の様々なクエリ
    lme_queries = [
        "copper",
        "copper price", 
        "copper market",
        "LME copper",
        "London Metal Exchange",
        "base metals",
        "industrial metals",
        "metals market"
    ]
    
    print("LME関連クエリテスト（過去6時間以内の記事数）:")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=6)
    
    for query in lme_queries:
        try:
            headlines = ek.get_news_headlines(query, count=50)
            
            if headlines is not None and not headlines.empty:
                # 期間内フィルタリング
                if 'versionCreated' in headlines.columns:
                    headlines['created_dt'] = pd.to_datetime(headlines['versionCreated'], errors='coerce')
                    recent = headlines[
                        (headlines['created_dt'] >= start_date) & 
                        (headlines['created_dt'] <= end_date)
                    ]
                    recent_count = len(recent)
                else:
                    recent_count = "日付不明"
            else:
                recent_count = 0
                
            print(f"  '{query}': {recent_count}件")
            
        except Exception as e:
            print(f"  '{query}': エラー - {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("LME News Collector - ニュース収集検証テスト")
    print("=" * 60)
    
    test_basic_api()
    test_date_filtering()
    test_query_variations()
    
    print("\n" + "=" * 60)
    print("テスト完了")