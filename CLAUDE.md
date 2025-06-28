# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Start the desktop application (auto-detects database)
python app.py

# Initialize database (auto-detects SQL Server JCL or PostgreSQL)
python setup_database_spec.py

# Test database auto-detection
python test_database_autodetect.py

# Test JCL database connection (Windows)
python test_jcl_connection.py

# Build Windows executable
python build_exe.py
```

### Testing and Development
```bash
# Install dependencies
pip install -r requirements.txt

# Manual news collection (development)
python -c "from news_collector_spec import RefinitivNewsCollector; collector = RefinitivNewsCollector(); collector.collect_news()"

# Database connection test
python -c "from database_spec import SpecDatabaseManager; import json; config = json.load(open('config_spec.json')); db = SpecDatabaseManager(config['database']); print('Connected:', db.test_connection())"
```

### Configuration
- Edit `config_spec.json` for all system settings
- Database credentials are in `config_spec.json["database"]`
- Refinitiv API key is in `config_spec.json["eikon_api_key"]`
- Gemini AI settings are in `config_spec.json["gemini_integration"]`

## Architecture Overview

### Core System Components

**Main Application (`app.py`)**
- Entry point using Eel framework for desktop UI
- Background threading for news polling
- Python-JavaScript bridge for web UI communication
- Manages application lifecycle and error handling

**Data Collection (`news_collector_spec.py`)**
- `RefinitivNewsCollector`: Main news collection engine with API integration
- `NewsPollingService`: Background polling with configurable intervals
- Handles text processing, deduplication, and metal classification
- Implements rate limiting and error recovery for Refinitiv API

**Database Layer (`database_spec.py`)**
- `SpecDatabaseManager`: Abstracts PostgreSQL and SQL Server operations
- Provides CRUD operations with prepared statements
- Implements search functionality with dynamic filtering
- Connection pooling and transaction management

**Database Auto-Detection (`database_detector.py`)**
- `DatabaseDetector`: Automatically detects available databases
- Tries SQL Server JCL database first (Windows production), then PostgreSQL if unavailable
- Supports Windows Authentication for SQL Server
- Provides fallback to configuration file settings

**AI Analysis (`gemini_analyzer.py`)**
- `GeminiNewsAnalyzer`: Integrates Google Gemini API for news analysis
- Cost-aware rate limiting with daily budget controls
- Batch processing for efficient API usage
- Provides sentiment analysis, summarization, and keyword extraction

**Data Models (`models_spec.py`)**
- `NewsArticle`: Core news article structure with metadata
- `NewsSearchFilter`: Search and filtering logic
- Database schema definitions for dual-database support
- Validation functions for manual news entry

### Data Flow Architecture

```
Refinitiv EIKON API → RefinitivNewsCollector → NewsArticle Models → Database
                                    ↓
Web UI ← Eel Bridge ← Database ← GeminiNewsAnalyzer (async analysis)
```

1. **Collection**: Background service polls Refinitiv API using configured query categories
2. **Processing**: Text cleaning, deduplication, and metal classification
3. **Storage**: Upsert operations with conflict resolution
4. **AI Analysis**: Asynchronous Gemini API calls for enhanced metadata
5. **Presentation**: Real-time UI updates through Eel's Python-JavaScript bridge

### Database Design

**Primary Table (`news_table`)**
- Core news storage with full-text search support
- Supports both Refinitiv and manual entries
- AI analysis fields (sentiment, summary, keywords) for Gemini integration
- Optimized indexes for search performance

**Multi-Database Support**
- PostgreSQL (development) and SQL Server (production) compatibility
- Consistent schema with database-specific optimizations
- Migration scripts for production deployment

### UI Architecture

**Technology Stack**
- Backend: Python + Eel framework
- Frontend: Vanilla HTML/CSS/JavaScript (no framework dependencies)
- Communication: Bidirectional RPC between Python and JavaScript

**Interface Structure**
- Tab-based navigation (Latest News, Archive, Manual Entry, Statistics)
- Modal dialogs for detailed views and settings
- Real-time updates without page refresh
- Responsive design using CSS Grid/Flexbox

### Configuration System

**Central Configuration (`config_spec.json`)**
- Database connection parameters for PostgreSQL/SQL Server
- Refinitiv API settings and query categories
- Gemini AI integration with cost controls
- Polling intervals and performance tuning
- Logging and monitoring settings

**Query Categories for News Collection**
- LME metals, base metals, market general news
- China-related metal news, supply/demand factors
- Market disruption events (strikes, shutdowns, tariffs)

### External Integrations

**Refinitiv EIKON API**
- Requires EIKON Desktop running with valid API key
- Rate-limited to respect API quotas
- Story ID-based deduplication
- HTML content processing and text normalization

**Google Gemini AI**
- Cost-optimized with daily budget limits
- LME market-focused analysis prompts
- Batch processing for efficiency
- Fallback model support for reliability

## Development Practices

### Database Operations
- Always use context managers for database connections
- Implement proper rollback on errors
- Use parameterized queries to prevent SQL injection
- Test both PostgreSQL and SQL Server compatibility

### API Integration
- Implement comprehensive error handling for external APIs
- Use rate limiting to respect service quotas
- Cache responses where appropriate to reduce API calls
- Provide graceful degradation when services are unavailable

### Configuration Management
- Never commit API keys or credentials to version control
- Use environment variables or secure config files for secrets
- Validate configuration on application startup
- Provide clear error messages for configuration issues

### Background Processing
- Use threading for non-blocking background operations
- Implement proper shutdown handling for background threads
- Log background process status and errors
- Provide UI feedback for background operations

### UI Development
- Use Eel's `@eel.expose` decorator for Python functions called from JavaScript
- Handle datetime serialization between Python and JavaScript
- Implement proper error handling in UI callbacks
- Test UI responsiveness during background operations

## Security Considerations

- API keys stored in configuration files (not hardcoded)
- Input validation for manual news entry to prevent injection
- Database credentials secured in configuration
- Proper error handling to avoid information disclosure
- Rate limiting to prevent API abuse