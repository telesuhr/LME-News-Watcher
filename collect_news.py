#!/usr/bin/env python3
"""
金属市場ニュース収集システム - メインモジュール
Refinitiv EIKON APIからニュースを取得してPostgreSQL/SQL Serverに保存
"""

import eikon as ek
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import os
from pathlib import Path
import re

from models import NewsItem, CollectionStats
from database import DatabaseManager

class NewsCollector:
    """金属市場ニュース収集器"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルパス
        """
        self.config = self._load_config(config_path)
        self.logger = self._setup_logger()
        self.db_manager = DatabaseManager(self.config["database"])
        
        # 統計カウンター
        self.stats = {
            'successful_queries': 0,
            'failed_queries': 0,
            'api_calls_made': 0,
            'errors_encountered': 0,
            'duplicate_removed': 0,
            'high_priority_count': 0,
            'medium_priority_count': 0,
            'low_priority_count': 0
        }
        
        # EIKON API初期化
        try:
            ek.set_app_key(self.config["eikon_api_key"])
            self.logger.info("EIKON API初期化完了")
        except Exception as e:
            self.logger.error(f"EIKON API初期化エラー: {e}")
            raise
    
    def _load_config(self, config_path: str) -> Dict:
        """設定ファイル読み込み"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"設定ファイル読み込みエラー: {e}")
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('NewsCollector')
        logger.setLevel(getattr(logging, self.config["logging"]["log_level"]))
        
        # ログディレクトリ作成
        log_dir = Path(self.config["logging"]["log_directory"])
        log_dir.mkdir(exist_ok=True)
        
        # ファイルハンドラー設定
        log_file = log_dir / f"news_collector_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_collection_period(self) -> tuple[datetime, datetime]:
        """収集期間計算"""
        end_date = datetime.now()
        days_back = self.config["news_settings"]["collection_period_days"]
        
        business_days_collected = 0
        start_date = end_date
        
        while business_days_collected < days_back:
            start_date = start_date - timedelta(days=1)
            if start_date.weekday() < 5:  # 平日のみ
                business_days_collected += 1
        
        return start_date, end_date
    
    def _calculate_priority_score(self, headline: str, source: str, published_date: datetime) -> int:
        """優先度スコア計算"""
        score = 0
        headline_lower = headline.lower()
        
        # 高優先度キーワード（+20点）
        high_priority = self.config["news_settings"]["priority_keywords"]["high_priority"]
        for keyword in high_priority:
            if keyword.lower() in headline_lower:
                score += 20
                break
        
        # 中優先度キーワード（+10点）
        medium_priority = self.config["news_settings"]["priority_keywords"]["medium_priority"]
        for keyword in medium_priority:
            if keyword.lower() in headline_lower:
                score += 10
                break
        
        # ソース信頼性（+5点）
        reliable_sources = self.config["news_settings"]["reliable_sources"]
        if source.upper() in [s.upper() for s in reliable_sources]:
            score += 5
        
        # 時間の新しさ（最大+15点）
        hours_ago = (datetime.now() - published_date).total_seconds() / 3600
        if hours_ago <= 6:
            score += 15
        elif hours_ago <= 12:
            score += 10
        elif hours_ago <= 24:
            score += 5
        elif hours_ago <= 48:
            score += 2
        
        return score
    
    def _extract_keywords(self, headline: str, body: str = "") -> List[str]:
        """キーワード抽出"""
        text = f"{headline} {body}".lower()
        keywords = []
        
        # 設定からキーワードを収集
        all_keywords = (
            self.config["news_settings"]["priority_keywords"]["high_priority"] +
            self.config["news_settings"]["priority_keywords"]["medium_priority"]
        )
        
        for keyword in all_keywords:
            if keyword.lower() in text:
                keywords.append(keyword)
        
        return list(set(keywords))  # 重複除去
    
    def _clean_text(self, text: str) -> str:
        """テキストクリーニング"""
        if not text:
            return ""
        
        # HTMLタグ除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 余分な空白除去
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 制御文字除去
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text
    
    def _get_news_by_query(self, query: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """クエリによるニュース取得"""
        try:
            self.logger.debug(f"ニュース取得開始: {query}")
            
            # API呼び出し
            headlines = ek.get_news_headlines(
                query=query,
                count=self.config["news_settings"]["max_news_per_query"],
                date_from=start_date.strftime('%Y-%m-%d'),
                date_to=end_date.strftime('%Y-%m-%d')
            )
            
            self.stats['api_calls_made'] += 1
            self.stats['successful_queries'] += 1
            
            if headlines is None or headlines.empty:
                self.logger.debug(f"ニュースが見つかりませんでした: {query}")
                return []
            
            news_items = []
            for _, row in headlines.iterrows():
                try:
                    # 基本情報取得
                    story_id = str(row.get('storyId', ''))
                    headline = self._clean_text(str(row.get('text', '')))
                    source = str(row.get('sourceCode', ''))
                    
                    # 日付処理
                    date_str = str(row.get('versionCreated', ''))
                    try:
                        published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        published_date = datetime.now()
                    
                    # 除外ソースチェック
                    excluded_sources = self.config["news_settings"]["excluded_sources"]
                    if source.upper() in [s.upper() for s in excluded_sources]:
                        continue
                    
                    # 本文取得（設定により）
                    body = ""
                    if self.config["news_settings"]["include_news_body"] and story_id:
                        try:
                            story = ek.get_news_story(story_id)
                            if story and hasattr(story, 'get'):
                                body = self._clean_text(story.get('storyHtml', ''))[:2000]
                            self.stats['api_calls_made'] += 1
                            time.sleep(0.05)  # API制限対策
                        except Exception as e:
                            self.logger.debug(f"本文取得エラー: {story_id} - {e}")
                    
                    # 優先度スコア計算
                    priority_score = self._calculate_priority_score(headline, source, published_date)
                    
                    # 最小優先度チェック
                    min_score = self.config["news_settings"]["minimum_priority_score"]
                    if priority_score < min_score:
                        continue
                    
                    # キーワード抽出
                    keywords = self._extract_keywords(headline, body)
                    
                    news_item = {
                        'story_id': story_id,
                        'headline': headline,
                        'source': source,
                        'published_date': published_date,
                        'body': body,
                        'priority_score': priority_score,
                        'keywords': keywords,
                        'query_type': query
                    }
                    
                    news_items.append(news_item)
                    
                    # 優先度統計更新
                    if priority_score >= 25:
                        self.stats['high_priority_count'] += 1
                    elif priority_score >= 15:
                        self.stats['medium_priority_count'] += 1
                    else:
                        self.stats['low_priority_count'] += 1
                    
                except Exception as e:
                    self.logger.warning(f"ニュースアイテム処理エラー: {e}")
                    continue
            
            # API制限対策
            time.sleep(self.config["news_settings"]["api_rate_limit_delay"])
            
            self.logger.info(f"クエリ '{query}' で {len(news_items)} 件のニュースを取得")
            return news_items
            
        except Exception as e:
            self.logger.error(f"ニュース取得エラー: {query} - {e}")
            self.stats['failed_queries'] += 1
            self.stats['errors_encountered'] += 1
            return []
    
    def _remove_duplicates(self, news_items: List[Dict]) -> List[Dict]:
        """重複除去"""
        if not self.config["news_settings"]["enable_duplicate_filtering"]:
            return news_items
        
        unique_items = []
        seen_ids = set()
        seen_headlines = set()
        
        for item in news_items:
            story_id = item['story_id']
            headline_key = item['headline'][:60].lower().strip()
            
            if story_id not in seen_ids and headline_key not in seen_headlines:
                unique_items.append(item)
                seen_ids.add(story_id)
                seen_headlines.add(headline_key)
            else:
                self.stats['duplicate_removed'] += 1
        
        self.logger.info(f"重複除去: {len(news_items)} → {len(unique_items)} 件")
        return unique_items
    
    def collect_news(self) -> int:
        """メインニュース収集処理"""
        start_time = datetime.now()
        self.logger.info("ニュース収集開始")
        
        try:
            # 収集期間計算
            start_date, end_date = self._get_collection_period()
            self.logger.info(f"収集期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
            
            all_news = []
            
            # カテゴリ別ニュース収集
            query_categories = self.config["news_settings"]["query_categories"]
            
            for category, queries in query_categories.items():
                self.logger.info(f"カテゴリ '{category}' の収集開始")
                
                for query in queries:
                    news_items = self._get_news_by_query(query, start_date, end_date)
                    all_news.extend(news_items)
            
            # 金属別ニュース収集
            target_metals = self.config["news_settings"]["target_metals"]
            for metal in target_metals:
                self.logger.info(f"金属 '{metal}' の収集開始")
                
                metal_queries = [
                    metal,
                    f"{metal} price",
                    f"{metal} LME",
                    f"{metal} market",
                    f"{metal} production"
                ]
                
                for query in metal_queries[:self.config["news_settings"]["max_queries_per_metal"]]:
                    news_items = self._get_news_by_query(query, start_date, end_date)
                    # 金属カテゴリを設定
                    for item in news_items:
                        item['metal_category'] = metal
                    all_news.extend(news_items)
            
            # 重複除去
            unique_news = self._remove_duplicates(all_news)
            
            # データベース保存
            saved_count = 0
            if unique_news:
                news_objects = []
                for item in unique_news:
                    news_obj = NewsItem(
                        story_id=item['story_id'],
                        headline=item['headline'],
                        source=item['source'],
                        published_date=item['published_date'],
                        body=item.get('body'),
                        priority_score=item['priority_score'],
                        metal_category=item.get('metal_category'),
                        keywords=item.get('keywords'),
                        query_type=item.get('query_type'),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    news_objects.append(news_obj)
                
                saved_count = self.db_manager.insert_news_batch(news_objects)
            
            # 統計保存
            execution_time = (datetime.now() - start_time).total_seconds()
            stats = CollectionStats(
                collection_date=datetime.now(),
                total_collected=saved_count,
                successful_queries=self.stats['successful_queries'],
                failed_queries=self.stats['failed_queries'],
                high_priority_count=self.stats['high_priority_count'],
                medium_priority_count=self.stats['medium_priority_count'],
                low_priority_count=self.stats['low_priority_count'],
                duplicate_removed=self.stats['duplicate_removed'],
                execution_time_seconds=execution_time,
                api_calls_made=self.stats['api_calls_made'],
                errors_encountered=self.stats['errors_encountered']
            )
            
            self.db_manager.insert_collection_stats(stats)
            
            self.logger.info(f"ニュース収集完了: {saved_count} 件保存、実行時間: {execution_time:.2f}秒")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"ニュース収集エラー: {e}")
            return 0

def main():
    """メイン実行関数"""
    try:
        collector = NewsCollector()
        
        # データベース接続テスト
        if not collector.db_manager.test_connection():
            print("データベース接続エラー。設定を確認してください。")
            return
        
        # ニュース収集実行
        saved_count = collector.collect_news()
        print(f"ニュース収集完了: {saved_count} 件保存")
        
    except Exception as e:
        print(f"実行エラー: {e}")

if __name__ == "__main__":
    main()