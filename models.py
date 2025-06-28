#!/usr/bin/env python3
"""
データモデル定義
PostgreSQL/SQL Server両対応の設計
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import json

@dataclass
class NewsItem:
    """ニュースアイテムデータモデル"""
    story_id: str
    headline: str
    source: str
    published_date: datetime
    body: Optional[str] = None
    priority_score: int = 0
    metal_category: Optional[str] = None
    keywords: Optional[List[str]] = None
    query_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'story_id': self.story_id,
            'headline': self.headline,
            'source': self.source,
            'published_date': self.published_date,
            'body': self.body,
            'priority_score': self.priority_score,
            'metal_category': self.metal_category,
            'keywords': json.dumps(self.keywords) if self.keywords else None,
            'query_type': self.query_type,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

@dataclass 
class CollectionStats:
    """収集統計データモデル"""
    collection_date: datetime
    total_collected: int
    successful_queries: int
    failed_queries: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    duplicate_removed: int
    execution_time_seconds: float
    api_calls_made: int
    errors_encountered: int
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            'collection_date': self.collection_date,
            'total_collected': self.total_collected,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'high_priority_count': self.high_priority_count,
            'medium_priority_count': self.medium_priority_count,
            'low_priority_count': self.low_priority_count,
            'duplicate_removed': self.duplicate_removed,
            'execution_time_seconds': self.execution_time_seconds,
            'api_calls_made': self.api_calls_made,
            'errors_encountered': self.errors_encountered
        }

# データベーススキーマ定義（PostgreSQL/SQL Server両対応）
DATABASE_SCHEMA = {
    "news_items": """
        CREATE TABLE news_items (
            id SERIAL PRIMARY KEY,
            story_id VARCHAR(255) UNIQUE NOT NULL,
            headline TEXT NOT NULL,
            source VARCHAR(100) NOT NULL,
            published_date TIMESTAMP NOT NULL,
            body TEXT,
            priority_score INTEGER DEFAULT 0,
            metal_category VARCHAR(50),
            keywords TEXT, -- JSON文字列として保存
            query_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    
    "collection_stats": """
        CREATE TABLE collection_stats (
            id SERIAL PRIMARY KEY,
            collection_date TIMESTAMP NOT NULL,
            total_collected INTEGER DEFAULT 0,
            successful_queries INTEGER DEFAULT 0,
            failed_queries INTEGER DEFAULT 0,
            high_priority_count INTEGER DEFAULT 0,
            medium_priority_count INTEGER DEFAULT 0,
            low_priority_count INTEGER DEFAULT 0,
            duplicate_removed INTEGER DEFAULT 0,
            execution_time_seconds DECIMAL(10,3) DEFAULT 0,
            api_calls_made INTEGER DEFAULT 0,
            errors_encountered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """,
    
    "indexes": [
        "CREATE INDEX idx_news_published_date ON news_items(published_date);",
        "CREATE INDEX idx_news_source ON news_items(source);",
        "CREATE INDEX idx_news_priority_score ON news_items(priority_score);",
        "CREATE INDEX idx_news_metal_category ON news_items(metal_category);",
        "CREATE INDEX idx_news_story_id ON news_items(story_id);",
        "CREATE INDEX idx_collection_stats_date ON collection_stats(collection_date);"
    ]
}

# SQL Server用スキーマ（将来の移行用）
SQLSERVER_SCHEMA = {
    "news_items": """
        CREATE TABLE news_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            story_id NVARCHAR(255) UNIQUE NOT NULL,
            headline NTEXT NOT NULL,
            source NVARCHAR(100) NOT NULL,
            published_date DATETIME2 NOT NULL,
            body NTEXT,
            priority_score INT DEFAULT 0,
            metal_category NVARCHAR(50),
            keywords NTEXT, -- JSON文字列として保存
            query_type NVARCHAR(50),
            created_at DATETIME2 DEFAULT GETDATE(),
            updated_at DATETIME2 DEFAULT GETDATE()
        );
    """,
    
    "collection_stats": """
        CREATE TABLE collection_stats (
            id INT IDENTITY(1,1) PRIMARY KEY,
            collection_date DATETIME2 NOT NULL,
            total_collected INT DEFAULT 0,
            successful_queries INT DEFAULT 0,
            failed_queries INT DEFAULT 0,
            high_priority_count INT DEFAULT 0,
            medium_priority_count INT DEFAULT 0,
            low_priority_count INT DEFAULT 0,
            duplicate_removed INT DEFAULT 0,
            execution_time_seconds DECIMAL(10,3) DEFAULT 0,
            api_calls_made INT DEFAULT 0,
            errors_encountered INT DEFAULT 0,
            created_at DATETIME2 DEFAULT GETDATE()
        );
    """,
    
    "indexes": [
        "CREATE INDEX idx_news_published_date ON news_items(published_date);",
        "CREATE INDEX idx_news_source ON news_items(source);", 
        "CREATE INDEX idx_news_priority_score ON news_items(priority_score);",
        "CREATE INDEX idx_news_metal_category ON news_items(metal_category);",
        "CREATE INDEX idx_news_story_id ON news_items(story_id);",
        "CREATE INDEX idx_collection_stats_date ON collection_stats(collection_date);"
    ]
}