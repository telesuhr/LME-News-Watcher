#!/usr/bin/env python3
"""
LME News Watcher - UIアプリケーション
eelを使用したデスクトップアプリケーション
"""

import eel
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import sys
import os
from pathlib import Path

# モジュールインポート
from models_spec import NewsArticle, NewsSearchFilter, validate_manual_news_input, extract_related_metals
from database_spec import SpecDatabaseManager
from news_collector_spec import RefinitivNewsCollector, NewsPollingService

class NewsWatcherApp:
    """ニュースウォッチャーアプリケーション"""
    
    def __init__(self, config_path: str = "config_spec.json"):
        """初期化"""
        self.config_path = config_path
        self.config = self._load_config()
        self.db_manager = SpecDatabaseManager(self.config["database"])
        self.news_collector = None
        self.polling_service = None
        self.polling_thread = None
        self.is_polling_active = False
        
        # ログ設定
        self.logger = self._setup_logger()
        
        # eelアプリケーション設定
        eel.init('web')
        
    def _load_config(self) -> Dict:
        """設定ファイル読み込み"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"設定ファイル読み込みエラー: {e}")
            sys.exit(1)
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('NewsWatcherApp')
        logger.setLevel(logging.INFO)
        
        # ログディレクトリ作成
        log_dir = Path(self.config["logging"]["log_directory"])
        log_dir.mkdir(exist_ok=True)
        
        # ファイルハンドラー
        log_file = log_dir / f"news_watcher_app_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def start_background_polling(self):
        """バックグラウンドポーリング開始"""
        if self.is_polling_active:
            return
        
        try:
            self.news_collector = RefinitivNewsCollector(self.config_path)
            self.polling_service = NewsPollingService(self.config_path)
            
            self.polling_thread = threading.Thread(
                target=self._polling_worker,
                daemon=True
            )
            self.polling_thread.start()
            self.is_polling_active = True
            
            self.logger.info("バックグラウンドポーリング開始")
            
        except Exception as e:
            self.logger.error(f"ポーリング開始エラー: {e}")
    
    def _polling_worker(self):
        """ポーリングワーカー"""
        while self.is_polling_active:
            try:
                # ニュース収集実行
                collected_count = self.news_collector.collect_news()
                self.logger.info(f"バックグラウンド収集: {collected_count} 件")
                
                # 次回実行まで待機
                polling_interval = self.config["news_collection"]["polling_interval_minutes"]
                for i in range(polling_interval * 60):
                    if not self.is_polling_active:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"ポーリングエラー: {e}")
                time.sleep(60)  # エラー時は1分待機
    
    def stop_background_polling(self):
        """バックグラウンドポーリング停止"""
        self.is_polling_active = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        self.logger.info("バックグラウンドポーリング停止")
    
    def run(self):
        """アプリケーション実行"""
        try:
            # データベース接続テスト
            if not self.db_manager.test_connection():
                print("データベース接続エラー")
                return
            
            # テーブル作成
            self.db_manager.create_tables()
            
            # バックグラウンドポーリング開始
            self.start_background_polling()
            
            # UI開始
            self.logger.info("UIアプリケーション開始")
            eel.start('index.html', size=(1400, 900), port=8080)
            
        except Exception as e:
            self.logger.error(f"アプリケーション実行エラー: {e}")
        finally:
            self.stop_background_polling()

# Global app instance
app = None

def init_app():
    """アプリケーション初期化"""
    global app
    if app is None:
        app = NewsWatcherApp()
    return app

# EEL公開関数

@eel.expose
def get_latest_news(limit: int = 50, offset: int = 0) -> Dict:
    """最新ニュース取得"""
    try:
        app = init_app()
        search_filter = NewsSearchFilter()
        search_filter.limit = limit
        search_filter.offset = offset
        
        news_list = app.db_manager.search_news(search_filter)
        total_count = app.db_manager.get_news_count()
        
        return {
            'success': True,
            'news': news_list,
            'total_count': total_count,
            'current_page': (offset // limit) + 1
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def search_news(search_params: Dict) -> Dict:
    """ニュース検索"""
    try:
        app = init_app()
        search_filter = NewsSearchFilter()
        
        if search_params.get('keyword'):
            search_filter.keyword = search_params['keyword']
        if search_params.get('source'):
            search_filter.source = search_params['source']
        if search_params.get('metal'):
            search_filter.related_metals = [search_params['metal']]
        if search_params.get('is_manual') is not None:
            search_filter.is_manual = search_params['is_manual'] == 'true'
        
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 50)
        search_filter.limit = per_page
        search_filter.offset = (page - 1) * per_page
        
        news_list = app.db_manager.search_news(search_filter)
        total_count = app.db_manager.get_news_count(search_filter)
        
        return {
            'success': True,
            'news': news_list,
            'total_count': total_count,
            'current_page': page
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def search_archive(search_params: Dict) -> Dict:
    """アーカイブ検索"""
    try:
        app = init_app()
        search_filter = NewsSearchFilter()
        
        if search_params.get('start_date'):
            search_filter.start_date = datetime.fromisoformat(search_params['start_date'])
        if search_params.get('end_date'):
            search_filter.end_date = datetime.fromisoformat(search_params['end_date'] + 'T23:59:59')
        if search_params.get('keyword'):
            search_filter.keyword = search_params['keyword']
        
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 50)
        search_filter.limit = per_page
        search_filter.offset = (page - 1) * per_page
        
        news_list = app.db_manager.search_news(search_filter)
        total_count = app.db_manager.get_news_count(search_filter)
        
        return {
            'success': True,
            'news': news_list,
            'total_count': total_count
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def get_news_detail(news_id: str) -> Dict:
    """ニュース詳細取得"""
    try:
        app = init_app()
        news = app.db_manager.get_news_by_id(news_id)
        
        if news:
            return {'success': True, **news}
        else:
            return {'success': False, 'error': 'ニュースが見つかりません'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def add_manual_news(news_data: Dict) -> Dict:
    """手動ニュース登録"""
    try:
        app = init_app()
        
        # 入力検証
        is_valid, error_message = validate_manual_news_input(news_data)
        if not is_valid:
            return {'success': False, 'error': error_message}
        
        # 公開日時処理
        if news_data.get('publish_time'):
            publish_time = datetime.fromisoformat(news_data['publish_time'])
        else:
            publish_time = datetime.now()
        
        # 関連金属自動抽出（入力がない場合）
        related_metals = news_data.get('related_metals')
        if not related_metals:
            related_metals = extract_related_metals(
                news_data['title'], 
                news_data['body']
            )
        
        # ニュース記事作成
        article = NewsArticle(
            title=news_data['title'],
            body=news_data['body'],
            publish_time=publish_time,
            acquire_time=datetime.now(),
            source=news_data.get('source', 'Manual Entry'),
            url=news_data.get('url'),
            related_metals=related_metals,
            is_manual=True
        )
        
        # データベース保存
        success = app.db_manager.insert_news_article(article)
        
        if success:
            app.logger.info(f"手動ニュース登録: {article.news_id}")
            return {'success': True, 'news_id': article.news_id}
        else:
            return {'success': False, 'error': 'データベース保存に失敗しました'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def delete_manual_news(news_id: str) -> Dict:
    """手動ニュース削除"""
    try:
        app = init_app()
        success = app.db_manager.delete_news_by_id(news_id)
        
        if success:
            app.logger.info(f"手動ニュース削除: {news_id}")
            return {'success': True}
        else:
            return {'success': False, 'error': '削除対象が見つからないか、手動登録ニュースではありません'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def get_sources_list() -> List[str]:
    """ソース一覧取得"""
    try:
        app = init_app()
        return app.db_manager.get_sources_list()
    except Exception as e:
        app.logger.error(f"ソース一覧取得エラー: {e}")
        return []

@eel.expose
def get_metals_list() -> List[str]:
    """金属一覧取得"""
    try:
        app = init_app()
        return app.db_manager.get_related_metals_list()
    except Exception as e:
        app.logger.error(f"金属一覧取得エラー: {e}")
        return []

@eel.expose
def get_system_stats() -> Dict:
    """システム統計取得"""
    try:
        app = init_app()
        
        # 基本統計
        total_news = app.db_manager.get_news_count()
        
        # 今日のニュース
        today_filter = NewsSearchFilter()
        today_filter.start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_news = app.db_manager.get_news_count(today_filter)
        
        # Refinitivニュース
        refinitiv_filter = NewsSearchFilter()
        refinitiv_filter.is_manual = False
        refinitiv_news = app.db_manager.get_news_count(refinitiv_filter)
        
        # 手動登録ニュース
        manual_filter = NewsSearchFilter()
        manual_filter.is_manual = True
        manual_news = app.db_manager.get_news_count(manual_filter)
        
        # システム統計
        system_stats = app.db_manager.get_system_stats_summary(30)
        
        return {
            'total_news': total_news,
            'today_news': today_news,
            'refinitiv_news': refinitiv_news,
            'manual_news': manual_news,
            'last_update': datetime.now().isoformat(),
            'collection_runs': system_stats.get('total_runs', 0),
            'avg_execution_time': system_stats.get('avg_execution_time', 0)
        }
    except Exception as e:
        app.logger.error(f"統計取得エラー: {e}")
        return {}

@eel.expose
def manual_collect_news() -> Dict:
    """手動ニュース収集"""
    try:
        app = init_app()
        
        if not app.news_collector:
            app.news_collector = RefinitivNewsCollector(app.config_path)
        
        collected_count = app.news_collector.collect_news()
        
        return {
            'success': True,
            'collected_count': collected_count,
            'status': app.news_collector.get_collection_status()
        }
    except Exception as e:
        app.logger.error(f"手動収集エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def get_app_status() -> Dict:
    """アプリケーション状態取得"""
    try:
        app = init_app()
        
        return {
            'database_connected': app.db_manager.test_connection(),
            'polling_active': app.is_polling_active,
            'last_update': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'database_connected': False,
            'polling_active': False,
            'error': str(e)
        }

def main():
    """メイン実行関数"""
    try:
        app = NewsWatcherApp()
        app.run()
    except KeyboardInterrupt:
        print("\nアプリケーション終了")
    except Exception as e:
        print(f"実行エラー: {e}")

if __name__ == "__main__":
    main()