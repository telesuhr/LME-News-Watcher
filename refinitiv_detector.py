"""
Refinitiv Workspace/EIKON検出ユーティリティ
起動状態の確認とモード切替機能
"""

import logging
import time
from typing import Dict, Optional, Tuple
import threading
from datetime import datetime, timedelta

try:
    import eikon as ek
    EIKON_AVAILABLE = True
except ImportError:
    EIKON_AVAILABLE = False


class RefinitivDetector:
    """Refinitiv Workspace/EIKON起動状態検出器"""
    
    def __init__(self, api_key: str):
        """初期化"""
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.is_available = False
        self.last_check = None
        self.check_interval = 30  # 30秒間隔でチェック
        self.connection_status = "未確認"
        
    def check_refinitiv_availability(self) -> Tuple[bool, str]:
        """
        Refinitiv Workspace/EIKON の起動状態確認
        
        Returns:
            Tuple[bool, str]: (利用可能かどうか, ステータスメッセージ)
        """
        if not EIKON_AVAILABLE:
            return False, "EIKON ライブラリがインストールされていません"
        
        try:
            # API キー設定（既に設定済みの場合はスキップ）
            ek.set_app_key(self.api_key)
            
            # 簡単なテスト呼び出し
            # システム情報取得（軽量なAPI呼び出し）
            test_response = ek.get_data(['AAPL.O'], ['TR.CommonName'])
            
            # レスポンスが正常かチェック
            if test_response and len(test_response) >= 1:
                self.is_available = True
                self.connection_status = "接続済み"
                self.last_check = datetime.now()
                self.logger.info("Refinitiv Workspace/EIKON 接続確認")
                return True, "Refinitiv Workspace/EIKON が利用可能です"
            else:
                self.is_available = False
                self.connection_status = "データ取得エラー"
                return False, "データ取得テストに失敗しました"
                
        except Exception as e:
            self.is_available = False
            error_msg = str(e).lower()
            
            # エラー内容に応じて詳細なメッセージを返す
            if "desktop session" in error_msg or "eikon desktop" in error_msg:
                self.connection_status = "Desktop未起動"
                return False, "Refinitiv Workspace/EIKON Desktopが起動していません"
            elif "api key" in error_msg:
                self.connection_status = "APIキーエラー"
                return False, "APIキーが無効または設定されていません"
            elif "permission" in error_msg or "unauthorized" in error_msg:
                self.connection_status = "権限エラー"
                return False, "API利用権限がありません"
            elif "timeout" in error_msg:
                self.connection_status = "タイムアウト"
                return False, "接続がタイムアウトしました"
            else:
                self.connection_status = f"エラー: {str(e)[:50]}"
                return False, f"接続エラー: {str(e)}"
    
    def is_refinitiv_available(self) -> bool:
        """
        現在の利用可能状態を返す（キャッシュ利用）
        
        Returns:
            bool: 利用可能かどうか
        """
        # 前回チェックから一定時間経過している場合は再チェック
        if (self.last_check is None or 
            datetime.now() - self.last_check > timedelta(seconds=self.check_interval)):
            self.check_refinitiv_availability()
        
        return self.is_available
    
    def get_connection_status(self) -> Dict:
        """
        接続状態の詳細情報を取得
        
        Returns:
            Dict: 接続状態の詳細
        """
        return {
            'is_available': self.is_available,
            'status': self.connection_status,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'check_interval_seconds': self.check_interval,
            'recommended_mode': 'active' if self.is_available else 'passive'
        }
    
    def start_periodic_check(self, callback=None):
        """
        定期的な接続状態チェックを開始
        
        Args:
            callback: 状態変化時に呼び出されるコールバック関数
        """
        def check_loop():
            previous_status = None
            
            while True:
                try:
                    current_available, message = self.check_refinitiv_availability()
                    
                    # 状態が変化した場合にコールバック実行
                    if callback and previous_status != current_available:
                        callback({
                            'was_available': previous_status,
                            'is_available': current_available,
                            'message': message,
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    previous_status = current_available
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"定期チェックエラー: {e}")
                    time.sleep(self.check_interval)
        
        # バックグラウンドスレッドで実行
        check_thread = threading.Thread(target=check_loop, daemon=True)
        check_thread.start()
        self.logger.info("Refinitiv接続状態の定期チェックを開始")
    
    def force_recheck(self) -> Tuple[bool, str]:
        """
        強制的に再チェックを実行
        
        Returns:
            Tuple[bool, str]: (利用可能かどうか, ステータスメッセージ)
        """
        self.last_check = None  # キャッシュをクリア
        return self.check_refinitiv_availability()


class ApplicationModeManager:
    """アプリケーションモード管理器"""
    
    def __init__(self, refinitiv_detector: RefinitivDetector):
        """初期化"""
        self.detector = refinitiv_detector
        self.current_mode = "unknown"
        self.mode_change_callbacks = []
        self.logger = logging.getLogger(__name__)
    
    def determine_mode(self) -> str:
        """
        Refinitiv接続状態に基づいてアプリケーションモードを決定
        
        Returns:
            str: 'active' または 'passive'
        """
        if self.detector.is_refinitiv_available():
            new_mode = "active"
        else:
            new_mode = "passive"
        
        # モードが変更された場合の処理
        if new_mode != self.current_mode:
            old_mode = self.current_mode
            self.current_mode = new_mode
            
            self.logger.info(f"アプリケーションモード変更: {old_mode} → {new_mode}")
            
            # コールバック実行
            for callback in self.mode_change_callbacks:
                try:
                    callback(old_mode, new_mode)
                except Exception as e:
                    self.logger.error(f"モード変更コールバックエラー: {e}")
        
        return self.current_mode
    
    def add_mode_change_callback(self, callback):
        """
        モード変更時のコールバック関数を追加
        
        Args:
            callback: コールバック関数 (old_mode, new_mode) -> None
        """
        self.mode_change_callbacks.append(callback)
    
    def get_mode_info(self) -> Dict:
        """
        現在のモード情報を取得
        
        Returns:
            Dict: モード情報
        """
        refinitiv_status = self.detector.get_connection_status()
        
        return {
            'current_mode': self.current_mode,
            'refinitiv_available': refinitiv_status['is_available'],
            'refinitiv_status': refinitiv_status['status'],
            'mode_description': {
                'active': 'Refinitiv接続有効 - 自動ニュース収集が利用可能',
                'passive': 'Refinitiv接続無効 - データベース閲覧・手動登録のみ',
                'unknown': 'モード確認中'
            }.get(self.current_mode, '不明'),
            'features_available': {
                'database_access': True,
                'manual_news_entry': True,
                'news_search': True,
                'automatic_collection': self.current_mode == 'active',
                'background_polling': self.current_mode == 'active'
            }
        }