#!/usr/bin/env python3
"""
ニュースデータ分析スクリプト
収集されたデータの統計と品質分析
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import sys
import os

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager

class NewsDataAnalyzer:
    """ニュースデータ分析器"""
    
    def __init__(self, config_path: str = "../config.json"):
        """初期化"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.db_manager = DatabaseManager(config["database"])
    
    def get_news_dataframe(self, days: int = 30) -> pd.DataFrame:
        """ニュースデータをDataFrameとして取得"""
        news_data = self.db_manager.get_recent_news(days=days, limit=5000)
        return pd.DataFrame(news_data)
    
    def analyze_collection_stats(self, days: int = 30) -> dict:
        """収集統計分析"""
        try:
            with self.db_manager.get_connection() as conn:
                if self.db_manager.db_type == "postgresql":
                    sql = """
                        SELECT 
                            DATE(collection_date) as date,
                            SUM(total_collected) as daily_collected,
                            AVG(execution_time_seconds) as avg_execution_time,
                            SUM(api_calls_made) as daily_api_calls,
                            SUM(high_priority_count) as high_priority,
                            SUM(medium_priority_count) as medium_priority,
                            SUM(low_priority_count) as low_priority
                        FROM collection_stats 
                        WHERE collection_date >= NOW() - INTERVAL '%s days'
                        GROUP BY DATE(collection_date)
                        ORDER BY date DESC
                    """
                    cursor = conn.cursor()
                    cursor.execute(sql, (days,))
                else:
                    sql = """
                        SELECT 
                            CAST(collection_date AS DATE) as date,
                            SUM(total_collected) as daily_collected,
                            AVG(execution_time_seconds) as avg_execution_time,
                            SUM(api_calls_made) as daily_api_calls,
                            SUM(high_priority_count) as high_priority,
                            SUM(medium_priority_count) as medium_priority,
                            SUM(low_priority_count) as low_priority
                        FROM collection_stats 
                        WHERE collection_date >= DATEADD(day, -?, GETDATE())
                        GROUP BY CAST(collection_date AS DATE)
                        ORDER BY date DESC
                    """
                    cursor = conn.cursor()
                    cursor.execute(sql, (days,))
                
                results = cursor.fetchall()
                return pd.DataFrame(results, columns=[
                    'date', 'daily_collected', 'avg_execution_time', 'daily_api_calls',
                    'high_priority', 'medium_priority', 'low_priority'
                ])
                
        except Exception as e:
            print(f"統計分析エラー: {e}")
            return pd.DataFrame()
    
    def generate_report(self, days: int = 30) -> str:
        """分析レポート生成"""
        report = []
        report.append("=" * 60)
        report.append("NewsCollector データ分析レポート")
        report.append("=" * 60)
        report.append(f"分析期間: 過去{days}日間")
        report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # ニュースデータ分析
        df = self.get_news_dataframe(days)
        if not df.empty:
            report.append("📊 ニュースデータサマリー")
            report.append("-" * 30)
            report.append(f"総ニュース件数: {len(df):,} 件")
            report.append(f"ユニークソース数: {df['source'].nunique()} 社")
            report.append(f"平均優先度スコア: {df['priority_score'].mean():.1f}")
            report.append(f"高優先度ニュース: {len(df[df['priority_score'] >= 25])} 件")
            report.append("")
            
            # ソース別統計
            report.append("📰 ソース別統計 (Top 10)")
            report.append("-" * 30)
            source_counts = df['source'].value_counts().head(10)
            for source, count in source_counts.items():
                report.append(f"  {source}: {count} 件")
            report.append("")
            
            # 金属カテゴリ別統計
            if 'metal_category' in df.columns:
                report.append("🔩 金属カテゴリ別統計")
                report.append("-" * 30)
                metal_counts = df['metal_category'].value_counts()
                for metal, count in metal_counts.items():
                    report.append(f"  {metal}: {count} 件")
                report.append("")
            
            # 優先度分布
            report.append("⭐ 優先度分布")
            report.append("-" * 30)
            high_priority = len(df[df['priority_score'] >= 25])
            medium_priority = len(df[(df['priority_score'] >= 15) & (df['priority_score'] < 25)])
            low_priority = len(df[df['priority_score'] < 15])
            report.append(f"  高優先度 (25+): {high_priority} 件 ({high_priority/len(df)*100:.1f}%)")
            report.append(f"  中優先度 (15-24): {medium_priority} 件 ({medium_priority/len(df)*100:.1f}%)")
            report.append(f"  低優先度 (<15): {low_priority} 件 ({low_priority/len(df)*100:.1f}%)")
            report.append("")
        
        # 収集統計分析
        stats_df = self.analyze_collection_stats(days)
        if not stats_df.empty:
            report.append("📈 収集パフォーマンス統計")
            report.append("-" * 30)
            report.append(f"総収集実行回数: {len(stats_df)} 回")
            report.append(f"平均実行時間: {stats_df['avg_execution_time'].mean():.1f} 秒")
            report.append(f"1日あたり平均収集数: {stats_df['daily_collected'].mean():.1f} 件")
            report.append(f"1日あたりAPI呼び出し: {stats_df['daily_api_calls'].mean():.1f} 回")
            report.append("")
            
            # 最新データの詳細
            if len(stats_df) > 0:
                latest = stats_df.iloc[0]
                report.append("📅 最新収集結果")
                report.append("-" * 30)
                report.append(f"  日付: {latest['date']}")
                report.append(f"  収集件数: {latest['daily_collected']} 件")
                report.append(f"  実行時間: {latest['avg_execution_time']:.1f} 秒")
                report.append(f"  高優先度: {latest['high_priority']} 件")
                report.append(f"  中優先度: {latest['medium_priority']} 件")
                report.append(f"  低優先度: {latest['low_priority']} 件")
                report.append("")
        
        # データベース接続状況
        report.append("🔗 システム状況")
        report.append("-" * 30)
        if self.db_manager.test_connection():
            report.append("  データベース接続: ✅ 正常")
        else:
            report.append("  データベース接続: ❌ エラー")
        
        report.append(f"  データベースタイプ: {self.db_manager.db_type.upper()}")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def export_high_priority_news(self, days: int = 7, min_score: int = 25) -> str:
        """高優先度ニュースエクスポート"""
        df = self.get_news_dataframe(days)
        
        if df.empty:
            return "データがありません"
        
        high_priority = df[df['priority_score'] >= min_score].copy()
        high_priority = high_priority.sort_values('priority_score', ascending=False)
        
        # CSV出力
        filename = f"high_priority_news_{datetime.now().strftime('%Y%m%d')}.csv"
        high_priority.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return f"高優先度ニュース {len(high_priority)} 件を {filename} に出力しました"

def main():
    """メイン処理"""
    try:
        analyzer = NewsDataAnalyzer()
        
        # 分析レポート生成
        report = analyzer.generate_report(days=30)
        print(report)
        
        # レポートファイル保存
        report_filename = f"news_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 詳細レポートを {report_filename} に保存しました")
        
        # 高優先度ニュースエクスポート
        export_result = analyzer.export_high_priority_news(days=7, min_score=25)
        print(f"📋 {export_result}")
        
    except Exception as e:
        print(f"分析エラー: {e}")

if __name__ == "__main__":
    main()