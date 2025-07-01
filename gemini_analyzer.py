#!/usr/bin/env python3
"""
Gemini AI分析モジュール
コスパと制限を考慮したニュース分析システム
"""

import google.generativeai as genai
import time
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import aiohttp
from pathlib import Path

@dataclass
class AnalysisResult:
    """分析結果データクラス"""
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    keywords: Optional[str] = None
    importance_score: Optional[int] = None
    sentiment_reason: Optional[str] = None
    importance_reason: Optional[str] = None
    translation: Optional[str] = None  # 翻訳結果
    analysis_time: Optional[datetime] = None
    model_used: Optional[str] = None
    cost_estimate: Optional[float] = None

class GeminiRateLimiter:
    """レート制限管理"""
    
    def __init__(self, max_per_minute: int = 15, max_per_day: int = 1500):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self.minute_requests = []
        self.daily_requests = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
    def can_make_request(self) -> bool:
        """リクエスト可能かチェック"""
        now = datetime.now()
        
        # 日次制限リセット
        if now >= self.daily_reset_time + timedelta(days=1):
            self.daily_requests = 0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 分次制限チェック
        one_minute_ago = now - timedelta(minutes=1)
        self.minute_requests = [t for t in self.minute_requests if t > one_minute_ago]
        
        return (len(self.minute_requests) < self.max_per_minute and 
                self.daily_requests < self.max_per_day)
    
    def record_request(self):
        """リクエスト記録"""
        now = datetime.now()
        self.minute_requests.append(now)
        self.daily_requests += 1
    
    def wait_time(self) -> float:
        """待機時間計算"""
        if not self.minute_requests:
            return 0
        
        oldest_request = min(self.minute_requests)
        time_since_oldest = (datetime.now() - oldest_request).total_seconds()
        
        if len(self.minute_requests) >= self.max_per_minute:
            return 60 - time_since_oldest
        
        return 0

class GeminiNewsAnalyzer:
    """Geminiニュース分析器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.gemini_config = config.get("gemini_integration", {})
        self.logger = self._setup_logger()
        
        # Gemini API初期化
        if self.gemini_config.get("api_key") and self.gemini_config["api_key"] != "YOUR_GEMINI_API_KEY_HERE":
            genai.configure(api_key=self.gemini_config["api_key"])
            self.model = genai.GenerativeModel(self.gemini_config.get("model", "gemini-1.5-flash"))
            self.fallback_model = genai.GenerativeModel(self.gemini_config.get("fallback_model", "gemini-1.5-flash-8b"))
        else:
            self.model = None
            self.fallback_model = None
            self.logger.warning("Gemini APIキーが設定されていません")
        
        # レート制限管理
        self.rate_limiter = GeminiRateLimiter(
            max_per_minute=self.gemini_config.get("max_requests_per_minute", 15),
            max_per_day=self.gemini_config.get("max_requests_per_day", 1500)
        )
        
        # コスト追跡
        self.daily_cost = 0.0
        self.max_daily_cost = self.gemini_config.get("cost_optimization", {}).get("max_daily_cost_usd", 5.0)
        
        # 分析済みニュースキャッシュ
        self.analyzed_cache = set()
        
        # パフォーマンス統計
        self.stats = {
            'total_analyzed': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'cache_hits': 0,
            'api_calls_made': 0,
            'total_cost': 0.0
        }
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('GeminiNewsAnalyzer')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _estimate_cost(self, text_length: int, model_name: str) -> float:
        """コスト見積もり（概算）"""
        # Gemini Flash: $0.075 per 1M input tokens, $0.30 per 1M output tokens
        # Gemini Flash 8B: $0.0375 per 1M input tokens, $0.15 per 1M output tokens
        
        # 簡易的にトークン数を文字数/4で概算
        input_tokens = text_length / 4
        output_tokens = 200  # 出力は約200トークンと仮定
        
        if "flash-8b" in model_name.lower():
            input_cost = (input_tokens / 1_000_000) * 0.0375
            output_cost = (output_tokens / 1_000_000) * 0.15
        else:
            input_cost = (input_tokens / 1_000_000) * 0.075
            output_cost = (output_tokens / 1_000_000) * 0.30
        
        return input_cost + output_cost
    
    def _should_analyze_news(self, news: Dict) -> bool:
        """ニュース分析対象かどうか判定"""
        if not self.gemini_config.get("enable_ai_analysis", False):
            return False
        
        # APIキーチェック
        if not self.model:
            return False
        
        # 日次コスト制限チェック
        if self.daily_cost >= self.max_daily_cost:
            self.logger.warning(f"日次コスト制限に達しました: ${self.daily_cost:.4f}")
            return False
        
        # レート制限チェック
        if not self.rate_limiter.can_make_request():
            return False
        
        # 重複分析スキップ
        news_id = news.get('news_id', '')
        if (self.gemini_config.get("cost_optimization", {}).get("skip_duplicate_analysis", True) and 
            news_id in self.analyzed_cache):
            self.stats['cache_hits'] += 1
            return False
        
        # 既に分析済みかチェック
        if news.get('sentiment') or news.get('summary'):
            return False
        
        # 重要度による分析フィルタ
        cost_opt = self.gemini_config.get("cost_optimization", {})
        if cost_opt.get("analyze_only_important_news", False):
            # 基本的な重要度判定（キーワードベース）
            title = news.get('title', '').lower()
            body = news.get('body', '').lower()
            text = f"{title} {body}"
            
            important_keywords = [
                'lme', 'copper', 'aluminium', 'zinc', 'lead', 'nickel', 'tin',
                'price', 'surge', 'drop', 'shortage', 'supply', 'demand',
                'strike', 'mine', 'smelter', 'inventory', 'crisis', 'disruption'
            ]
            
            keyword_count = sum(1 for keyword in important_keywords if keyword in text)
            importance_score = min(10, keyword_count * 2)
            
            threshold = cost_opt.get("importance_threshold", 7)
            if importance_score < threshold:
                return False
        
        return True
    
    def _clean_and_truncate_text(self, text: str) -> str:
        """テキストクリーニングと長さ制限"""
        if not text:
            return ""
        
        # HTMLタグ除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 余分な空白除去
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 長さ制限
        max_length = self.gemini_config.get("max_text_length", 4000)
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    def _should_translate(self, title: str, body: str) -> bool:
        """翻訳が必要かどうか判定（英語記事の場合に翻訳）"""
        text = f"{title} {body}".lower()
        
        # 日本語文字が含まれている場合は翻訳不要
        japanese_chars = re.search(r'[ひらがなカタカナ漢字]', text)
        if japanese_chars:
            return False
        
        # 英語のキーワードが多い場合は翻訳対象
        english_keywords = [
            'copper', 'aluminium', 'aluminum', 'zinc', 'lead', 'nickel', 'tin',
            'lme', 'london metal exchange', 'commodity', 'metal', 'mining',
            'price', 'market', 'trading', 'inventory', 'supply', 'demand',
            'production', 'consumption', 'exports', 'imports', 'china'
        ]
        
        english_count = sum(1 for keyword in english_keywords if keyword in text)
        
        # 英語キーワードが3個以上含まれていれば翻訳対象
        return english_count >= 3
    
    async def _call_gemini_api(self, prompt: str, use_fallback: bool = False) -> Optional[str]:
        """Gemini API呼び出し"""
        if not self.model:
            return None
        
        # レート制限チェック
        wait_time = self.rate_limiter.wait_time()
        if wait_time > 0:
            self.logger.info(f"レート制限のため {wait_time:.1f}秒待機")
            await asyncio.sleep(wait_time)
        
        # レート制限再チェック
        if not self.rate_limiter.can_make_request():
            self.logger.warning("レート制限により分析をスキップ")
            return None
        
        try:
            model = self.fallback_model if use_fallback else self.model
            
            # API呼び出し
            response = model.generate_content(prompt)
            
            # レート制限記録
            self.rate_limiter.record_request()
            self.stats['api_calls_made'] += 1
            
            # コスト更新
            cost = self._estimate_cost(len(prompt), model.model_name)
            self.daily_cost += cost
            self.stats['total_cost'] += cost
            
            # 設定した遅延
            delay = self.gemini_config.get("rate_limit_delay", 4.5)
            await asyncio.sleep(delay)
            
            return response.text if response.text else None
            
        except Exception as e:
            self.logger.error(f"Gemini API呼び出しエラー: {e}")
            
            # フォールバックモデル試行
            if not use_fallback and self.fallback_model:
                self.logger.info("フォールバックモデルで再試行")
                return await self._call_gemini_api(prompt, use_fallback=True)
            
            return None
    
    def _parse_importance_response(self, response: str) -> Tuple[Optional[int], Optional[str]]:
        """重要度レスポンス解析"""
        if not response:
            return None, None
        
        # 数値を抽出
        score_match = re.search(r'(\d+)', response)
        score = int(score_match.group(1)) if score_match else None
        
        # 理由を抽出（数値以降のテキスト）
        if score_match:
            reason_start = score_match.end()
            reason = response[reason_start:].strip().strip('.,:-')
        else:
            reason = response.strip()
        
        return score, reason
    
    def _parse_sentiment_response(self, response: str) -> Tuple[Optional[str], Optional[str]]:
        """センチメントレスポンス解析"""
        if not response:
            return None, None
        
        response_lower = response.lower()
        
        if 'ポジティブ' in response or 'positive' in response_lower:
            sentiment = 'ポジティブ'
        elif 'ネガティブ' in response or 'negative' in response_lower:
            sentiment = 'ネガティブ'
        elif 'ニュートラル' in response or 'neutral' in response_lower:
            sentiment = 'ニュートラル'
        else:
            sentiment = 'ニュートラル'  # デフォルト
        
        # 理由を抽出
        lines = response.split('\n')
        reason = None
        for line in lines:
            if line.strip() and not any(word in line.lower() for word in ['ポジティブ', 'ネガティブ', 'ニュートラル', 'positive', 'negative', 'neutral']):
                reason = line.strip()
                break
        
        return sentiment, reason
    
    async def analyze_news_item(self, news: Dict) -> Optional[AnalysisResult]:
        """個別ニュース分析"""
        if not self._should_analyze_news(news):
            return None
        
        try:
            self.stats['total_analyzed'] += 1
            
            title = news.get('title', '')
            body = news.get('body', '')
            text = self._clean_and_truncate_text(f"{title}\n\n{body}")
            
            if not text:
                return None
            
            result = AnalysisResult(analysis_time=datetime.now())
            prompts = self.gemini_config.get("analysis_prompts", {})
            
            # 要約生成
            if self.gemini_config.get("summary_generation", False):
                summary_prompt = f"{prompts.get('summary', '要約してください:')}\n\n{text}"
                result.summary = await self._call_gemini_api(summary_prompt)
            
            # センチメント分析
            if self.gemini_config.get("sentiment_analysis", False):
                sentiment_prompt = f"{prompts.get('sentiment', 'センチメントを評価してください:')}\n\n{text}"
                sentiment_response = await self._call_gemini_api(sentiment_prompt)
                result.sentiment, result.sentiment_reason = self._parse_sentiment_response(sentiment_response)
            
            # キーワード抽出
            if self.gemini_config.get("keyword_extraction", False):
                keyword_prompt = f"{prompts.get('keywords', 'キーワードを抽出してください:')}\n\n{text}"
                result.keywords = await self._call_gemini_api(keyword_prompt)
            
            # 重要度評価
            if self.gemini_config.get("importance_scoring", False):
                importance_prompt = f"{prompts.get('importance', '重要度を評価してください:')}\n\n{text}"
                importance_response = await self._call_gemini_api(importance_prompt)
                result.importance_score, result.importance_reason = self._parse_importance_response(importance_response)
            
            # 翻訳（英語記事の場合、設定で有効な場合のみ）
            if self.gemini_config.get("translation_enabled", False) and self._should_translate(title, body):
                translation_prompt = f"{prompts.get('translation', '日本語に翻訳してください:')}\n\n{text}"
                result.translation = await self._call_gemini_api(translation_prompt)
                self.logger.info(f"翻訳完了: {title[:30]}...")
            
            # モデル情報
            result.model_used = self.model.model_name if self.model else None
            result.cost_estimate = self._estimate_cost(len(text), result.model_used or "unknown")
            
            # キャッシュに追加
            news_id = news.get('news_id', '')
            if news_id:
                self.analyzed_cache.add(news_id)
            
            self.stats['successful_analyses'] += 1
            self.logger.info(f"ニュース分析完了: {title[:50]}...")
            
            return result
            
        except Exception as e:
            self.logger.error(f"ニュース分析エラー: {e}")
            self.stats['failed_analyses'] += 1
            return None
    
    async def analyze_news_batch(self, news_list: List[Dict]) -> List[Tuple[str, AnalysisResult]]:
        """ニュース一括分析"""
        batch_size = self.gemini_config.get("cost_optimization", {}).get("batch_size", 5)
        results = []
        
        # バッチ処理
        for i in range(0, len(news_list), batch_size):
            batch = news_list[i:i + batch_size]
            
            # 日次コスト制限チェック
            if self.daily_cost >= self.max_daily_cost:
                self.logger.warning("日次コスト制限に達したため、分析を停止")
                break
            
            # バッチ内並列処理
            tasks = []
            for news in batch:
                if self._should_analyze_news(news):
                    task = self.analyze_news_item(news)
                    tasks.append((news.get('news_id', ''), task))
            
            if tasks:
                # 並列実行
                batch_results = await asyncio.gather(*[task for _, task in tasks])
                
                # 結果をペアリング
                for (news_id, _), result in zip(tasks, batch_results):
                    if result:
                        results.append((news_id, result))
                
                # バッチ間の遅延
                if i + batch_size < len(news_list):
                    await asyncio.sleep(2)
        
        return results
    
    def get_analysis_stats(self) -> Dict:
        """分析統計取得"""
        return {
            **self.stats,
            'daily_cost': self.daily_cost,
            'remaining_daily_budget': max(0, self.max_daily_cost - self.daily_cost),
            'cache_size': len(self.analyzed_cache),
            'rate_limit_status': {
                'requests_this_minute': len(self.rate_limiter.minute_requests),
                'requests_today': self.rate_limiter.daily_requests,
                'can_make_request': self.rate_limiter.can_make_request()
            }
        }

# 使用例とテスト用
async def main():
    """テスト用メイン関数"""
    config = {
        "gemini_integration": {
            "enable_ai_analysis": True,
            "api_key": "YOUR_API_KEY",
            "model": "gemini-1.5-flash",
            "summary_generation": True,
            "sentiment_analysis": True,
            "keyword_extraction": True,
            "importance_scoring": True
        }
    }
    
    analyzer = GeminiNewsAnalyzer(config)
    
    # テストニュース
    test_news = {
        'news_id': 'test_001',
        'title': 'LME copper prices surge on supply concerns',
        'body': 'London Metal Exchange copper prices rose sharply today amid growing concerns about supply disruptions...'
    }
    
    result = await analyzer.analyze_news_item(test_news)
    if result:
        print(f"Summary: {result.summary}")
        print(f"Sentiment: {result.sentiment}")
        print(f"Keywords: {result.keywords}")
        print(f"Importance: {result.importance_score}")

if __name__ == "__main__":
    asyncio.run(main())