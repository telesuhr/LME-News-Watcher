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
import warnings
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from pathlib import Path

# pandas/numpy datetime64 問題を回避するための設定
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
pd.set_option('mode.chained_assignment', None)

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
        self.db_manager = SpecDatabaseManager(self.config)
        
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
        
        # エラー抑制用（同じエラーの重複を防ぐ）
        self.recent_errors: Dict[str, datetime] = {}
        self.error_cooldown_minutes = 5
        
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
    
    def _safe_datetime_convert(self, dt_value) -> datetime:
        """安全なdatetime変換（datetime64エラー対応）"""
        if dt_value is None:
            return datetime.now()
        
        try:
            # pandas Timestampの場合
            if hasattr(dt_value, 'to_pydatetime'):
                return dt_value.to_pydatetime()
            
            # numpy datetime64の場合（unit指定で安全変換）
            elif hasattr(dt_value, 'astype') and 'datetime64' in str(type(dt_value)):
                # datetime64をTimestampに変換してからdatetimeに
                ts = pd.Timestamp(dt_value)
                return ts.to_pydatetime()
            
            # 文字列の場合
            elif isinstance(dt_value, str):
                if 'T' in dt_value:
                    if dt_value.endswith('Z'):
                        return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                    else:
                        return datetime.fromisoformat(dt_value.split('+')[0].split('Z')[0])
                else:
                    return pd.to_datetime(dt_value, errors='coerce').to_pydatetime()
            
            # その他の型（pandas to_datetimeで変換）
            else:
                result = pd.to_datetime(dt_value, errors='coerce', unit='ns')
                if pd.isna(result):
                    return datetime.now()
                return result.to_pydatetime()
                
        except Exception:
            # 全ての変換が失敗した場合は現在時刻を返す
            return datetime.now()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('RefinitivNewsCollector')
        
        # 既存のハンドラーを削除（重複を防ぐ）
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        logger.setLevel(getattr(logging, self.config["logging"]["log_level"]))
        
        # 親ロガーからの伝播を防ぐ
        logger.propagate = False
        
        # ログディレクトリ作成
        log_dir = Path(self.config["logging"]["log_directory"])
        log_dir.mkdir(exist_ok=True)
        
        # ファイルハンドラー設定（全レベル）
        log_file = log_dir / f"refinitiv_news_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # コンソールハンドラー（WARNINGレベル以上のみ - より静か）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # ERRORからWARNINGに緩和
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')  # よりシンプル
        console_handler.setFormatter(console_formatter)
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
        """クエリによるニュース取得 - datetime64エラー完全対応版"""
        try:
            self.logger.debug(f"ニュース取得開始: {query}")
            
            # 安全性チェック
            if not self._is_safe_query(query):
                self.logger.debug(f"危険なクエリをスキップ: {query}")
                return []
            
            # datetime64エラー対策：日付パラメータを使わずに取得
            # EIKON APIの日付パラメータがdatetime64エラーの根本原因のため完全に回避
            try:
                # API制限を考慮して安全な件数に制限
                safe_count = min(self.config["news_collection"]["max_news_per_query"], 20)
                headlines = ek.get_news_headlines(
                    query=query,
                    count=safe_count
                )
                
                # クライアントサイドで日付フィルタリング
                if headlines is not None and not headlines.empty:
                    headlines = self._filter_headlines_by_date(headlines, start_date, end_date)
                    self.logger.debug(f"クライアントサイドフィルタリング完了: {query} - {len(headlines)} 件")
                else:
                    headlines = pd.DataFrame()
                    
            except Exception as api_error:
                error_key = f"query_failed_{query}"
                if self._should_log_error(error_key):
                    self.logger.error(f"ニュース取得失敗: {query} (全手法失敗)")
                return []
            
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
                    
                    # 日付処理（最適化版）
                    publish_time = self._safe_datetime_convert(row.get('versionCreated'))
                    
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
                    self.logger.debug(f"ニュースアイテム処理スキップ: {e}")
                    continue
            
            # API制限対策
            time.sleep(self.config["news_collection"]["api_rate_limit_delay"])
            
            self._log_successful_query(query, len(news_items))
            self.stats['successful_queries'] += 1
            return news_items
            
        except Exception as e:
            # エラー抑制機能を使用してログ出力を制御
            if not datetime64_retry_attempted:
                error_key = f"general_error_{query}_{type(e).__name__}"
                if self._should_log_error(error_key):
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
    
    def _get_collection_period(self, collection_mode: str = "background") -> tuple[datetime, datetime]:
        """収集期間計算"""
        end_date = datetime.now()
        
        if collection_mode == "manual":
            # 手動収集の場合は短い期間を使用
            hours_back = self.config["news_collection"].get("manual_collection_period_hours", 2)
            self.logger.info(f"手動収集モード: 過去{hours_back}時間のニュースを収集")
        else:
            # バックグラウンド収集の場合は通常期間
            hours_back = self.config["news_collection"]["collection_period_hours"]
            self.logger.info(f"バックグラウンド収集モード: 過去{hours_back}時間のニュースを収集")
        
        start_date = end_date - timedelta(hours=hours_back)
        return start_date, end_date
    
    def _is_safe_query(self, query: str) -> bool:
        """
        クエリが安全（datetime64エラーを起こさない）かどうかをチェック
        """
        # 問題が確認されているクエリパターン
        problematic_patterns = [
            "LME",
            "london metal exchange",
            "lme prices",
            "lme warehouse", 
            "lme stocks",
            "lme trading",
            "lme copper",
            "lme aluminium",
            "lme zinc",
            "lme lead", 
            "lme nickel",
            "lme tin",
            "metal production",
            "metal demand",
            "mining strike",
            "trade war metals"
        ]
        
        query_lower = query.lower()
        for pattern in problematic_patterns:
            if pattern.lower() in query_lower:
                return False
        
        return True
    
    def _optimize_query(self, query: str) -> Optional[str]:
        """
        クエリの最適化・問題クエリの代替
        
        Args:
            query: 元のクエリ
            
        Returns:
            最適化されたクエリまたはNone（スキップ）
        """
        # 既知の問題クエリとその代替
        query_replacements = {
            'metal inventory': 'metals inventory',  # より一般的な表現
            'metal stockpile': 'metals stockpile',
            'metal market': 'metals market',
            'metal production': 'metals production'
        }
        
        # 問題クエリのスキップリスト
        skip_queries = [
            # 特に問題があることがわかったクエリ
        ]
        
        query_lower = query.lower()
        
        # スキップ対象チェック
        if query_lower in [q.lower() for q in skip_queries]:
            return None
        
        # 代替クエリチェック
        for original, replacement in query_replacements.items():
            if query_lower == original.lower():
                self.logger.debug(f"クエリ最適化: '{query}' -> '{replacement}'")
                return replacement
        
        return query
    
    def _should_log_error(self, error_key: str) -> bool:
        """
        エラーログを出力するべきかチェック（重複抑制）
        
        Args:
            error_key: エラーの識別キー
            
        Returns:
            ログ出力するべきかどうか
        """
        now = datetime.now()
        
        # 過去のエラーをクリーンアップ（古いものを削除）
        expired_keys = [
            key for key, timestamp in self.recent_errors.items()
            if (now - timestamp).total_seconds() > self.error_cooldown_minutes * 60
        ]
        for key in expired_keys:
            del self.recent_errors[key]
        
        # 同じエラーが最近出力されたかチェック
        if error_key in self.recent_errors:
            time_since_last = (now - self.recent_errors[error_key]).total_seconds()
            if time_since_last < self.error_cooldown_minutes * 60:
                return False  # 最近同じエラーが出力されているのでスキップ
        
        # エラーを記録
        self.recent_errors[error_key] = now
        return True
    
    def _log_successful_query(self, query: str, count: int) -> None:
        """成功したクエリをログ記録"""
        if count > 0:
            self.logger.info(f"クエリ '{query}' で {count} 件のニュースを取得")
        else:
            self.logger.debug(f"クエリ '{query}' ではニュースが見つかりませんでした")
    
    def _filter_headlines_by_date(self, headlines: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        ヘッドラインを日付範囲でフィルタリング（クライアントサイド）
        
        Args:
            headlines: 生のヘッドラインDataFrame
            start_date: 開始日時
            end_date: 終了日時
            
        Returns:
            フィルタリングされたDataFrame
        """
        if headlines.empty:
            return headlines
            
        try:
            # 日付カラムを特定
            date_column = None
            for col in headlines.columns:
                if 'versionCreated' in col or 'created' in col.lower() or 'date' in col.lower():
                    date_column = col
                    break
            
            if date_column is None:
                self.logger.debug("日付カラムが見つからないため、フィルタリングをスキップ")
                return headlines
            
            # 日付をdatetimeに変換（最適化版）
            filtered_headlines = []
            for idx, row in headlines.iterrows():
                try:
                    date_value = row[date_column]
                    publish_time = self._safe_datetime_convert(date_value)
                    
                    # 日付範囲チェック
                    if start_date <= publish_time <= end_date:
                        filtered_headlines.append(row)
                        
                except Exception as e:
                    self.logger.debug(f"日付フィルタリングエラー: {e}")
                    # エラーの場合は含める
                    filtered_headlines.append(row)
            
            if filtered_headlines:
                return pd.DataFrame(filtered_headlines)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.logger.debug(f"日付フィルタリング処理エラー: {e}")
            # エラーの場合は元のデータを返す
            return headlines
    
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
    
    def collect_news(self, collection_mode: str = "background") -> int:
        """
        メインニュース収集処理
        
        Args:
            collection_mode: "manual" or "background"
        """
        start_time = datetime.now()
        self.logger.info("Refinitivニュース収集開始")
        
        try:
            # 既存ニュースID読み込み
            self._load_existing_news_ids()
            
            # 収集期間計算
            start_date, end_date = self._get_collection_period(collection_mode)
            self.logger.info(f"収集期間: {start_date.strftime('%Y-%m-%d %H:%M')} - {end_date.strftime('%Y-%m-%d %H:%M')}")
            
            all_news = []
            
            # 収集モードに応じてクエリを選択
            query_categories = self.config["news_collection"]["query_categories"]
            
            if collection_mode == "manual":
                # 手動収集時は優先度の高いクエリのみを使用（高速化）
                priority_categories = ["lme_metals", "base_metals"]
                filtered_categories = {k: v for k, v in query_categories.items() if k in priority_categories}
                self.logger.info(f"手動収集モード: 優先カテゴリのみ使用 ({', '.join(priority_categories)})")
            else:
                # バックグラウンド収集時は全カテゴリを使用
                filtered_categories = query_categories
                self.logger.info("バックグラウンド収集モード: 全カテゴリ使用")
            
            for category, queries in filtered_categories.items():
                self.logger.info(f"カテゴリ '{category}' の収集開始")
                
                category_failed_count = 0
                for query in queries:
                    # 既知の問題クエリをスキップまたは代替
                    optimized_query = self._optimize_query(query)
                    if optimized_query is None:
                        self.logger.debug(f"問題クエリをスキップ: {query}")
                        continue
                    
                    try:
                        news_items = self._get_news_by_query(optimized_query, start_date, end_date)
                        all_news.extend(news_items)
                    except Exception:
                        category_failed_count += 1
                        # 個別エラーログは_get_news_by_queryで抑制済み
                        continue
                    
                    # API制限対策（手動モード時は短縮）
                    if collection_mode == "manual":
                        # 手動収集時は短いインターバル
                        time.sleep(self.config["news_collection"].get("query_interval", 1.0) * 0.3)
                    else:
                        # バックグラウンド収集時は通常インターバル
                        time.sleep(self.config["news_collection"]["query_interval"])
                
                # カテゴリ単位のサマリーログ
                if category_failed_count > 0:
                    self.logger.debug(f"カテゴリ '{category}': {category_failed_count}/{len(queries)} クエリ失敗")
            
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
                
                # AI分析実行（手動収集時はスキップして高速化）
                if collection_mode == "background" and self.gemini_analyzer.gemini_config.get("enable_ai_analysis", False):
                    try:
                        self.logger.info(f"AI分析開始: {len(news_articles)} 件")
                        asyncio.run(self._analyze_news_batch(news_articles))
                    except Exception as e:
                        self.logger.error(f"AI分析エラー: {e}")
                        self.stats['ai_analysis_errors'] += 1
                elif collection_mode == "manual":
                    self.logger.info("手動収集モード: AI分析をスキップ（高速化のため）")
            
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
            
            # 統計サマリー表示
            total_queries = self.stats['successful_queries'] + self.stats['failed_queries']
            success_rate = (self.stats['successful_queries'] / total_queries * 100) if total_queries > 0 else 0
            
            # 重要な完了メッセージはコンソールにも表示（WARNING以上）
            if saved_count > 0:
                self.logger.warning(f"✓ ニュース収集完了: {saved_count} 件保存、実行時間: {execution_time:.2f}秒")
            else:
                self.logger.info(f"ニュース収集完了: {saved_count} 件保存、実行時間: {execution_time:.2f}秒")
            
            self.logger.info(f"統計: 成功クエリ {self.stats['successful_queries']}/{total_queries} ({success_rate:.1f}%), API呼び出し {self.stats['api_calls_made']} 回")
            
            # エラー率が高い場合のみ警告
            if total_queries > 0 and success_rate < 70:
                self.logger.warning(f"クエリ成功率が低下しています ({success_rate:.1f}%) - API状態を確認してください")
            
            # エラーサマリー表示（個別エラーの代わり）
            if self.stats['failed_queries'] > 0:
                self.logger.warning(f"一部クエリが失敗しました: {self.stats['failed_queries']} 件（詳細はログファイルを確認）")
            
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
        if hasattr(self, 'gemini_analyzer') and self.gemini_analyzer:
            try:
                gemini_stats = self.gemini_analyzer.get_analysis_stats()
                base_stats['gemini_analysis'] = gemini_stats
            except Exception as e:
                self.logger.error(f"Gemini統計取得エラー: {e}")
                base_stats['gemini_analysis'] = {'error': str(e)}
        
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