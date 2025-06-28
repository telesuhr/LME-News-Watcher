#!/usr/bin/env python3
"""
仕様書対応ニュース収集システム
Refinitiv EIKON APIからLME非鉄金属・市場ニュースを取得してデータベースに保存
"""

import eikon as ek
import json
import logging
import time
import re
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path

from models_spec import NewsArticle, SystemStats, extract_related_metals
from database_spec import SpecDatabaseManager
from gemini_analyzer import GeminiNewsAnalyzer

class RefinitivNewsCollector:
    """Refinitivニュース収集器（仕様書準拠）"""
    
    def __init__(self, config_path: str = "config_spec.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルパス
        """
        self.config = self._load_config(config_path)
        self.logger = self._setup_logger()
        self.db_manager = SpecDatabaseManager(self.config["database"])
        
        # Gemini分析器初期化
        self.gemini_analyzer = GeminiNewsAnalyzer(self.config)
        
        # 統計カウンター
        self.stats = {
            'successful_queries': 0,
            'failed_queries': 0,
            'api_calls_made': 0,
            'errors_encountered': 0,
            'total_collected': 0,
            'ai_analyzed': 0,
            'ai_analysis_errors': 0
        }
        
        # 重複チェック用キャッシュ
        self.existing_news_ids: Set[str] = set()
        
        # EIKON API初期化
        try:
            ek.set_app_key(self.config["eikon_api_key"])
            self.logger.info("Refinitiv EIKON API初期化完了")
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
        logger = logging.getLogger('RefinitivNewsCollector')
        logger.setLevel(getattr(logging, self.config["logging"]["log_level"]))
        
        # ログディレクトリ作成
        log_dir = Path(self.config["logging"]["log_directory"])
        log_dir.mkdir(exist_ok=True)
        
        # ファイルハンドラー設定
        log_file = log_dir / f"refinitiv_news_{datetime.now().strftime('%Y%m%d')}.log"
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
    
    def _load_existing_news_ids(self):
        """既存ニュースID読み込み（重複チェック用）"""
        try:
            days_back = self.config["news_collection"]["duplicate_check_days"]
            self.existing_news_ids = set(self.db_manager.get_duplicate_news_ids(days_back))
            self.logger.info(f"重複チェック用ID読み込み完了: {len(self.existing_news_ids)} 件")
        except Exception as e:
            self.logger.warning(f"既存ID読み込み警告: {e}")
            self.existing_news_ids = set()
    
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
    
    def _extract_url_from_story(self, story_id: str) -> Optional[str]:
        """ストーリーIDからURL抽出"""
        try:
            # Refinitivのニュース詳細取得
            story = ek.get_news_story(story_id)
            if story and hasattr(story, 'get'):
                # URL情報があれば取得
                url = story.get('url') or story.get('link')
                return url
        except Exception as e:
            self.logger.debug(f"URL取得エラー: {story_id} - {e}")
        
        return None
    
    def _get_news_by_query(self, query: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """クエリによるニュース取得"""
        try:
            self.logger.debug(f"ニュース取得開始: {query}")
            
            # API呼び出し
            headlines = ek.get_news_headlines(
                query=query,
                count=self.config["news_collection"]["max_news_per_query"],
                date_from=start_date.strftime('%Y-%m-%d'),
                date_to=end_date.strftime('%Y-%m-%d')
            )
            
            self.stats['api_calls_made'] += 1
            
            if headlines is None or headlines.empty:
                self.logger.debug(f"ニュースが見つかりませんでした: {query}")
                return []
            
            news_items = []
            for idx, row in headlines.iterrows():
                try:
                    # 基本情報取得（エラーの原因を特定するため最小限に）
                    story_id = str(row.get('storyId', ''))
                    headline = self._clean_text(str(row.get('text', '')))
                    source = str(row.get('sourceCode', ''))
                    
                    # 既存チェック（重複除去）
                    if story_id in self.existing_news_ids:
                        continue
                    
                    # 日付処理（簡略化してエラー回避）
                    try:
                        version_created = row.get('versionCreated')
                        
                        if version_created is not None:
                            # まずpandas Timestampへの変換を試す
                            if hasattr(pd, 'to_datetime'):
                                ts = pd.to_datetime(version_created, errors='coerce')
                                if not pd.isna(ts):
                                    publish_time = ts.to_pydatetime()
                                else:
                                    publish_time = datetime.now()
                            else:
                                # フォールバック: 文字列として処理
                                date_str = str(version_created)
                                if 'T' in date_str and 'Z' in date_str:
                                    publish_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    publish_time = datetime.now()
                        else:
                            publish_time = datetime.now()
                    except Exception as e:
                        self.logger.debug(f"日付変換エラー (フォールバック): {e}")
                        publish_time = datetime.now()
                    
                    # 除外ソースチェック
                    excluded_sources = self.config["news_collection"]["excluded_sources"]
                    if source.upper() in [s.upper() for s in excluded_sources]:
                        continue
                    
                    # 本文取得
                    body = ""
                    url = None
                    if story_id:
                        try:
                            story = ek.get_news_story(story_id)
                            self.stats['api_calls_made'] += 1
                            
                            if story:
                                # 辞書形式の場合
                                if isinstance(story, dict):
                                    body = self._clean_text(story.get('storyHtml', '') or story.get('story', '') or story.get('text', ''))
                                    url = story.get('url') or story.get('link')
                                # 文字列の場合
                                elif isinstance(story, str):
                                    body = self._clean_text(story)
                                # その他の形式
                                else:
                                    body = self._clean_text(str(story))
                                    
                            time.sleep(0.1)  # API制限対策
                        except Exception as e:
                            self.logger.debug(f"本文取得エラー: {story_id} - {e}")
                            # エラーの場合はヘッドラインを本文として使用
                            body = headline
                    
                    # 関連金属抽出
                    related_metals = extract_related_metals(headline, body)
                    
                    # LME関連フィルタリング
                    if self.config["news_collection"]["lme_only_filter"]:
                        if not self._is_lme_related(headline, body, related_metals):
                            continue
                    
                    news_item = {
                        'story_id': story_id,
                        'headline': headline,
                        'body': body,
                        'source': source,
                        'publish_time': publish_time,
                        'url': url,
                        'related_metals': related_metals,
                        'query': query
                    }
                    
                    news_items.append(news_item)
                    
                    # 重複チェック用に追加
                    self.existing_news_ids.add(story_id)
                    
                except Exception as e:
                    self.logger.warning(f"ニュースアイテム処理エラー: {e}")
                    continue
            
            # API制限対策
            time.sleep(self.config["news_collection"]["api_rate_limit_delay"])
            
            self.logger.info(f"クエリ '{query}' で {len(news_items)} 件のニュースを取得")
            self.stats['successful_queries'] += 1
            return news_items
            
        except Exception as e:
            self.logger.error(f"ニュース取得エラー: {query} - {e}")
            self.stats['failed_queries'] += 1
            self.stats['errors_encountered'] += 1
            return []
    
    def _is_lme_related(self, headline: str, body: str, related_metals: str) -> bool:
        """LME関連ニュースかどうか判定"""
        text = f"{headline} {body}".lower()
        
        # LME関連キーワード
        lme_keywords = self.config["news_collection"]["lme_keywords"]
        for keyword in lme_keywords:
            if keyword.lower() in text:
                return True
        
        # 金属関連チェック
        if related_metals:
            return True
        
        # 市場関連キーワード
        market_keywords = self.config["news_collection"]["market_keywords"]
        for keyword in market_keywords:
            if keyword.lower() in text:
                return True
        
        return False
    
    def _get_collection_period(self) -> tuple[datetime, datetime]:
        """収集期間計算"""
        end_date = datetime.now()
        hours_back = self.config["news_collection"]["collection_period_hours"]
        start_date = end_date - timedelta(hours=hours_back)
        return start_date, end_date
    
    def collect_historical_news(self, months_back: int = 3) -> int:
        """過去数ヶ月のニュース一括収集"""
        start_time = datetime.now()
        self.logger.info(f"過去{months_back}ヶ月のニュース一括収集開始")
        
        try:
            # 収集期間計算（数ヶ月）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back * 30)
            self.logger.info(f"収集期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
            
            # 既存ニュースID読み込み
            self._load_existing_news_ids()
            
            all_news = []
            
            # 基本的なクエリのみ使用（エラーが起きにくいもの）
            basic_queries = [
                "copper",
                "aluminium", 
                "zinc",
                "lead",
                "nickel",
                "tin",
                "LME",
                "metals",
                "commodity",
                "mining"
            ]
            
            for query in basic_queries:
                self.logger.info(f"クエリ '{query}' の収集開始")
                
                try:
                    # API制限を考慮して小分けして取得
                    current_start = start_date
                    while current_start < end_date:
                        current_end = min(current_start + timedelta(days=7), end_date)
                        
                        self.logger.info(f"期間: {current_start.strftime('%Y-%m-%d')} - {current_end.strftime('%Y-%m-%d')}")
                        
                        try:
                            news_items = self._get_news_by_query(query, current_start, current_end)
                            all_news.extend(news_items)
                            self.logger.info(f"取得: {len(news_items)} 件")
                            
                            # API制限対策
                            time.sleep(2)
                            
                        except Exception as e:
                            self.logger.warning(f"期間別取得エラー: {e}")
                            continue
                        
                        current_start = current_end
                        
                    # クエリ間の間隔
                    time.sleep(3)
                    
                except Exception as e:
                    self.logger.error(f"クエリ '{query}' エラー: {e}")
                    continue
            
            # データベース保存
            saved_count = 0
            if all_news:
                self.logger.info(f"データベース保存開始: {len(all_news)} 件")
                
                # 重複除去
                unique_news = {}
                for item in all_news:
                    story_id = item.get('story_id', '')
                    if story_id and story_id not in unique_news:
                        unique_news[story_id] = item
                
                self.logger.info(f"重複除去後: {len(unique_news)} 件")
                
                # NewsArticleオブジェクトに変換
                news_articles = []
                current_time = datetime.now()
                
                for item in unique_news.values():
                    try:
                        article = NewsArticle(
                            news_id=item['story_id'],
                            title=item['headline'],
                            body=item['body'],
                            publish_time=item['publish_time'],
                            acquire_time=current_time,
                            source=item['source'],
                            url=item.get('url'),
                            related_metals=item.get('related_metals'),
                            is_manual=False
                        )
                        news_articles.append(article)
                    except Exception as e:
                        self.logger.warning(f"記事変換エラー: {e}")
                        continue
                
                # バッチ保存
                saved_count = self.db_manager.insert_news_batch(news_articles)
                self.stats['total_collected'] = saved_count
            
            # 統計保存
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.info(f"一括収集完了: {saved_count} 件保存、実行時間: {execution_time:.2f}秒")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"一括収集エラー: {e}")
            return 0
    
    def collect_news(self) -> int:
        """メインニュース収集処理"""
        start_time = datetime.now()
        self.logger.info("Refinitivニュース収集開始")
        
        try:
            # 既存ニュースID読み込み
            self._load_existing_news_ids()
            
            # 収集期間計算
            start_date, end_date = self._get_collection_period()
            self.logger.info(f"収集期間: {start_date.strftime('%Y-%m-%d %H:%M')} - {end_date.strftime('%Y-%m-%d %H:%M')}")
            
            all_news = []
            
            # 設定されたクエリで収集
            query_categories = self.config["news_collection"]["query_categories"]
            
            for category, queries in query_categories.items():
                self.logger.info(f"カテゴリ '{category}' の収集開始")
                
                for query in queries:
                    news_items = self._get_news_by_query(query, start_date, end_date)
                    all_news.extend(news_items)
                    
                    # API制限対策
                    time.sleep(self.config["news_collection"]["query_interval"])
            
            # データベース保存とAI分析
            saved_count = 0
            if all_news:
                news_articles = []
                current_time = datetime.now()
                
                # ニュース記事オブジェクト作成
                for item in all_news:
                    article = NewsArticle(
                        news_id=item['story_id'],
                        title=item['headline'],
                        body=item['body'],
                        publish_time=item['publish_time'],
                        acquire_time=current_time,
                        source=item['source'],
                        url=item.get('url'),
                        related_metals=item.get('related_metals'),
                        is_manual=False
                    )
                    news_articles.append(article)
                
                # データベース保存
                saved_count = self.db_manager.insert_news_batch(news_articles)
                self.stats['total_collected'] = saved_count
                
                # AI分析実行（非同期）
                if self.gemini_analyzer.gemini_config.get("enable_ai_analysis", False):
                    try:
                        self.logger.info(f"AI分析開始: {len(news_articles)} 件")
                        asyncio.run(self._analyze_news_batch(news_articles))
                    except Exception as e:
                        self.logger.error(f"AI分析エラー: {e}")
                        self.stats['ai_analysis_errors'] += 1
            
            # 統計保存
            execution_time = (datetime.now() - start_time).total_seconds()
            stats = SystemStats(
                collection_date=datetime.now(),
                total_collected=saved_count,
                successful_queries=self.stats['successful_queries'],
                failed_queries=self.stats['failed_queries'],
                api_calls_made=self.stats['api_calls_made'],
                errors_encountered=self.stats['errors_encountered'],
                execution_time_seconds=execution_time
            )
            
            self.db_manager.insert_system_stats(stats)
            
            self.logger.info(f"ニュース収集完了: {saved_count} 件保存、実行時間: {execution_time:.2f}秒")
            return saved_count
            
        except Exception as e:
            self.logger.error(f"ニュース収集エラー: {e}")
            self.stats['errors_encountered'] += 1
            return 0
    
    async def _analyze_news_batch(self, news_articles: List[NewsArticle]):
        """ニュース一括AI分析"""
        try:
            # NewsArticleをDict形式に変換
            news_dicts = []
            for article in news_articles:
                news_dict = {
                    'news_id': article.news_id,
                    'title': article.title,
                    'body': article.body,
                    'source': article.source,
                    'publish_time': article.publish_time,
                    'related_metals': article.related_metals
                }
                news_dicts.append(news_dict)
            
            # AI分析実行
            analysis_results = await self.gemini_analyzer.analyze_news_batch(news_dicts)
            
            # 分析結果をデータベースに更新
            for news_id, result in analysis_results:
                try:
                    self.db_manager.update_news_analysis(news_id, {
                        'summary': result.summary,
                        'sentiment': result.sentiment,
                        'keywords': result.keywords,
                        'importance_score': result.importance_score
                    })
                    self.stats['ai_analyzed'] += 1
                except Exception as e:
                    self.logger.error(f"分析結果更新エラー {news_id}: {e}")
            
            self.logger.info(f"AI分析完了: {len(analysis_results)} 件")
            
        except Exception as e:
            self.logger.error(f"AI分析バッチエラー: {e}")
            self.stats['ai_analysis_errors'] += 1
    
    def get_collection_status(self) -> Dict:
        """収集状況取得"""
        base_stats = {
            'successful_queries': self.stats['successful_queries'],
            'failed_queries': self.stats['failed_queries'],
            'api_calls_made': self.stats['api_calls_made'],
            'errors_encountered': self.stats['errors_encountered'],
            'total_collected': self.stats['total_collected'],
            'existing_news_count': len(self.existing_news_ids),
            'ai_analyzed': self.stats['ai_analyzed'],
            'ai_analysis_errors': self.stats['ai_analysis_errors']
        }
        
        # Gemini分析統計を追加
        if hasattr(self, 'gemini_analyzer'):
            gemini_stats = self.gemini_analyzer.get_analysis_stats()
            base_stats['gemini_analysis'] = gemini_stats
        
        return base_stats

class NewsPollingService:
    """ニュースポーリングサービス"""
    
    def __init__(self, config_path: str = "config_spec.json"):
        """初期化"""
        self.collector = RefinitivNewsCollector(config_path)
        self.config = self.collector.config
        self.logger = self.collector.logger
        self.is_running = False
    
    def start_polling(self):
        """ポーリング開始"""
        self.is_running = True
        self.logger.info("ニュースポーリング開始")
        
        while self.is_running:
            try:
                # ニュース収集実行
                collected_count = self.collector.collect_news()
                self.logger.info(f"ポーリング実行完了: {collected_count} 件収集")
                
                # 次回実行まで待機
                polling_interval = self.config["news_collection"]["polling_interval_minutes"]
                self.logger.info(f"次回実行まで {polling_interval} 分待機")
                
                for i in range(polling_interval * 60):  # 秒単位で待機
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                self.logger.info("ユーザーによる中断")
                break
            except Exception as e:
                self.logger.error(f"ポーリングエラー: {e}")
                time.sleep(60)  # エラー時は1分待機
        
        self.logger.info("ニュースポーリング終了")
    
    def stop_polling(self):
        """ポーリング停止"""
        self.is_running = False
        self.logger.info("ポーリング停止要求")

def main():
    """メイン実行関数"""
    try:
        collector = RefinitivNewsCollector()
        
        # データベース接続テスト
        if not collector.db_manager.test_connection():
            print("データベース接続エラー。設定を確認してください。")
            return
        
        # ニュース収集実行
        saved_count = collector.collect_news()
        print(f"ニュース収集完了: {saved_count} 件保存")
        
        # 収集状況表示
        status = collector.get_collection_status()
        print(f"実行統計: {status}")
        
    except Exception as e:
        print(f"実行エラー: {e}")

if __name__ == "__main__":
    main()