#!/usr/bin/env python3
"""
仕様書に基づくデータモデル定義
Refinitivニュースモニタリングシステム用
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import uuid
import json

@dataclass
class NewsArticle:
    """ニュース記事データモデル（仕様書準拠）"""
    title: str
    body: str
    publish_time: datetime
    acquire_time: datetime
    source: str
    is_manual: bool = False
    news_id: Optional[str] = None
    url: Optional[str] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[str] = None
    related_metals: Optional[str] = None
    rating: Optional[int] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初期化後処理"""
        if self.news_id is None:
            # 手動登録時はシステムがユニークIDを生成
            if self.is_manual:
                self.news_id = f"manual_{uuid.uuid4().hex[:12]}"
            else:
                # Refinitivからの場合は別途設定される
                self.news_id = f"system_{uuid.uuid4().hex[:12]}"
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'news_id': self.news_id,
            'title': self.title,
            'body': self.body,
            'publish_time': self.publish_time,
            'acquire_time': self.acquire_time,
            'source': self.source,
            'url': self.url,
            'sentiment': self.sentiment,
            'summary': self.summary,
            'keywords': self.keywords,
            'related_metals': self.related_metals,
            'is_manual': self.is_manual,
            'rating': self.rating,
            'is_read': self.is_read,
            'read_at': self.read_at
        }

@dataclass
class SystemStats:
    """システム統計データモデル"""
    collection_date: datetime
    total_collected: int
    successful_queries: int
    failed_queries: int
    api_calls_made: int
    errors_encountered: int
    execution_time_seconds: float
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'collection_date': self.collection_date,
            'total_collected': self.total_collected,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'api_calls_made': self.api_calls_made,
            'errors_encountered': self.errors_encountered,
            'execution_time_seconds': self.execution_time_seconds
        }

# データベーススキーマ定義（仕様書準拠）
SPEC_DATABASE_SCHEMA = {
    "news_table": """
        CREATE TABLE IF NOT EXISTS news_table (
            news_id VARCHAR(255) PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            publish_time TIMESTAMP NOT NULL,
            acquire_time TIMESTAMP NOT NULL,
            source TEXT NOT NULL,
            url TEXT,
            sentiment TEXT,
            summary TEXT,
            keywords TEXT,
            related_metals TEXT,
            is_manual BOOLEAN DEFAULT FALSE,
            rating INTEGER DEFAULT NULL CHECK (rating >= 1 AND rating <= 3),
            is_read BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP DEFAULT NULL
        );
    """,
    
    "system_stats": """
        CREATE TABLE IF NOT EXISTS system_stats (
            id SERIAL PRIMARY KEY,
            collection_date TIMESTAMP NOT NULL,
            total_collected INTEGER DEFAULT 0,
            successful_queries INTEGER DEFAULT 0,
            failed_queries INTEGER DEFAULT 0,
            api_calls_made INTEGER DEFAULT 0,
            errors_encountered INTEGER DEFAULT 0,
            execution_time_seconds DECIMAL(10,3) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    
    "indexes": [
        "CREATE INDEX IF NOT EXISTS idx_news_publish_time ON news_table(publish_time DESC);",
        "CREATE INDEX IF NOT EXISTS idx_news_source ON news_table(source);",
        "CREATE INDEX IF NOT EXISTS idx_news_related_metals ON news_table(related_metals);",
        "CREATE INDEX IF NOT EXISTS idx_news_is_manual ON news_table(is_manual);",
        "CREATE INDEX IF NOT EXISTS idx_news_title_search ON news_table USING gin(to_tsvector('english', title));",
        "CREATE INDEX IF NOT EXISTS idx_news_body_search ON news_table USING gin(to_tsvector('english', body));",
        "CREATE INDEX IF NOT EXISTS idx_system_stats_date ON system_stats(collection_date);"
    ]
}

# SQL Server用スキーマ（Azure SQL Database対応）
SQLSERVER_SPEC_SCHEMA = {
    "news_table": """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'news_table')
        CREATE TABLE news_table (
            news_id NVARCHAR(255) PRIMARY KEY,
            title NVARCHAR(MAX) NOT NULL,
            body NVARCHAR(MAX) NOT NULL,
            publish_time DATETIME2 NOT NULL,
            acquire_time DATETIME2 NOT NULL,
            source NVARCHAR(500) NOT NULL,
            url NVARCHAR(MAX),
            sentiment NVARCHAR(50),
            summary NVARCHAR(MAX),
            keywords NVARCHAR(MAX),
            related_metals NVARCHAR(500),
            is_manual BIT DEFAULT 0,
            rating INTEGER DEFAULT NULL,
            is_read BIT DEFAULT 0,
            read_at DATETIME2 DEFAULT NULL,
            importance_score INTEGER DEFAULT NULL
        );
    """,
    
    "system_stats": """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'system_stats')
        CREATE TABLE system_stats (
            id INT IDENTITY(1,1) PRIMARY KEY,
            collection_date DATETIME2 NOT NULL,
            total_collected INT DEFAULT 0,
            successful_queries INT DEFAULT 0,
            failed_queries INT DEFAULT 0,
            api_calls_made INT DEFAULT 0,
            errors_encountered INT DEFAULT 0,
            execution_time_seconds DECIMAL(10,3) DEFAULT 0,
            created_at DATETIME2 DEFAULT GETDATE()
        );
    """,
    
    "indexes": [
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_news_publish_time') CREATE INDEX idx_news_publish_time ON news_table(publish_time DESC);",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_news_source') CREATE INDEX idx_news_source ON news_table(source);",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_news_related_metals') CREATE INDEX idx_news_related_metals ON news_table(related_metals);",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_news_is_manual') CREATE INDEX idx_news_is_manual ON news_table(is_manual);",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_system_stats_date') CREATE INDEX idx_system_stats_date ON system_stats(collection_date);"
    ]
}

# 金属カテゴリマッピング
METAL_CATEGORIES = {
    'copper': ['copper', 'cu', 'red metal'],
    'aluminium': ['aluminium', 'aluminum', 'al'],
    'zinc': ['zinc', 'zn'],
    'lead': ['lead', 'pb'],
    'nickel': ['nickel', 'ni'],
    'tin': ['tin', 'sn'],
    'steel': ['steel', 'iron ore', 'fe'],
    'gold': ['gold', 'au'],
    'silver': ['silver', 'ag']
}

def extract_related_metals(title: str, body: str) -> str:
    """
    タイトルと本文から関連金属を抽出
    
    Args:
        title: ニュースタイトル
        body: ニュース本文
        
    Returns:
        カンマ区切りの金属名文字列
    """
    # None値の安全な処理
    title = str(title) if title is not None else ""
    body = str(body) if body is not None else ""
    
    text = f"{title} {body}".lower()
    found_metals = []
    
    for metal, keywords in METAL_CATEGORIES.items():
        for keyword in keywords:
            if keyword in text:
                if metal.capitalize() not in found_metals:
                    found_metals.append(metal.capitalize())
                break
    
    return ', '.join(found_metals) if found_metals else None

def validate_manual_news_input(data: dict) -> tuple[bool, str]:
    """
    手動ニュース入力の検証
    
    Args:
        data: 入力データ辞書
        
    Returns:
        (is_valid, error_message)
    """
    required_fields = ['title', 'body', 'source']
    
    for field in required_fields:
        value = data.get(field)
        if value is None or str(value).strip() == '':
            return False, f"{field} は必須項目です"
    
    # タイトル長制限
    title = str(data.get('title', ''))
    if len(title) > 500:
        return False, "タイトルは500文字以内で入力してください"
    
    # 本文長制限  
    body = str(data.get('body', ''))
    if len(body) > 10000:
        return False, "本文は10000文字以内で入力してください"
    
    # URL形式チェック（入力がある場合）
    url = data.get('url')
    if url is not None:
        url_str = str(url).strip()
        if url_str and not (url_str.startswith('http://') or url_str.startswith('https://')):
            return False, "URLはhttp://またはhttps://で始まる必要があります"
    
    return True, ""

class NewsSearchFilter:
    """ニュース検索フィルタークラス"""
    
    def __init__(self):
        self.keyword: Optional[str] = None
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.source: Optional[str] = None
        self.related_metals: Optional[List[str]] = None
        self.is_manual: Optional[bool] = None
        self.rating: Optional[int] = None
        self.min_importance_score: Optional[int] = None  # 重要度スコア下限フィルター
        self.is_read: Optional[bool] = None  # 既読フィルター
        self.limit: int = 100
        self.offset: int = 0
        # ソート機能
        self.sort_by: str = "smart"  # smart, time_desc, time_asc, rating_desc, rating_asc, relevance
        self.sort_direction: str = "desc"
    
    def to_sql_where_clause(self, db_type: str = "postgresql") -> tuple[str, list]:
        """
        SQLのWHERE句とパラメータを生成
        
        Args:
            db_type: データベースタイプ
            
        Returns:
            (where_clause, parameters)
        """
        conditions = []
        params = []
        
        if self.keyword:
            if db_type == "postgresql":
                conditions.append("(title ILIKE %s OR body ILIKE %s)")
                params.extend([f"%{self.keyword}%", f"%{self.keyword}%"])
            else:  # SQL Server
                conditions.append("(title LIKE ? OR body LIKE ?)")
                params.extend([f"%{self.keyword}%", f"%{self.keyword}%"])
        
        if self.start_date:
            if db_type == "postgresql":
                conditions.append("publish_time >= %s")
            else:
                conditions.append("publish_time >= ?")
            params.append(self.start_date)
        
        if self.end_date:
            if db_type == "postgresql":
                conditions.append("publish_time <= %s")
            else:
                conditions.append("publish_time <= ?")
            params.append(self.end_date)
        
        if self.source:
            if db_type == "postgresql":
                conditions.append("source ILIKE %s")
                params.append(f"%{self.source}%")
            else:
                conditions.append("source LIKE ?")
                params.append(f"%{self.source}%")
        
        if self.related_metals:
            metal_conditions = []
            for metal in self.related_metals:
                if db_type == "postgresql":
                    metal_conditions.append("related_metals ILIKE %s")
                    params.append(f"%{metal}%")
                else:
                    metal_conditions.append("related_metals LIKE ?")
                    params.append(f"%{metal}%")
            if metal_conditions:
                conditions.append(f"({' OR '.join(metal_conditions)})")
        
        if self.is_manual is not None:
            if db_type == "postgresql":
                conditions.append("is_manual = %s")
            else:
                conditions.append("is_manual = ?")
            params.append(self.is_manual)
        
        if self.rating is not None:
            if db_type == "postgresql":
                conditions.append("rating = %s")
            else:
                conditions.append("rating = ?")
            params.append(self.rating)
        
        if self.min_importance_score is not None:
            if db_type == "postgresql":
                conditions.append("importance_score >= %s")
            else:
                conditions.append("importance_score >= ?")
            params.append(self.min_importance_score)
        
        if self.is_read is not None:
            if db_type == "postgresql":
                conditions.append("is_read = %s")
            else:
                conditions.append("is_read = ?")
            params.append(self.is_read)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params
    
    def to_sql_order_clause(self, db_type: str = "postgresql") -> str:
        """
        SQLのORDER BY句を生成（時系列とレーティング最適化）
        
        Args:
            db_type: データベースタイプ
            
        Returns:
            order_clause: ORDER BY句
        """
        if self.sort_by == "smart":
            # スマートソート: レーティング優先、次に時系列
            return """ORDER BY 
                CASE 
                    WHEN rating IS NOT NULL THEN rating 
                    ELSE 0 
                END DESC,
                publish_time DESC,
                acquire_time DESC"""
        
        elif self.sort_by == "rating_priority":
            # レーティング優先: 高レーティング → 未評価 → 低レーティング、同じレーティング内は時系列
            return """ORDER BY 
                CASE 
                    WHEN rating = 3 THEN 1
                    WHEN rating = 2 THEN 2  
                    WHEN rating IS NULL THEN 3
                    WHEN rating = 1 THEN 4
                    ELSE 5
                END,
                publish_time DESC"""
        
        elif self.sort_by == "time_desc":
            return "ORDER BY publish_time DESC, acquire_time DESC"
        
        elif self.sort_by == "time_asc":
            return "ORDER BY publish_time ASC, acquire_time ASC"
        
        elif self.sort_by == "rating_desc":
            return "ORDER BY rating DESC NULLS LAST, publish_time DESC"
        
        elif self.sort_by == "rating_asc":
            return "ORDER BY rating ASC NULLS LAST, publish_time DESC"
        
        elif self.sort_by == "relevance":
            # 関連性ソート: キーワードマッチ度 + レーティング + 時系列
            if self.keyword:
                if db_type == "postgresql":
                    return f"""ORDER BY 
                        (CASE WHEN title ILIKE '%{self.keyword}%' THEN 2 ELSE 0 END +
                         CASE WHEN body ILIKE '%{self.keyword}%' THEN 1 ELSE 0 END +
                         CASE WHEN rating IS NOT NULL THEN rating * 0.5 ELSE 0 END) DESC,
                        publish_time DESC"""
                else:  # SQL Server
                    return f"""ORDER BY 
                        (CASE WHEN title LIKE '%{self.keyword}%' THEN 2 ELSE 0 END +
                         CASE WHEN body LIKE '%{self.keyword}%' THEN 1 ELSE 0 END +
                         CASE WHEN rating IS NOT NULL THEN rating * 0.5 ELSE 0 END) DESC,
                        publish_time DESC"""
            else:
                return self.to_sql_order_clause(db_type).replace("relevance", "smart")
        
        else:
            # デフォルトはスマートソート
            return self.to_sql_order_clause(db_type).replace(self.sort_by, "smart")