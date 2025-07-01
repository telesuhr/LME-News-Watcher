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
from database_detector import DatabaseDetector
from refinitiv_detector import RefinitivDetector, ApplicationModeManager

class NewsWatcherApp:
    """ニュースウォッチャーアプリケーション"""
    
    def __init__(self, config_path: str = "config_spec.json"):
        """初期化"""
        self.config_path = config_path
        self.config = self._load_config()
        
        # ログ設定（データベースセットアップの前に初期化）
        self.logger = self._setup_logger()
        
        # データベース自動検出
        self.db_manager = self._setup_database()
        
        # Refinitiv接続検出とモード管理
        self.refinitiv_detector = RefinitivDetector(self.config["eikon_api_key"])
        self.mode_manager = ApplicationModeManager(self.refinitiv_detector)
        self.current_mode = "unknown"
        
        self.news_collector = None
        self.polling_service = None
        self.polling_thread = None
        self.is_polling_active = False
        
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
    
    def _setup_database(self) -> SpecDatabaseManager:
        """データベース自動検出とセットアップ"""
        print("データベース接続を確認しています...")
        
        # 自動検出
        detector = DatabaseDetector(self.config_path)
        db_type, db_config = detector.detect_and_configure()
        
        # 検出結果を設定に反映
        self.config["database"] = db_config
        
        # 利用可能なデータベース一覧を表示
        available_dbs = detector.get_available_databases()
        print("\n利用可能なデータベース:")
        for db, is_available in available_dbs.items():
            status = "✓" if is_available else "✗"
            print(f"  {status} {db}")
        
        print(f"\n選択されたデータベース: {db_type}")
        
        # データベースマネージャー作成（全体設定を渡してURLフィルタリング設定にアクセス）
        full_config = self.config.copy()
        full_config["database"] = db_config
        db_manager = SpecDatabaseManager(full_config)
        
        # 起動時に古い 'Manual Entry' を '手動登録' に自動修正
        self._fix_manual_entry_sources(db_manager)
        
        return db_manager
    
    def _fix_manual_entry_sources(self, db_manager):
        """起動時に古い 'Manual Entry' ソースを '手動登録' に修正"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 'Manual Entry'の件数確認
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE source = 'Manual Entry'")
                old_count = cursor.fetchone()[0]
                
                if old_count > 0:
                    print(f"古い 'Manual Entry' データを修正中... ({old_count}件)")
                    
                    # 'Manual Entry' を '手動登録' に更新
                    cursor.execute("UPDATE news_table SET source = '手動登録' WHERE source = 'Manual Entry'")
                    updated_count = cursor.rowcount
                    
                    print(f"✓ ソース名更新完了: 'Manual Entry' → '手動登録' ({updated_count}件)")
                    self.logger.info(f"起動時ソース名修正: 'Manual Entry' → '手動登録' ({updated_count}件)")
                    
        except Exception as e:
            print(f"⚠️ ソース名修正エラー: {e}")
            self.logger.warning(f"起動時ソース名修正エラー: {e}")
    
    def start_background_polling(self):
        """バックグラウンドポーリング開始（Activeモードのみ）"""
        if self.is_polling_active:
            return
        
        # Refinitiv利用可能性チェック
        is_available, message = self.refinitiv_detector.check_refinitiv_availability()
        if not is_available:
            self.logger.warning(f"Refinitiv未利用可能のためポーリングスキップ: {message}")
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
            
            self.logger.info("バックグラウンドポーリング開始（Activeモード）")
            
        except Exception as e:
            self.logger.error(f"ポーリング開始エラー: {e}")
    
    def _polling_worker(self):
        """ポーリングワーカー"""
        while self.is_polling_active:
            try:
                # ニュース収集実行
                collected_count = self.news_collector.collect_news(collection_mode="background")
                self.logger.info(f"バックグラウンド収集: {collected_count} 件")
                
                # 高評価ニュース通知チェック
                self._check_high_importance_news()
                
                # 次回実行まで待機
                polling_interval = self.config["news_collection"]["polling_interval_minutes"]
                for i in range(polling_interval * 60):
                    if not self.is_polling_active:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"ポーリングエラー: {e}")
                time.sleep(60)  # エラー時は1分待機

    def start_passive_mode_polling(self):
        """パッシブモード用のデータベース更新ポーリング開始"""
        if hasattr(self, 'passive_polling_thread') and self.passive_polling_thread and self.passive_polling_thread.is_alive():
            return  # 既に実行中
        
        self.passive_polling_active = True
        self.passive_polling_thread = threading.Thread(
            target=self._passive_polling_worker,
            daemon=True
        )
        self.passive_polling_thread.start()
        self.logger.info("パッシブモード: データベース更新ポーリング開始")
    
    def _passive_polling_worker(self):
        """パッシブモード用ポーリングワーカー（データベース更新チェック）"""
        while getattr(self, 'passive_polling_active', False):
            try:
                # 新しいニュースがあるかチェック
                self._check_database_updates()
                
                # 高評価ニュース通知チェック（パッシブモードでも実行）
                self._check_high_importance_news()
                
                # 次回チェックまで待機（パッシブモードは短い間隔）
                passive_check_interval = self.config.get("passive_mode", {}).get("check_interval_minutes", 2)
                for i in range(passive_check_interval * 60):
                    if not getattr(self, 'passive_polling_active', False):
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"パッシブモードポーリングエラー: {e}")
                time.sleep(60)  # エラー時は1分待機
    
    def _check_database_updates(self):
        """データベースの更新をチェックして通知"""
        try:
            # 最後のチェック時間以降の新しいニュースを取得
            if not hasattr(self, '_last_passive_check'):
                self._last_passive_check = datetime.now() - timedelta(minutes=5)
            
            from models_spec import NewsSearchFilter
            search_filter = NewsSearchFilter()
            search_filter.start_date = self._last_passive_check
            search_filter.limit = 50
            
            new_news = self.db_manager.search_news(search_filter)
            
            if new_news:
                self.logger.info(f"パッシブモード: {len(new_news)}件の新しいニュースを検出")
                # WebUIに更新通知を送信
                eel.notify_database_update({
                    'type': 'database_update',
                    'new_count': len(new_news),
                    'timestamp': datetime.now().isoformat()
                })
            
            self._last_passive_check = datetime.now()
            
        except Exception as e:
            self.logger.error(f"データベース更新チェックエラー: {e}")
    
    def stop_passive_mode_polling(self):
        """パッシブモードポーリング停止"""
        self.passive_polling_active = False
        if hasattr(self, 'passive_polling_thread') and self.passive_polling_thread and self.passive_polling_thread.is_alive():
            self.passive_polling_thread.join(timeout=5)
        self.logger.info("パッシブモードポーリング停止")
    
    def _check_high_importance_news(self):
        """高評価ニュースの通知チェック"""
        try:
            # 過去5分間の高評価ニュース（importance_score >= 8）を取得
            from models_spec import NewsSearchFilter
            
            search_filter = NewsSearchFilter()
            search_filter.start_date = datetime.now() - timedelta(minutes=5)
            search_filter.min_importance_score = 8
            search_filter.limit = 10
            
            high_importance_news = self.db_manager.search_news(search_filter)
            
            for news in high_importance_news:
                # 未通知のニュースのみ通知
                if not self._is_already_notified(news['news_id']):
                    self._send_high_importance_notification(news)
                    self._mark_as_notified(news['news_id'])
                    
        except Exception as e:
            self.logger.error(f"高評価ニュース通知チェックエラー: {e}")
    
    def _send_high_importance_notification(self, news):
        """高評価ニュース通知を送信"""
        try:
            notification_data = {
                'type': 'high_importance_news',
                'news_id': news['news_id'],
                'title': news['title'],
                'importance_score': news.get('importance_score', 0),
                'source': news['source'],
                'timestamp': datetime.now().isoformat()
            }
            
            # WebUIに通知を送信（JavaScript側で受信）
            eel.notify_high_importance_news(notification_data)
            self.logger.info(f"高評価ニュース通知送信: {news['title']} (スコア: {news.get('importance_score', 0)})")
            
        except Exception as e:
            self.logger.error(f"高評価ニュース通知送信エラー: {e}")
    
    def _is_already_notified(self, news_id):
        """既に通知済みかチェック"""
        # 簡易的にメモリ内で管理（実装を簡単にするため）
        if not hasattr(self, '_notified_news_ids'):
            self._notified_news_ids = set()
        return news_id in self._notified_news_ids
    
    def _mark_as_notified(self, news_id):
        """通知済みとしてマーク"""
        if not hasattr(self, '_notified_news_ids'):
            self._notified_news_ids = set()
        self._notified_news_ids.add(news_id)
        
        # メモリ制限のため、100件を超えたら古いものを削除
        if len(self._notified_news_ids) > 100:
            # setから任意の要素を50件削除
            for _ in range(50):
                self._notified_news_ids.pop()
    
    def stop_background_polling(self):
        """バックグラウンドポーリング停止"""
        self.is_polling_active = False
        if self.polling_thread and self.polling_thread.is_alive():
            self.polling_thread.join(timeout=5)
        self.logger.info("バックグラウンドポーリング停止")
    
    def _on_refinitiv_status_change(self, status_change: Dict):
        """Refinitiv接続状態変更時のコールバック"""
        self.logger.info(f"Refinitiv状態変更: {status_change}")
        
        # モード再評価
        new_mode = self.mode_manager.determine_mode()
        
        if new_mode == "active" and not self.is_polling_active:
            # Active モードに切り替わった場合
            self.logger.info("Active モードに切り替え - バックグラウンドポーリング開始")
            self.start_background_polling()
        elif new_mode == "passive" and self.is_polling_active:
            # Passive モードに切り替わった場合
            self.logger.info("Passive モードに切り替え - バックグラウンドポーリング停止")
            self.stop_background_polling()
            # パッシブモードポーリング開始
            self.start_passive_mode_polling()
    
    def run(self):
        """アプリケーション実行"""
        try:
            # データベース接続テスト
            if not self.db_manager.test_connection():
                print("データベース接続エラー")
                return
            
            # テーブル作成
            self.db_manager.create_tables()
            
            # アプリケーションモード決定
            self.current_mode = self.mode_manager.determine_mode()
            mode_info = self.mode_manager.get_mode_info()
            
            print(f"\n=== アプリケーションモード ===")
            print(f"モード: {self.current_mode.upper()}")
            print(f"説明: {mode_info['mode_description']}")
            print(f"Refinitiv状態: {mode_info['refinitiv_status']}")
            
            # モードに応じた初期化
            if self.current_mode == "active":
                # バックグラウンドポーリング開始
                self.start_background_polling()
                # Refinitiv状態の定期チェック開始
                self.refinitiv_detector.start_periodic_check(self._on_refinitiv_status_change)
            else:
                print("Passiveモード: データベース閲覧・手動登録のみ利用可能")
                # パッシブモードでもデータベース更新を監視
                self.start_passive_mode_polling()
            
            # UI開始
            self.logger.info(f"UIアプリケーション開始（{self.current_mode}モード）")
            eel.start('index.html', size=(1400, 900), port=8080)
            
        except Exception as e:
            self.logger.error(f"アプリケーション実行エラー: {e}")
        finally:
            self.stop_background_polling()
            if hasattr(self, 'stop_passive_mode_polling'):
                self.stop_passive_mode_polling()

# Global app instance
app = None

def init_app():
    """アプリケーション初期化"""
    global app
    if app is None:
        app = NewsWatcherApp()
    return app

# EEL公開関数

def _convert_datetime_to_iso(news_list: List[Dict]) -> List[Dict]:
    """日時をISO形式文字列に変換"""
    converted_news = []
    for news in news_list:
        news_copy = news.copy()
        if 'publish_time' in news_copy and news_copy['publish_time']:
            if isinstance(news_copy['publish_time'], datetime):
                news_copy['publish_time'] = news_copy['publish_time'].isoformat()
        if 'acquire_time' in news_copy and news_copy['acquire_time']:
            if isinstance(news_copy['acquire_time'], datetime):
                news_copy['acquire_time'] = news_copy['acquire_time'].isoformat()
        converted_news.append(news_copy)
    return converted_news

@eel.expose
def get_latest_news(limit: int = 50, offset: int = 0) -> Dict:
    """最新ニュース取得"""
    try:
        app = init_app()
        
        # ページング情報をログ出力
        current_page = (offset // limit) + 1 if limit > 0 else 1
        app.logger.info(f"📄 最新ニュース取得: limit={limit}, offset={offset}, 推定ページ={current_page}")
        
        search_filter = NewsSearchFilter()
        search_filter.limit = limit
        search_filter.offset = offset
        
        news_list = app.db_manager.search_news(search_filter)
        news_list = _convert_datetime_to_iso(news_list)
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
        
        # ページング情報をログ出力
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 50)
        app.logger.info(f"📄 ニュース検索: page={page}, per_page={per_page}")
        
        search_filter = NewsSearchFilter()
        
        if search_params.get('keyword'):
            search_filter.keyword = search_params['keyword']
        if search_params.get('source'):
            search_filter.source = search_params['source']
            app.logger.info(f"ソースフィルター適用: '{search_params['source']}'")
        else:
            app.logger.info("ソースフィルターなし")
        if search_params.get('metal'):
            search_filter.related_metals = [search_params['metal']]
        if search_params.get('is_manual'):
            search_filter.is_manual = search_params['is_manual'] == 'true'
            app.logger.info(f"手動登録フィルター適用: {search_filter.is_manual}")
        else:
            app.logger.info("手動登録フィルターなし（全て表示）")
        if search_params.get('rating'):
            try:
                rating_value = int(search_params['rating'])
                if 1 <= rating_value <= 3:
                    search_filter.rating = rating_value
            except (ValueError, TypeError):
                pass  # 無効なレーティング値は無視
        
        # ソートパラメータ
        if search_params.get('sort_by'):
            sort_by = search_params['sort_by']
            valid_sorts = ['smart', 'rating_priority', 'time_desc', 'time_asc', 'rating_desc', 'rating_asc', 'relevance']
            if sort_by in valid_sorts:
                search_filter.sort_by = sort_by
        
        # 既読フィルター
        if search_params.get('is_read'):
            search_filter.is_read = search_params['is_read'] == 'true'
            app.logger.info(f"既読フィルター適用: {search_filter.is_read}")
        else:
            app.logger.info("既読フィルターなし（全て表示）")
        
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 50)
        search_filter.limit = per_page
        search_filter.offset = (page - 1) * per_page
        
        news_list = app.db_manager.search_news(search_filter)
        news_list = _convert_datetime_to_iso(news_list)
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
        
        # ページング情報をログ出力
        page = search_params.get('page', 1)
        per_page = search_params.get('per_page', 50)
        app.logger.info(f"📄 アーカイブ検索: page={page}, per_page={per_page}, 期間={search_params.get('start_date')}〜{search_params.get('end_date')}")
        
        search_filter = NewsSearchFilter()
        
        if search_params.get('start_date'):
            search_filter.start_date = datetime.fromisoformat(search_params['start_date'])
        if search_params.get('end_date'):
            search_filter.end_date = datetime.fromisoformat(search_params['end_date'] + 'T23:59:59')
        if search_params.get('keyword'):
            search_filter.keyword = search_params['keyword']
        
        # ソートパラメータ
        if search_params.get('sort_by'):
            sort_by = search_params['sort_by']
            valid_sorts = ['smart', 'rating_priority', 'time_desc', 'time_asc', 'rating_desc', 'rating_asc', 'relevance']
            if sort_by in valid_sorts:
                search_filter.sort_by = sort_by
        
        search_filter.limit = per_page
        search_filter.offset = (page - 1) * per_page
        
        news_list = app.db_manager.search_news(search_filter)
        news_list = _convert_datetime_to_iso(news_list)
        total_count = app.db_manager.get_news_count(search_filter)
        
        app.logger.info(f"📄 アーカイブ検索結果: {len(news_list)}件取得, 総件数={total_count}")
        
        return {
            'success': True,
            'news': news_list,
            'total_count': total_count,
            'current_page': page
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
            # 日時をISO形式に変換
            news_converted = _convert_datetime_to_iso([news])[0]
            return {'success': True, **news_converted}
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
            source=news_data.get('source', '手動登録'),
            url=news_data.get('url'),
            related_metals=related_metals,
            is_manual=True
        )
        
        # データベース保存
        app.logger.info(f"手動ニュース登録開始: news_id={article.news_id}, title='{article.title[:30]}...'")
        success = app.db_manager.insert_news_article(article)
        
        if success:
            app.logger.info(f"手動ニュース登録成功: {article.news_id}")
            
            # 登録後の確認
            saved_news = app.db_manager.get_news_by_id(article.news_id)
            if saved_news:
                app.logger.info(f"確認取得成功: news_id={saved_news['news_id']}, is_manual={saved_news.get('is_manual', 'N/A')}")
            else:
                app.logger.warning(f"確認取得失敗: news_id={article.news_id} が見つからない")
            
            return {'success': True, 'news_id': article.news_id}
        else:
            app.logger.error(f"手動ニュース登録失敗: {article.news_id}")
            return {'success': False, 'error': 'データベース保存に失敗しました'}
            
    except Exception as e:
        app.logger.error(f"手動ニュース登録例外: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def delete_manual_news(news_id: str) -> Dict:
    """手動ニュース削除"""
    try:
        app = init_app()
        app.logger.info(f"手動ニュース削除要求受信: news_id={news_id}")
        
        success = app.db_manager.delete_news_by_id(news_id)
        
        if success:
            app.logger.info(f"手動ニュース削除成功: {news_id}")
            return {'success': True, 'message': 'ニュースを削除しました'}
        else:
            app.logger.warning(f"手動ニュース削除失敗: {news_id}")
            return {'success': False, 'error': '削除対象が見つからないか、手動登録ニュースではありません'}
            
    except Exception as e:
        app.logger.error(f"手動ニュース削除例外: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def get_sources_list() -> List[str]:
    """ソース一覧取得"""
    try:
        app = init_app()
        sources = app.db_manager.get_sources_list()
        app.logger.info(f"利用可能ソース一覧: {sources}")
        
        
        return sources
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
        
        app.logger.info("手動ニュース収集開始（高速モード）")
        collected_count = app.news_collector.collect_news(collection_mode="manual")
        app.logger.info(f"手動ニュース収集完了: {collected_count}件")
        
        # 手動収集後も高評価ニュース通知をチェック
        app._check_high_importance_news()
        
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
        
        # モード情報取得
        mode_info = app.mode_manager.get_mode_info()
        refinitiv_status = app.refinitiv_detector.get_connection_status()
        
        return {
            'database_connected': app.db_manager.test_connection(),
            'polling_active': app.is_polling_active,
            'current_mode': app.current_mode,
            'mode_description': mode_info['mode_description'],
            'refinitiv_available': refinitiv_status['is_available'],
            'refinitiv_status': refinitiv_status['status'],
            'features_available': mode_info['features_available'],
            'last_update': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'database_connected': False,
            'polling_active': False,
            'current_mode': 'error',
            'error': str(e)
        }


@eel.expose
def get_gemini_stats() -> Dict:
    """Gemini分析統計取得"""
    try:
        app = init_app()
        
        if not hasattr(app, 'news_collector') or not app.news_collector:
            return {'success': False, 'error': 'ニュース収集器が初期化されていません'}
        
        if not hasattr(app.news_collector, 'gemini_analyzer') or not app.news_collector.gemini_analyzer:
            return {'success': False, 'error': 'Gemini分析器が初期化されていません'}
        
        stats = app.news_collector.gemini_analyzer.get_analysis_stats()
        return {'success': True, **stats}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def analyze_single_news(news_id: str) -> Dict:
    """単一ニュースのAI分析実行"""
    try:
        app = init_app()
        
        # ニュース取得
        news = app.db_manager.get_news_by_id(news_id)
        if not news:
            return {'success': False, 'error': 'ニュースが見つかりません'}
        
        # ニュース収集器初期化（未初期化の場合）
        if not app.news_collector:
            app.news_collector = RefinitivNewsCollector(app.config_path)
        
        # 既存の分析を一時的にクリアして強制的に再分析
        news_for_analysis = news.copy()
        news_for_analysis['summary'] = None
        news_for_analysis['sentiment'] = None
        news_for_analysis['keywords'] = None
        
        # AI分析実行（手動分析では高速モデルを使用）
        async def analyze():
            # 手動分析用の高速設定を適用
            original_model = app.news_collector.gemini_analyzer.model
            manual_config = app.config.get('gemini_integration', {}).get('manual_analysis', {})
            
            if manual_config.get('use_fast_model'):
                # 一時的にFlashモデルに切り替え
                try:
                    import google.generativeai as genai
                    fast_model_name = manual_config.get('model', 'gemini-1.5-flash')
                    app.news_collector.gemini_analyzer.model = genai.GenerativeModel(fast_model_name)
                    app.logger.info(f"手動分析用高速モデル使用: {fast_model_name}")
                except Exception as e:
                    app.logger.warning(f"高速モデル切り替え失敗: {e}")
            
            try:
                result = await app.news_collector.gemini_analyzer.analyze_news_item(news_for_analysis)
                return result
            finally:
                # 元のモデルに戻す
                if manual_config.get('use_fast_model'):
                    app.news_collector.gemini_analyzer.model = original_model
        
        import asyncio
        result = asyncio.run(analyze())
        
        if result:
            # データベース更新
            success = app.db_manager.update_news_analysis(news_id, {
                'summary': result.summary,
                'sentiment': result.sentiment,
                'keywords': result.keywords,
                'importance_score': result.importance_score
            })
            
            if success:
                app.logger.info(f"AI分析完了: {news_id}")
                return {'success': True}
            else:
                return {'success': False, 'error': 'データベース更新に失敗しました'}
        else:
            return {'success': False, 'error': 'AI分析に失敗しました'}
            
    except Exception as e:
        app.logger.error(f"AI分析エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def update_news_analysis(analysis_data: Dict) -> Dict:
    """ニュース分析結果の手動更新"""
    try:
        app = init_app()
        
        news_id = analysis_data.get('news_id')
        if not news_id:
            return {'success': False, 'error': 'ニュースIDが指定されていません'}
        
        # データベース更新
        update_data = {
            'summary': analysis_data.get('summary', ''),
            'sentiment': analysis_data.get('sentiment', ''),
            'keywords': analysis_data.get('keywords', '')
        }
        
        success = app.db_manager.update_news_analysis(news_id, update_data)
        
        if success:
            app.logger.info(f"分析結果手動更新: {news_id}")
            return {'success': True}
        else:
            return {'success': False, 'error': '更新に失敗しました'}
            
    except Exception as e:
        app.logger.error(f"分析更新エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def check_refinitiv_status() -> Dict:
    """Refinitiv接続状態の強制チェック"""
    try:
        app = init_app()
        
        # 強制的に再チェック実行
        is_available, message = app.refinitiv_detector.force_recheck()
        
        # モード再評価
        old_mode = app.current_mode
        new_mode = app.mode_manager.determine_mode()
        
        return {
            'success': True,
            'refinitiv_available': is_available,
            'status_message': message,
            'old_mode': old_mode,
            'new_mode': new_mode,
            'mode_changed': old_mode != new_mode,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        app.logger.error(f"Refinitiv状態チェックエラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def get_search_keywords() -> Dict:
    """現在の検索キーワード設定を取得"""
    try:
        app = init_app()
        
        news_config = app.config.get('news_collection', {})
        return {
            'success': True,
            'query_categories': news_config.get('query_categories', {}),
            'lme_keywords': news_config.get('lme_keywords', []),
            'market_keywords': news_config.get('market_keywords', [])
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def update_search_keywords(keywords_data: Dict) -> Dict:
    """検索キーワード設定を更新"""
    try:
        app = init_app()
        
        # 設定ファイル更新
        if 'query_categories' in keywords_data:
            app.config['news_collection']['query_categories'] = keywords_data['query_categories']
        if 'lme_keywords' in keywords_data:
            app.config['news_collection']['lme_keywords'] = keywords_data['lme_keywords']
        if 'market_keywords' in keywords_data:
            app.config['news_collection']['market_keywords'] = keywords_data['market_keywords']
        
        # 設定ファイル保存
        with open(app.config_path, 'w', encoding='utf-8') as f:
            json.dump(app.config, f, ensure_ascii=False, indent=2)
        
        app.logger.info("検索キーワード設定を更新")
        return {'success': True}
        
    except Exception as e:
        app.logger.error(f"キーワード設定更新エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def get_duplicate_stats() -> Dict:
    """重複ニュース統計を取得"""
    try:
        app = init_app()
        duplicate_stats = app.db_manager.get_duplicate_stats()
        return {'success': True, **duplicate_stats}
    except Exception as e:
        app.logger.error(f"重複統計取得エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def remove_duplicate_news(keep_latest: bool = True) -> Dict:
    """重複ニュースを削除"""
    try:
        app = init_app()
        deleted_count = app.db_manager.remove_duplicate_news(keep_latest)
        app.logger.info(f"重複ニュース削除: {deleted_count}件")
        return {
            'success': True, 
            'deleted_count': deleted_count,
            'message': f'{deleted_count}件の重複ニュースを削除しました'
        }
    except Exception as e:
        app.logger.error(f"重複ニュース削除エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def find_duplicate_news() -> Dict:
    """重複ニュースを検索"""
    try:
        app = init_app()
        duplicates = app.db_manager.find_duplicate_news()
        return {'success': True, 'duplicates': duplicates}
    except Exception as e:
        app.logger.error(f"重複ニュース検索エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def get_filter_settings() -> Dict:
    """フィルタ設定取得"""
    try:
        app = init_app()
        news_config = app.config.get("news_collection", {})
        
        return {
            'success': True,
            'filter_url_only_news': news_config.get("filter_url_only_news", True),
            'min_body_length': news_config.get("min_body_length", 50)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def save_filter_settings(filter_url_only: bool, min_body_length: int) -> Dict:
    """フィルタ設定保存"""
    try:
        app = init_app()
        
        # 設定更新
        if "news_collection" not in app.config:
            app.config["news_collection"] = {}
        
        app.config["news_collection"]["filter_url_only_news"] = filter_url_only
        app.config["news_collection"]["min_body_length"] = min_body_length
        
        # 設定ファイル保存
        with open(app.config_path, 'w', encoding='utf-8') as f:
            json.dump(app.config, f, indent=2, ensure_ascii=False)
        
        # データベースマネージャーの設定更新
        app.db_manager.filter_url_only = filter_url_only
        app.db_manager.min_body_length = min_body_length
        
        return {'success': True, 'message': 'フィルタ設定を保存しました'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def update_news_rating(news_id: str, rating: int) -> Dict:
    """ニュースレーティング更新"""
    try:
        app = init_app()
        
        # レーティング値の検証
        if not isinstance(rating, int) or rating < 1 or rating > 3:
            return {'success': False, 'error': 'レーティングは1-3の整数で指定してください'}
        
        success = app.db_manager.update_news_rating(news_id, rating)
        
        if success:
            return {'success': True, 'message': f'レーティングを{rating}星に設定しました'}
        else:
            return {'success': False, 'error': 'レーティング更新に失敗しました'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def clear_news_rating(news_id: str) -> Dict:
    """ニュースレーティングクリア"""
    try:
        app = init_app()
        
        success = app.db_manager.update_news_rating(news_id, None)
        
        if success:
            return {'success': True, 'message': 'レーティングをクリアしました'}
        else:
            return {'success': False, 'error': 'レーティングクリアに失敗しました'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def mark_news_as_read(news_id: str) -> Dict:
    """ニュースを既読にマーク"""
    try:
        app = init_app()
        
        success = app.db_manager.mark_news_as_read(news_id)
        
        if success:
            return {'success': True, 'message': 'ニュースを既読にマークしました'}
        else:
            return {'success': False, 'error': '既読マークに失敗しました'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def mark_news_as_unread(news_id: str) -> Dict:
    """ニュースを未読にマーク"""
    try:
        app = init_app()
        
        success = app.db_manager.mark_news_as_unread(news_id)
        
        if success:
            return {'success': True, 'message': 'ニュースを未読にマークしました'}
        else:
            return {'success': False, 'error': '未読マークに失敗しました'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def mark_all_as_read(filter_conditions: Dict = None) -> Dict:
    """表示中のニュースを一括既読にマーク"""
    try:
        app = init_app()
        
        affected_count = app.db_manager.mark_all_as_read(filter_conditions)
        
        return {
            'success': True, 
            'message': f'{affected_count}件のニュースを既読にマークしました',
            'affected_count': affected_count
        }
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def debug_manual_news_search() -> Dict:
    """手動ニュース検索のデバッグ"""
    try:
        app = init_app()
        
        # 手動ニュースのみでフィルタ検索
        search_filter = NewsSearchFilter()
        search_filter.is_manual = True
        search_filter.limit = 10
        
        app.logger.info("手動ニュース検索デバッグ開始")
        results = app.db_manager.search_news(search_filter)
        app.logger.info(f"手動ニュース検索結果: {len(results)}件")
        
        # 結果の詳細をログ出力
        for i, news in enumerate(results[:3]):  # 最初の3件のみ
            app.logger.info(f"手動ニュース{i+1}: news_id={news.get('news_id')}, title='{news.get('title', '')[:30]}...', is_manual={news.get('is_manual')}")
        
        return {
            'success': True,
            'manual_news_count': len(results),
            'manual_news': results
        }
        
    except Exception as e:
        app.logger.error(f"手動ニュース検索デバッグエラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def debug_database_counts() -> Dict:
    """データベース内の件数をデバッグ確認"""
    try:
        app = init_app()
        
        with app.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 全件数
            cursor.execute("SELECT COUNT(*) FROM news_table")
            total_count = cursor.fetchone()[0]
            
            # 手動登録件数（SQL Serverの場合）
            if app.db_manager.db_type == "sqlserver":
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE is_manual = 1")
            else:
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE is_manual = TRUE")
            manual_count = cursor.fetchone()[0]
            
            # Refinitiv件数
            if app.db_manager.db_type == "sqlserver":
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE is_manual = 0")
            else:
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE is_manual = FALSE")
            refinitiv_count = cursor.fetchone()[0]
            
            # ソース別件数
            cursor.execute("SELECT source, COUNT(*) FROM news_table GROUP BY source ORDER BY COUNT(*) DESC")
            source_counts = cursor.fetchall()
            
            app.logger.info(f"データベース件数確認 - 総件数: {total_count}, 手動: {manual_count}, Refinitiv: {refinitiv_count}")
            
            return {
                'success': True,
                'total_count': total_count,
                'manual_count': manual_count,
                'refinitiv_count': refinitiv_count,
                'source_counts': [{'source': row[0], 'count': row[1]} for row in source_counts]
            }
            
    except Exception as e:
        app.logger.error(f"データベース件数確認エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def fix_manual_entry_source() -> Dict:
    """古い 'Manual Entry' ソースを '手動登録' に更新"""
    try:
        app = init_app()
        
        with app.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 'Manual Entry'の件数確認
            cursor.execute("SELECT COUNT(*) FROM news_table WHERE source = 'Manual Entry'")
            old_count = cursor.fetchone()[0]
            
            if old_count == 0:
                return {
                    'success': True,
                    'message': '更新対象の「Manual Entry」データはありません',
                    'updated_count': 0
                }
            
            # 'Manual Entry' を '手動登録' に更新
            cursor.execute("UPDATE news_table SET source = '手動登録' WHERE source = 'Manual Entry'")
            
            updated_count = cursor.rowcount
            conn.commit()
            
            app.logger.info(f"ソース名更新完了: 'Manual Entry' → '手動登録' ({updated_count}件)")
            
            return {
                'success': True,
                'message': f'「Manual Entry」を「手動登録」に更新しました',
                'updated_count': updated_count
            }
            
    except Exception as e:
        app.logger.error(f"ソース名更新エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def test_manual_news_deletion() -> Dict:
    """手動ニュース削除のテスト"""
    try:
        app = init_app()
        
        # 手動ニュースのリストを取得
        search_filter = NewsSearchFilter()
        search_filter.is_manual = True
        search_filter.limit = 5
        
        manual_news = app.db_manager.search_news(search_filter)
        
        if not manual_news:
            return {
                'success': False,
                'message': '削除テスト用の手動ニュースが見つかりません'
            }
        
        # 最初の手動ニュースのIDを取得
        test_news_id = manual_news[0]['news_id']
        test_title = manual_news[0]['title']
        
        app.logger.info(f"削除テスト対象: news_id={test_news_id}, title='{test_title[:30]}...'")
        
        return {
            'success': True,
            'test_news_id': test_news_id,
            'test_title': test_title,
            'manual_news_count': len(manual_news),
            'message': f'削除テスト準備完了。対象: {test_title[:30]}...'
        }
        
    except Exception as e:
        app.logger.error(f"削除テスト準備エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def debug_manual_filter_issue() -> Dict:
    """手動登録フィルターの問題を調査"""
    try:
        app = init_app()
        
        with app.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 手動登録関連の全データを詳細調査
            if app.db_manager.db_type == "sqlserver":
                # SQL Serverの場合
                sql = """
                    SELECT TOP 20 news_id, title, source, is_manual,
                           CASE WHEN is_manual = 1 THEN 'TRUE' 
                                WHEN is_manual = 0 THEN 'FALSE' 
                                ELSE 'NULL' END as is_manual_text
                    FROM news_table 
                    WHERE source = '手動登録' OR is_manual = 1
                    ORDER BY acquire_time DESC
                """
            else:
                # PostgreSQLの場合
                sql = """
                    SELECT news_id, title, source, is_manual,
                           CASE WHEN is_manual = TRUE THEN 'TRUE' 
                                WHEN is_manual = FALSE THEN 'FALSE' 
                                ELSE 'NULL' END as is_manual_text
                    FROM news_table 
                    WHERE source = '手動登録' OR is_manual = TRUE
                    ORDER BY acquire_time DESC
                    LIMIT 20
                """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            # 結果を辞書形式に変換
            columns = ['news_id', 'title', 'source', 'is_manual_raw', 'is_manual_text']
            debug_data = []
            for row in results:
                debug_data.append(dict(zip(columns, row)))
            
            # フィルターテスト
            search_filter = NewsSearchFilter()
            search_filter.is_manual = True
            search_filter.limit = 20
            
            filtered_results = app.db_manager.search_news(search_filter)
            
            app.logger.info(f"手動登録調査 - DB直接: {len(debug_data)}件, フィルター結果: {len(filtered_results)}件")
            
            # 不整合チェック
            db_news_ids = {item['news_id'] for item in debug_data}
            filter_news_ids = {item['news_id'] for item in filtered_results}
            
            missing_in_filter = db_news_ids - filter_news_ids
            extra_in_filter = filter_news_ids - db_news_ids
            
            return {
                'success': True,
                'db_direct_count': len(debug_data),
                'filter_result_count': len(filtered_results),
                'debug_data': debug_data[:10],  # 最初の10件のみ
                'missing_in_filter': list(missing_in_filter),
                'extra_in_filter': list(extra_in_filter),
                'inconsistency_found': len(missing_in_filter) > 0 or len(extra_in_filter) > 0
            }
            
    except Exception as e:
        app.logger.error(f"手動登録フィルター調査エラー: {e}")
        return {'success': False, 'error': str(e)}

@eel.expose
def fix_manual_filter_inconsistency() -> Dict:
    """手動登録フィルターの不整合を修正"""
    try:
        app = init_app()
        
        with app.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # ソースが「手動登録」なのにis_manual=0のレコードを修正
            if app.db_manager.db_type == "sqlserver":
                # 不整合チェック
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE source = '手動登録' AND is_manual = 0")
                inconsistent_count = cursor.fetchone()[0]
                
                if inconsistent_count > 0:
                    # 修正実行
                    cursor.execute("UPDATE news_table SET is_manual = 1 WHERE source = '手動登録' AND is_manual = 0")
                    updated_count = cursor.rowcount
                    
                    app.logger.info(f"手動登録フラグ修正: {updated_count}件更新")
                    
                    return {
                        'success': True,
                        'message': f'手動登録フラグを修正しました ({updated_count}件)',
                        'updated_count': updated_count
                    }
                else:
                    return {
                        'success': True,
                        'message': '修正が必要な不整合はありませんでした',
                        'updated_count': 0
                    }
            else:
                # PostgreSQLの場合
                cursor.execute("SELECT COUNT(*) FROM news_table WHERE source = '手動登録' AND is_manual = FALSE")
                inconsistent_count = cursor.fetchone()[0]
                
                if inconsistent_count > 0:
                    cursor.execute("UPDATE news_table SET is_manual = TRUE WHERE source = '手動登録' AND is_manual = FALSE")
                    updated_count = cursor.rowcount
                    
                    app.logger.info(f"手動登録フラグ修正: {updated_count}件更新")
                    
                    return {
                        'success': True,
                        'message': f'手動登録フラグを修正しました ({updated_count}件)',
                        'updated_count': updated_count
                    }
                else:
                    return {
                        'success': True,
                        'message': '修正が必要な不整合はありませんでした',
                        'updated_count': 0
                    }
            
    except Exception as e:
        app.logger.error(f"手動登録フラグ修正エラー: {e}")
        return {'success': False, 'error': str(e)}


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