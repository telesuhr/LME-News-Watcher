// LME News Watcher - JavaScript Application

class NewsWatcher {
    constructor() {
        this.currentPage = 1;
        this.newsPerPage = 50;
        this.currentTab = 'latest';
        this.autoRefreshInterval = null;
        this.isAutoRefreshEnabled = false;
        this.highImportanceNotifications = [];
        this.notificationCount = 0;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupTabs();
        this.loadLatestNews();
        this.loadFilters();
        this.loadStats();
        this.setupAutoRefresh();
        this.setupHighImportanceNotifications();
    }
    
    setupEventListeners() {
        // 基本操作
        document.getElementById('manualCollectBtn').addEventListener('click', () => this.manualCollectNews());
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshCurrentTab());
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('searchKeyword').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        // フィルター
        document.getElementById('sourceFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('metalFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('typeFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('ratingFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('sortFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('readFilter').addEventListener('change', () => this.performSearch());
        
        
        // 過去ニュース
        document.getElementById('dateSearchBtn').addEventListener('click', () => this.searchArchive());
        
        // 手動登録
        document.getElementById('manualNewsForm').addEventListener('submit', (e) => this.submitManualNews(e));
        
        // モーダル
        document.getElementById('modalClose').addEventListener('click', () => this.closeModal('newsModal'));
        document.getElementById('settingsBtn').addEventListener('click', () => this.openSettings());
        document.getElementById('settingsModalClose').addEventListener('click', () => this.closeModal('settingsModal'));
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        
        // 設定タブ
        this.setupSettingsTabs();
        
        // システム状態チェック
        document.getElementById('checkRefinitivBtn').addEventListener('click', () => this.checkRefinitivStatus());
        
        // キーワード設定
        document.getElementById('saveKeywordsBtn').addEventListener('click', () => this.saveKeywords());
        document.getElementById('resetKeywordsBtn').addEventListener('click', () => this.resetKeywords());
        
        // 高評価ニュース通知
        document.getElementById('notificationIndicator').addEventListener('click', () => this.showHighImportanceNotifications());
        
        
        // モーダル外クリックで閉じる
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.closeModal(e.target.id);
            }
        });
    }
    
    setupTabs() {
        const tabs = document.querySelectorAll('.nav-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.getAttribute('data-tab');
                this.switchTab(targetTab);
            });
        });
    }
    
    switchTab(tabName) {
        // 現在のタブと同じ場合は何もしない
        if (this.currentTab === tabName) {
            return;
        }
        
        // タブボタンの状態更新
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const targetTabButton = document.querySelector(`[data-tab="${tabName}"]`);
        if (targetTabButton) {
            targetTabButton.classList.add('active');
        }
        
        // タブコンテンツの表示切替
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const targetTabContent = document.getElementById(`${tabName}-tab`);
        if (targetTabContent) {
            targetTabContent.classList.add('active');
        }
        
        this.currentTab = tabName;
        
        // レイアウト安定化のため少し遅延させてから処理
        setTimeout(() => {
            this.handleTabSwitch(tabName);
        }, 50);
    }
    
    handleTabSwitch(tabName) {
        // タブ切替時の処理
        switch(tabName) {
            case 'latest':
                this.loadLatestNews();
                break;
            case 'archive':
                this.setupArchiveTab();
                break;
            case 'manual':
                this.setupManualTab();
                break;
            case 'stats':
                this.loadStats();
                break;
        }
    }
    
    async loadLatestNews() {
        this.showLoading();
        try {
            const response = await eel.get_latest_news(this.newsPerPage, (this.currentPage - 1) * this.newsPerPage)();
            this.displayNewsList(response.news, 'newsList');
            this.updatePagination(response.total_count, this.currentPage);
            this.updateStatus('正常', 'success');
        } catch (error) {
            this.showError('ニュースの読み込みに失敗しました: ' + error.message);
            this.updateStatus('エラー', 'error');
        }
    }
    
    async loadFilters() {
        try {
            const sources = await eel.get_sources_list()();
            const metals = await eel.get_metals_list()();
            
            // Debugging: Log sources list
            console.log('=== Sources Debug Info ===');
            console.log('Total sources count:', sources.length);
            console.log('All sources:', sources);
            
            // Check if Gemini is in the sources
            const hasGemini = sources.some(source => source.toLowerCase().includes('gemini'));
            console.log('Contains "Gemini":', hasGemini);
            
            // Find any sources containing "gemini" (case insensitive)
            const geminiSources = sources.filter(source => source.toLowerCase().includes('gemini'));
            console.log('Gemini-related sources:', geminiSources);
            
            console.log('=== End Sources Debug ===');
            
            this.populateFilter('sourceFilter', sources);
            this.populateFilter('metalFilter', metals);
        } catch (error) {
            console.error('フィルター読み込みエラー:', error);
        }
    }
    
    populateFilter(filterId, options) {
        const filter = document.getElementById(filterId);
        const currentValue = filter.value;
        
        // 既存のオプション（最初の「全て」以外）を削除
        while (filter.children.length > 1) {
            filter.removeChild(filter.lastChild);
        }
        
        // 新しいオプションを追加
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option;
            filter.appendChild(optionElement);
        });
        
        // 以前の選択を復元
        if (currentValue) {
            filter.value = currentValue;
        }
    }
    
    async performSearch() {
        this.currentPage = 1;
        this.showLoading('newsList');
        
        try {
            const searchParams = {
                keyword: document.getElementById('searchKeyword').value,
                source: document.getElementById('sourceFilter').value,
                metal: document.getElementById('metalFilter').value,
                is_manual: document.getElementById('typeFilter').value,
                rating: document.getElementById('ratingFilter').value,
                sort_by: document.getElementById('sortFilter').value,
                is_read: document.getElementById('readFilter').value,
                page: this.currentPage,
                per_page: this.newsPerPage
            };
            
            const response = await eel.search_news(searchParams)();
            this.displayNewsList(response.news, 'newsList');
            this.updatePagination(response.total_count, this.currentPage);
            this.updateStatus('検索完了', 'success');
        } catch (error) {
            this.showError('検索に失敗しました: ' + error.message);
            this.updateStatus('検索エラー', 'error');
        }
    }
    
    async searchArchive() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        if (!startDate || !endDate) {
            this.showError('開始日と終了日を指定してください');
            return;
        }
        
        this.showLoading('archiveList');
        
        try {
            const searchParams = {
                start_date: startDate,
                end_date: endDate,
                keyword: document.getElementById('archiveKeyword').value,
                sort_by: document.getElementById('archiveSortFilter').value,
                page: 1,
                per_page: this.newsPerPage
            };
            
            const response = await eel.search_archive(searchParams)();
            this.displayNewsList(response.news, 'archiveList');
            this.updateStatus('アーカイブ検索完了', 'success');
        } catch (error) {
            this.showError('アーカイブ検索に失敗しました: ' + error.message);
            this.updateStatus('検索エラー', 'error');
        }
    }
    
    displayNewsList(news, containerId) {
        const container = document.getElementById(containerId);
        
        if (!container) {
            console.error(`Container with id '${containerId}' not found`);
            return;
        }
        
        // レイアウト崩れを防ぐため、一旦内容をクリア
        container.innerHTML = '';
        
        if (!news || news.length === 0) {
            container.innerHTML = '<div class="no-results">ニュースが見つかりませんでした</div>';
            return;
        }
        
        // ソート情報ヘッダーを追加
        const sortInfo = this.getCurrentSortInfo(containerId);
        
        // ニュースアイテムのHTMLを生成
        const newsHTML = news.map(item => this.createNewsItemHTML(item)).join('');
        container.innerHTML = sortInfo + newsHTML;
        
        // ニュースアイテムのクリックイベント設定
        requestAnimationFrame(() => {
            container.querySelectorAll('.news-item').forEach(item => {
                item.addEventListener('click', () => {
                    const newsId = item.getAttribute('data-news-id');
                    this.showNewsDetail(newsId);
                });
            });
        });
    }
    
    getCurrentSortInfo(containerId) {
        // ソートフィルターから現在の設定を取得
        let sortFilter, sortName;
        
        if (containerId === 'archiveList') {
            const archiveSortFilter = document.getElementById('archiveSortFilter');
            sortFilter = archiveSortFilter ? archiveSortFilter.value : 'smart';
        } else {
            const mainSortFilter = document.getElementById('sortFilter');
            sortFilter = mainSortFilter ? mainSortFilter.value : 'smart';
        }
        
        // ソート名の日本語変換
        const sortNames = {
            'smart': 'スマートソート (レーティング優先)',
            'rating_priority': 'レーティング優先ソート',
            'time_desc': '新しい順',
            'time_asc': '古い順',
            'rating_desc': '高評価順',
            'rating_asc': '低評価順',
            'relevance': '関連性順'
        };
        
        sortName = sortNames[sortFilter] || 'スマートソート';
        
        return `<div class="sort-info-header">
            <i class="fas fa-sort"></i> ${sortName}で表示中
        </div>`;
    }
    
    createNewsItemHTML(news) {
        const publishTime = new Date(news.publish_time).toLocaleString('ja-JP');
        const acquireTime = new Date(news.acquire_time).toLocaleString('ja-JP');
        const isManual = news.is_manual;
        const preview = news.body ? news.body.substring(0, 200) + '...' : '';
        const metals = news.related_metals ? news.related_metals.split(',').map(m => m.trim()) : [];
        
        // AI分析結果の表示
        const hasAIAnalysis = news.summary || news.sentiment || news.keywords;
        const sentiment = news.sentiment || '';
        const keywords = news.keywords || '';
        const isRead = news.is_read || false;
        
        // 重要度スコアの抽出（keywordsフィールドから）
        let importanceScore = null;
        if (keywords) {
            const importanceMatch = keywords.match(/\[重要度:(\d+)\/10\]/);
            if (importanceMatch) {
                importanceScore = parseInt(importanceMatch[1]);
            }
        }
        
        return `
            <div class="news-item ${isRead ? 'news-read' : 'news-unread'}" data-news-id="${news.news_id}">
                <div class="news-header">
                    <div class="news-title">${this.escapeHtml(news.title)}</div>
                    <div class="news-badges">
                        <span class="badge ${isManual ? 'badge-manual' : 'badge-refinitiv'}">
                            ${isManual ? '手動登録' : 'Refinitiv'}
                        </span>
                        <span class="badge ${isRead ? 'badge-read' : 'badge-unread'}">
                            <i class="fas ${isRead ? 'fa-check' : 'fa-circle'}"></i> ${isRead ? '既読' : '未読'}
                        </span>
                        ${hasAIAnalysis ? '<span class="badge badge-ai">AI分析済</span>' : ''}
                        ${importanceScore !== null ? `<span class="badge badge-importance importance-${this.getImportanceClass(importanceScore)}">${importanceScore}/10</span>` : ''}
                    </div>
                </div>
                
                <div class="news-meta">
                    <div class="news-meta-left">
                        <span class="news-source">${this.escapeHtml(news.source)}</span>
                        ${sentiment ? `<span class="sentiment sentiment-${sentiment.toLowerCase()}">${sentiment}</span>` : ''}
                    </div>
                    <div class="news-meta-right">
                        <span class="news-date">${publishTime}</span>
                        ${this.createInlineRatingControl(news.news_id, news.rating)}
                    </div>
                </div>
                
                ${news.summary ? `<div class="news-summary"><strong>要約:</strong> ${this.escapeHtml(news.summary)}</div>` : ''}
                ${preview && !news.summary ? `<div class="news-preview">${this.escapeHtml(preview)}</div>` : ''}
                
                ${metals.length > 0 ? `
                    <div class="news-metals">
                        ${metals.map(metal => `<span class="metal-tag">${this.escapeHtml(metal)}</span>`).join('')}
                    </div>
                ` : ''}
                
            </div>
        `;
    }
    
    async showNewsDetail(newsId) {
        try {
            const news = await eel.get_news_detail(newsId)();
            
            const modal = document.getElementById('newsModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');
            
            modalTitle.textContent = news.title;
            
            const publishTime = new Date(news.publish_time).toLocaleString('ja-JP');
            const acquireTime = new Date(news.acquire_time).toLocaleString('ja-JP');
            const isManual = news.is_manual;
            const isRead = news.is_read || false;
            
            // 詳細表示で自動的に既読にマーク（未読の場合のみ）
            if (!isRead) {
                await this.markAsRead(newsId);
            }
            
            modalBody.innerHTML = `
                <div class="news-detail">
                    <div class="news-detail-meta">
                        <div class="meta-row">
                            <strong>ソース:</strong> ${this.escapeHtml(news.source)}
                            <span class="badge ${isManual ? 'badge-manual' : 'badge-refinitiv'}">
                                ${isManual ? '手動登録' : 'Refinitiv'}
                            </span>
                        </div>
                        <div class="meta-row">
                            <strong>公開日時:</strong> ${publishTime}
                        </div>
                        <div class="meta-row">
                            <strong>取得日時:</strong> ${acquireTime}
                        </div>
                        ${news.url ? `
                            <div class="meta-row">
                                <strong>URL:</strong> <a href="${news.url}" target="_blank">${news.url}</a>
                            </div>
                        ` : ''}
                        ${news.related_metals ? `
                            <div class="meta-row">
                                <strong>関連金属:</strong> ${this.escapeHtml(news.related_metals)}
                            </div>
                        ` : ''}
                        
                        <div class="meta-row">
                            ${this.createRatingControl(news.news_id, news.rating)}
                        </div>
                    </div>
                    
                    <div class="ai-analysis-section">
                        <div class="analysis-header">
                            <h4>AI分析結果</h4>
                            <div class="analysis-actions">
                                ${!news.summary && !news.sentiment && !news.keywords ? `
                                    <button class="btn btn-ai btn-sm" onclick="newsWatcher.runAIAnalysis('${news.news_id}')">
                                        <i class="fas fa-robot"></i> AI分析を実行
                                    </button>
                                ` : `
                                    <button class="btn btn-secondary btn-sm" onclick="newsWatcher.toggleEditAnalysis('${news.news_id}')">
                                        <i class="fas fa-edit"></i> 編集
                                    </button>
                                    <button class="btn btn-ai btn-sm" onclick="newsWatcher.runAIAnalysis('${news.news_id}')">
                                        <i class="fas fa-sync"></i> 再分析
                                    </button>
                                `}
                            </div>
                        </div>
                        
                        <div id="analysis-view-${news.news_id}" class="analysis-content">
                            ${news.summary || news.sentiment || news.keywords ? `
                                ${news.summary ? `
                                    <div class="analysis-item">
                                        <strong>要約:</strong>
                                        <p>${this.escapeHtml(news.summary)}</p>
                                    </div>
                                ` : ''}
                                ${news.sentiment ? `
                                    <div class="analysis-item">
                                        <strong>センチメント:</strong>
                                        <span class="sentiment sentiment-${news.sentiment.toLowerCase()}">${news.sentiment}</span>
                                    </div>
                                ` : ''}
                                ${news.keywords ? `
                                    <div class="analysis-item">
                                        <strong>キーワード:</strong>
                                        <p>${this.escapeHtml(news.keywords)}</p>
                                    </div>
                                ` : ''}
                            ` : `
                                <p class="no-analysis">まだAI分析が実行されていません。</p>
                            `}
                        </div>
                        
                        <div id="analysis-edit-${news.news_id}" class="analysis-edit" style="display: none;">
                            <div class="form-group">
                                <label>要約</label>
                                <textarea id="edit-summary-${news.news_id}" class="form-textarea" rows="3">${news.summary || ''}</textarea>
                            </div>
                            <div class="form-group">
                                <label>センチメント</label>
                                <select id="edit-sentiment-${news.news_id}" class="form-select">
                                    <option value="">選択してください</option>
                                    <option value="ポジティブ" ${news.sentiment === 'ポジティブ' ? 'selected' : ''}>ポジティブ</option>
                                    <option value="ネガティブ" ${news.sentiment === 'ネガティブ' ? 'selected' : ''}>ネガティブ</option>
                                    <option value="ニュートラル" ${news.sentiment === 'ニュートラル' ? 'selected' : ''}>ニュートラル</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>キーワード</label>
                                <input type="text" id="edit-keywords-${news.news_id}" class="form-input" value="${news.keywords || ''}">
                            </div>
                            <div class="edit-actions">
                                <button class="btn btn-primary btn-sm" onclick="newsWatcher.saveAnalysisEdit('${news.news_id}')">
                                    <i class="fas fa-save"></i> 保存
                                </button>
                                <button class="btn btn-secondary btn-sm" onclick="newsWatcher.cancelEditAnalysis('${news.news_id}')">
                                    <i class="fas fa-times"></i> キャンセル
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="news-detail-body">
                        <h4>本文</h4>
                        <div class="news-body-content">
                            ${this.escapeHtml(news.body).replace(/\n/g, '<br>')}
                        </div>
                    </div>
                    
                    ${isManual ? `
                        <div class="news-detail-actions">
                            <button class="btn btn-danger" onclick="deleteNews('${news.news_id}')">
                                <i class="fas fa-trash"></i> 削除
                            </button>
                        </div>
                    ` : ''}
                </div>
            `;
            
            modal.classList.add('show');
        } catch (error) {
            this.showError('ニュース詳細の読み込みに失敗しました: ' + error.message);
        }
    }
    
    async submitManualNews(event) {
        event.preventDefault();
        
        const formData = {
            title: document.getElementById('manualTitle').value,
            body: document.getElementById('manualBody').value,
            source: document.getElementById('manualSource').value || 'Manual Entry',
            url: document.getElementById('manualUrl').value || null,
            publish_time: document.getElementById('manualPublishTime').value || null,
            related_metals: document.getElementById('manualMetals').value || null
        };
        
        try {
            const result = await eel.add_manual_news(formData)();
            
            if (result.success) {
                this.showSuccess('ニュースを登録しました');
                document.getElementById('manualNewsForm').reset();
                
                // 最新ニュースタブに切り替えて更新
                this.switchTab('latest');
            } else {
                this.showError('登録に失敗しました: ' + result.error);
            }
        } catch (error) {
            this.showError('登録に失敗しました: ' + error.message);
        }
    }
    
    async loadStats() {
        try {
            const stats = await eel.get_system_stats()();
            
            document.getElementById('totalNewsCount').textContent = stats.total_news.toLocaleString();
            document.getElementById('todayNewsCount').textContent = stats.today_news.toLocaleString();
            document.getElementById('refinitivNewsCount').textContent = stats.refinitiv_news.toLocaleString();
            document.getElementById('manualNewsCount').textContent = stats.manual_news.toLocaleString();
            
            const systemInfo = document.getElementById('systemInfo');
            systemInfo.innerHTML = `
                <h4>システム情報</h4>
                <div class="system-info-content">
                    <p><strong>最終更新:</strong> ${new Date(stats.last_update).toLocaleString('ja-JP')}</p>
                    <p><strong>データベース接続:</strong> <span class="status-ok">正常</span></p>
                    <p><strong>今日の収集回数:</strong> ${stats.collection_runs}</p>
                    <p><strong>平均実行時間:</strong> ${stats.avg_execution_time.toFixed(2)}秒</p>
                </div>
            `;
            
            // Gemini統計を読み込み表示
            this.loadGeminiStats();
            
        } catch (error) {
            console.error('統計読み込みエラー:', error);
        }
    }
    
    setupArchiveTab() {
        // デフォルト日付設定（過去1週間）
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - 7);
        
        document.getElementById('endDate').value = endDate.toISOString().split('T')[0];
        document.getElementById('startDate').value = startDate.toISOString().split('T')[0];
    }
    
    setupManualTab() {
        // デフォルト公開日時を現在時刻に設定
        const now = new Date();
        const localDateTime = now.getFullYear() + '-' + 
            String(now.getMonth() + 1).padStart(2, '0') + '-' + 
            String(now.getDate()).padStart(2, '0') + 'T' + 
            String(now.getHours()).padStart(2, '0') + ':' + 
            String(now.getMinutes()).padStart(2, '0');
        
        document.getElementById('manualPublishTime').value = localDateTime;
    }
    
    setupAutoRefresh() {
        // 設定から自動更新設定を読み込み
        const autoRefreshEnabled = localStorage.getItem('autoRefreshEnabled') === 'true';
        const autoRefreshInterval = parseInt(localStorage.getItem('autoRefreshInterval')) || 300;
        
        document.getElementById('autoRefreshEnabled').checked = autoRefreshEnabled;
        document.getElementById('autoRefreshInterval').value = autoRefreshInterval;
        
        if (autoRefreshEnabled) {
            this.startAutoRefresh(autoRefreshInterval);
        }
    }
    
    startAutoRefresh(intervalSeconds) {
        this.stopAutoRefresh();
        this.isAutoRefreshEnabled = true;
        
        this.autoRefreshInterval = setInterval(() => {
            if (this.currentTab === 'latest') {
                this.loadLatestNews();
            }
        }, intervalSeconds * 1000);
        
        this.updateStatus(`自動更新中 (${intervalSeconds}秒間隔)`, 'success');
    }
    
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }
        this.isAutoRefreshEnabled = false;
    }
    
    refreshCurrentTab() {
        switch(this.currentTab) {
            case 'latest':
                this.loadLatestNews();
                break;
            case 'archive':
                this.searchArchive();
                break;
            case 'stats':
                this.loadStats();
                break;
        }
    }
    
    openSettings() {
        document.getElementById('settingsModal').classList.add('show');
        // システム状態を更新
        this.updateSystemStatus();
        // キーワード設定を読み込み
        this.loadKeywordSettings();
    }
    
    saveSettings() {
        const autoRefreshEnabled = document.getElementById('autoRefreshEnabled').checked;
        const autoRefreshInterval = parseInt(document.getElementById('autoRefreshInterval').value);
        const newsPerPage = parseInt(document.getElementById('newsPerPage').value);
        
        // LocalStorageに保存
        localStorage.setItem('autoRefreshEnabled', autoRefreshEnabled);
        localStorage.setItem('autoRefreshInterval', autoRefreshInterval);
        localStorage.setItem('newsPerPage', newsPerPage);
        
        // 設定を適用
        this.newsPerPage = newsPerPage;
        
        if (autoRefreshEnabled) {
            this.startAutoRefresh(autoRefreshInterval);
        } else {
            this.stopAutoRefresh();
            this.updateStatus('待機中', 'success');
        }
        
        this.closeModal('settingsModal');
        this.showSuccess('設定を保存しました');
    }
    
    setupSettingsTabs() {
        // 設定タブの切り替え
        const settingsTabs = document.querySelectorAll('.settings-tab');
        settingsTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.getAttribute('data-settings-tab');
                this.switchSettingsTab(targetTab);
            });
        });
    }
    
    switchSettingsTab(tabName) {
        // タブボタンの状態更新
        document.querySelectorAll('.settings-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-settings-tab="${tabName}"]`).classList.add('active');
        
        // タブコンテンツの表示切替
        document.querySelectorAll('.settings-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-settings`).classList.add('active');
        
        // タブ切り替え時の特別な処理
        if (tabName === 'system') {
            this.updateSystemStatus();
        } else if (tabName === 'keywords') {
            this.loadKeywordSettings();
        }
    }
    
    async updateSystemStatus() {
        try {
            const status = await eel.get_app_status()();
            
            // 動作モード
            const modeElement = document.getElementById('currentMode');
            modeElement.textContent = status.current_mode ? status.current_mode.toUpperCase() : 'UNKNOWN';
            modeElement.className = `mode-badge ${status.current_mode}`;
            
            // Refinitiv状態
            const refinitivElement = document.getElementById('refinitivStatus');
            refinitivElement.textContent = status.refinitiv_status || '不明';
            refinitivElement.className = `status-badge ${status.refinitiv_available ? 'connected' : 'disconnected'}`;
            
            // データベース状態
            const dbElement = document.getElementById('databaseStatus');
            dbElement.textContent = status.database_connected ? '接続済み' : '切断';
            dbElement.className = `status-badge ${status.database_connected ? 'connected' : 'disconnected'}`;
            
            // ポーリング状態
            const pollingElement = document.getElementById('pollingStatus');
            pollingElement.textContent = status.polling_active ? '動作中' : '停止中';
            pollingElement.className = `status-badge ${status.polling_active ? 'running' : 'stopped'}`;
            
            // 利用可能機能の表示
            this.updateAvailableFeatures(status.features_available);
            
        } catch (error) {
            console.error('システム状態取得エラー:', error);
            this.showError('システム状態の取得に失敗しました');
        }
    }
    
    updateAvailableFeatures(features) {
        const featuresList = document.getElementById('availableFeatures');
        featuresList.innerHTML = '';
        
        const featureLabels = {
            'database_access': 'データベースアクセス',
            'manual_news_entry': '手動ニュース登録',
            'news_search': 'ニュース検索',
            'automatic_collection': '自動ニュース収集',
            'background_polling': 'バックグラウンド更新'
        };
        
        for (const [feature, available] of Object.entries(features)) {
            const li = document.createElement('li');
            li.textContent = featureLabels[feature] || feature;
            if (!available) {
                li.classList.add('disabled');
            }
            featuresList.appendChild(li);
        }
    }
    
    async checkRefinitivStatus() {
        const button = document.getElementById('checkRefinitivBtn');
        const originalContent = button.innerHTML;
        
        try {
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> チェック中...';
            button.disabled = true;
            
            const result = await eel.check_refinitiv_status()();
            
            if (result.success) {
                // 状態を更新
                this.updateSystemStatus();
                
                // 結果メッセージ
                if (result.mode_changed) {
                    this.showInfo(`モードが${result.old_mode}から${result.new_mode}に変更されました`);
                } else {
                    this.showSuccess('Refinitiv状態をチェックしました');
                }
            } else {
                this.showError(`チェックエラー: ${result.error}`);
            }
        } catch (error) {
            console.error('Refinitiv状態チェックエラー:', error);
            this.showError('Refinitiv状態チェックに失敗しました');
        } finally {
            button.innerHTML = originalContent;
            button.disabled = false;
        }
    }
    
    async loadKeywordSettings() {
        try {
            const result = await eel.get_search_keywords()();
            
            if (result.success) {
                // LMEキーワード
                document.getElementById('lmeKeywords').value = result.lme_keywords.join(', ');
                
                // 市場キーワード
                document.getElementById('marketKeywords').value = result.market_keywords.join(', ');
                
                // カテゴリ別キーワード
                this.displayCategoryKeywords(result.query_categories);
            } else {
                this.showError('キーワード設定の読み込みに失敗しました');
            }
        } catch (error) {
            console.error('キーワード設定読み込みエラー:', error);
            this.showError('キーワード設定の読み込みに失敗しました');
        }
    }
    
    displayCategoryKeywords(categories) {
        const container = document.getElementById('categoryKeywords');
        container.innerHTML = '';
        
        for (const [categoryName, keywords] of Object.entries(categories)) {
            const categoryDiv = document.createElement('div');
            categoryDiv.className = 'category-item';
            
            const title = document.createElement('h6');
            title.textContent = categoryName;
            categoryDiv.appendChild(title);
            
            const textarea = document.createElement('textarea');
            textarea.name = `category_${categoryName}`;
            textarea.value = keywords.join(', ');
            categoryDiv.appendChild(textarea);
            
            container.appendChild(categoryDiv);
        }
    }
    
    async saveKeywords() {
        try {
            // LMEキーワード
            const lmeKeywords = document.getElementById('lmeKeywords').value
                .split(',').map(k => k.trim()).filter(k => k);
            
            // 市場キーワード
            const marketKeywords = document.getElementById('marketKeywords').value
                .split(',').map(k => k.trim()).filter(k => k);
            
            // カテゴリ別キーワード
            const queryCategories = {};
            const categoryItems = document.querySelectorAll('.category-item textarea');
            categoryItems.forEach(textarea => {
                const categoryName = textarea.name.replace('category_', '');
                const keywords = textarea.value.split(',').map(k => k.trim()).filter(k => k);
                queryCategories[categoryName] = keywords;
            });
            
            const keywordsData = {
                lme_keywords: lmeKeywords,
                market_keywords: marketKeywords,
                query_categories: queryCategories
            };
            
            const result = await eel.update_search_keywords(keywordsData)();
            
            if (result.success) {
                this.showSuccess('検索キーワードを保存しました');
            } else {
                this.showError('検索キーワードの保存に失敗しました');
            }
        } catch (error) {
            console.error('キーワード保存エラー:', error);
            this.showError('検索キーワードの保存に失敗しました');
        }
    }
    
    async resetKeywords() {
        if (confirm('検索キーワードをデフォルト設定にリセットしますか？')) {
            this.loadKeywordSettings();
            this.showInfo('検索キーワード設定をリセットしました');
        }
    }
    
    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
    }
    
    updatePagination(totalCount, currentPage) {
        const totalPages = Math.ceil(totalCount / this.newsPerPage);
        const pagination = document.getElementById('pagination');
        
        console.log(`📄 ページング更新: 総件数=${totalCount}, 現在ページ=${currentPage}, 総ページ数=${totalPages}`);
        
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let paginationHTML = '';
        
        // 前のページボタン
        paginationHTML += `
            <button class="page-btn" ${currentPage <= 1 ? 'disabled' : ''} onclick="newsWatcher.goToPage(${currentPage - 1})">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;
        
        // ページ番号ボタン
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="newsWatcher.goToPage(${i})">
                    ${i}
                </button>
            `;
        }
        
        // 次のページボタン
        paginationHTML += `
            <button class="page-btn" ${currentPage >= totalPages ? 'disabled' : ''} onclick="newsWatcher.goToPage(${currentPage + 1})">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;
        
        pagination.innerHTML = paginationHTML;
    }
    
    goToPage(page) {
        console.log(`🔄 ページ移動: ${this.currentPage} → ${page}`);
        this.currentPage = page;
        
        // タブに応じて適切な関数を呼び出し
        if (this.currentTab === 'latest') {
            this.loadLatestNews();
        } else if (this.currentTab === 'archive') {
            this.searchArchive();
        } else {
            this.performSearch();
        }
    }
    
    updateStatus(message, type = 'success') {
        const statusText = document.getElementById('statusText');
        const statusDot = document.querySelector('.status-dot');
        
        statusText.textContent = message;
        statusDot.className = `status-dot ${type}`;
    }
    
    showLoading(containerId = 'newsList') {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> 読み込み中...</div>';
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showInfo(message) {
        this.showNotification(message, 'info');
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    async markAsRead(newsId) {
        try {
            const response = await eel.mark_news_as_read(newsId)();
            if (response.success) {
                // UIの更新
                this.updateNewsItemReadStatus(newsId, true);
                return true;
            } else {
                this.showError(response.error);
                return false;
            }
        } catch (error) {
            this.showError('既読マークに失敗しました: ' + error.message);
            return false;
        }
    }
    
    async markAsUnread(newsId) {
        try {
            const response = await eel.mark_news_as_unread(newsId)();
            if (response.success) {
                // UIの更新
                this.updateNewsItemReadStatus(newsId, false);
                return true;
            } else {
                this.showError(response.error);
                return false;
            }
        } catch (error) {
            this.showError('未読マークに失敗しました: ' + error.message);
            return false;
        }
    }
    
    
    updateNewsItemReadStatus(newsId, isRead) {
        const newsItem = document.querySelector(`[data-news-id="${newsId}"]`);
        if (newsItem) {
            // CSSクラス更新
            newsItem.classList.remove('news-read', 'news-unread');
            newsItem.classList.add(isRead ? 'news-read' : 'news-unread');
            
            // バッジ更新
            const readBadge = newsItem.querySelector('.badge-read, .badge-unread');
            if (readBadge) {
                readBadge.className = `badge ${isRead ? 'badge-read' : 'badge-unread'}`;
                readBadge.innerHTML = `<i class="fas ${isRead ? 'fa-check' : 'fa-circle'}"></i> ${isRead ? '既読' : '未読'}`;
            }
        }
    }
    
    getImportanceClass(score) {
        if (score >= 8) return 'high';
        if (score >= 6) return 'medium';
        return 'low';
    }
    
    createRatingDisplay(rating) {
        if (!rating) return '';
        
        const stars = '★'.repeat(rating) + '☆'.repeat(3 - rating);
        return `<div class="rating-badge">
            <span class="rating-stars">${stars}</span>
        </div>`;
    }
    
    createInlineRatingControl(newsId, currentRating = null) {
        const stars = [];
        for (let i = 1; i <= 3; i++) {
            const isActive = currentRating && i <= currentRating;
            stars.push(`<span class="star-inline ${isActive ? 'active' : ''}" data-rating="${i}" onclick="event.stopPropagation(); newsWatcher.setRatingInline('${newsId}', ${i})">★</span>`);
        }
        
        return `<div class="rating-control-inline" title="クリックして評価">
            ${stars.join('')}
            ${currentRating ? `<span class="rating-clear" onclick="event.stopPropagation(); newsWatcher.clearRatingInline('${newsId}')" title="評価をクリア">×</span>` : ''}
        </div>`;
    }
    
    createRatingControl(newsId, currentRating = null) {
        const stars = [];
        for (let i = 1; i <= 3; i++) {
            const isActive = currentRating && i <= currentRating;
            stars.push(`<span class="star ${isActive ? 'active' : ''}" data-rating="${i}" onclick="newsWatcher.setRating('${newsId}', ${i})">★</span>`);
        }
        
        return `<div class="rating-control">
            <label>評価: </label>
            ${stars.join('')}
            ${currentRating ? `<button class="btn btn-sm btn-outline-secondary" onclick="newsWatcher.clearRating('${newsId}')" style="margin-left: 0.5rem;">クリア</button>` : ''}
        </div>`;
    }
    
    async loadGeminiStats() {
        try {
            const result = await eel.get_gemini_stats()();
            
            if (result.success) {
                const stats = result;
                const geminiInfo = document.getElementById('geminiInfo') || this.createGeminiInfoSection();
                
                geminiInfo.innerHTML = `
                    <h4>Gemini AI分析統計</h4>
                    <div class="gemini-info-content">
                        <p><strong>総分析数:</strong> ${stats.total_analyzed || 0}</p>
                        <p><strong>成功:</strong> ${stats.successful_analyses || 0}</p>
                        <p><strong>失敗:</strong> ${stats.failed_analyses || 0}</p>
                        <p><strong>本日のコスト:</strong> $${(stats.daily_cost || 0).toFixed(4)}</p>
                        <p><strong>残り予算:</strong> $${(stats.remaining_daily_budget || 0).toFixed(4)}</p>
                        <p><strong>API呼び出し数:</strong> ${stats.api_calls_made || 0}</p>
                        <p><strong>キャッシュヒット数:</strong> ${stats.cache_hits || 0}</p>
                        ${stats.rate_limit_status ? `
                            <p><strong>今分のリクエスト:</strong> ${stats.rate_limit_status.requests_this_minute || 0}/15</p>
                            <p><strong>今日のリクエスト:</strong> ${stats.rate_limit_status.requests_today || 0}/1500</p>
                        ` : ''}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Gemini統計読み込みエラー:', error);
        }
    }
    
    createGeminiInfoSection() {
        const systemInfo = document.getElementById('systemInfo');
        const geminiInfo = document.createElement('div');
        geminiInfo.id = 'geminiInfo';
        geminiInfo.className = 'gemini-info';
        systemInfo.parentNode.insertBefore(geminiInfo, systemInfo.nextSibling);
        return geminiInfo;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // AI分析関連メソッド
    async runAIAnalysis(newsId) {
        // ボタンを無効化
        const analysisButtons = document.querySelectorAll(`[onclick*="${newsId}"]`);
        analysisButtons.forEach(btn => {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 分析中...';
        });
        
        try {
            this.showInfo('AI分析を実行中... (高速モデル使用)');
            
            const startTime = Date.now();
            const result = await eel.analyze_single_news(newsId)();
            const duration = ((Date.now() - startTime) / 1000).toFixed(1);
            
            if (result.success) {
                this.showSuccess(`AI分析が完了しました (${duration}秒)`);
                // モーダルを再読み込み
                await this.showNewsDetail(newsId);
            } else {
                this.showError('AI分析に失敗しました: ' + result.error);
            }
        } catch (error) {
            this.showError('AI分析エラー: ' + error.message);
        } finally {
            // ボタンを復元
            analysisButtons.forEach(btn => {
                btn.disabled = false;
                if (btn.innerHTML.includes('分析中')) {
                    btn.innerHTML = '<i class="fas fa-sync"></i> 再分析';
                }
            });
        }
    }
    
    toggleEditAnalysis(newsId) {
        const viewDiv = document.getElementById(`analysis-view-${newsId}`);
        const editDiv = document.getElementById(`analysis-edit-${newsId}`);
        
        if (viewDiv && editDiv) {
            viewDiv.style.display = viewDiv.style.display === 'none' ? 'block' : 'none';
            editDiv.style.display = editDiv.style.display === 'none' ? 'block' : 'none';
        }
    }
    
    cancelEditAnalysis(newsId) {
        this.toggleEditAnalysis(newsId);
    }
    
    async saveAnalysisEdit(newsId) {
        try {
            const summary = document.getElementById(`edit-summary-${newsId}`).value;
            const sentiment = document.getElementById(`edit-sentiment-${newsId}`).value;
            const keywords = document.getElementById(`edit-keywords-${newsId}`).value;
            
            const analysisData = {
                news_id: newsId,
                summary: summary,
                sentiment: sentiment,
                keywords: keywords
            };
            
            this.showInfo('分析結果を保存中...');
            
            const result = await eel.update_news_analysis(analysisData)();
            
            if (result.success) {
                this.showSuccess('分析結果を保存しました');
                // モーダルを再読み込み
                await this.showNewsDetail(newsId);
            } else {
                this.showError('保存に失敗しました: ' + result.error);
            }
        } catch (error) {
            this.showError('保存エラー: ' + error.message);
        }
    }
    
    async manualCollectNews() {
        const btn = document.getElementById('manualCollectBtn');
        const originalContent = btn.innerHTML;
        
        try {
            // ボタンを無効化
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 収集中...';
            
            this.updateStatus('高速ニュース収集中...', 'warning');
            this.showInfo('高速モードでRefinitiv APIからニュースを収集しています...');
            
            // 開始時刻を記録
            const startTime = Date.now();
            
            const result = await eel.manual_collect_news()();
            
            if (result.success) {
                const endTime = Date.now();
                const duration = Math.round((endTime - startTime) / 1000);
                
                this.showSuccess(`高速ニュース収集完了: ${result.collected_count}件の新しいニュースを取得しました（${duration}秒）`);
                this.updateStatus('収集完了', 'success');
                
                // 最新ニュースタブの場合は自動更新
                if (this.currentTab === 'latest') {
                    await this.loadLatestNews();
                }
            } else {
                this.showError('ニュース収集に失敗しました: ' + result.error);
                this.updateStatus('収集エラー', 'error');
            }
        } catch (error) {
            this.showError('ニュース収集エラー: ' + error.message);
            this.updateStatus('収集エラー', 'error');
        } finally {
            // ボタンを復元
            btn.disabled = false;
            btn.innerHTML = originalContent;
        }
    }
    
    async loadFilterSettings() {
        try {
            const result = await eel.get_filter_settings()();
            if (result.success) {
                document.getElementById('filterUrlOnlyNews').checked = result.filter_url_only_news;
                document.getElementById('minBodyLength').value = result.min_body_length;
            }
        } catch (error) {
            console.error('フィルタ設定読み込みエラー:', error);
        }
    }
    
    async saveDisplaySettings() {
        try {
            const filterUrlOnly = document.getElementById('filterUrlOnlyNews').checked;
            const minBodyLength = parseInt(document.getElementById('minBodyLength').value);
            
            const result = await eel.save_filter_settings(filterUrlOnly, minBodyLength)();
            
            if (result.success) {
                this.showNotification(result.message || 'フィルタ設定を保存しました', 'success');
                // ニュース再読み込み
                this.loadLatestNews();
            } else {
                this.showNotification(result.error || '保存に失敗しました', 'error');
            }
        } catch (error) {
            console.error('フィルタ設定保存エラー:', error);
            this.showNotification('設定保存中にエラーが発生しました', 'error');
        }
    }
    
    async setRating(newsId, rating) {
        try {
            const result = await eel.update_news_rating(newsId, rating)();
            
            if (result.success) {
                this.showNotification(`レーティングを${rating}星に設定しました`, 'success');
                
                // モーダル内のレーティング表示を更新
                const ratingControl = document.querySelector(`[onclick*="${newsId}"]`).closest('.rating-control');
                if (ratingControl) {
                    ratingControl.innerHTML = this.createRatingControl(newsId, rating).match(/<div[^>]*>(.*)<\/div>/)[1];
                }
                
                // ニュース一覧の再読み込みは行わない（パフォーマンス向上）
            } else {
                this.showNotification(result.error || 'レーティング設定に失敗しました', 'error');
            }
        } catch (error) {
            console.error('レーティング設定エラー:', error);
            this.showNotification('レーティング設定中にエラーが発生しました', 'error');
        }
    }
    
    async clearRating(newsId) {
        try {
            const result = await eel.clear_news_rating(newsId)();
            
            if (result.success) {
                this.showNotification('レーティングをクリアしました', 'success');
                
                // モーダル内のレーティング表示を更新
                const ratingControl = document.querySelector(`[onclick*="${newsId}"]`).closest('.rating-control');
                if (ratingControl) {
                    ratingControl.innerHTML = this.createRatingControl(newsId, null).match(/<div[^>]*>(.*)<\/div>/)[1];
                }
            } else {
                this.showNotification(result.error || 'レーティングクリアに失敗しました', 'error');
            }
        } catch (error) {
            console.error('レーティングクリアエラー:', error);
            this.showNotification('レーティングクリア中にエラーが発生しました', 'error');
        }
    }
    
    async setRatingInline(newsId, rating) {
        try {
            const result = await eel.update_news_rating(newsId, rating)();
            
            if (result.success) {
                // 一覧画面のレーティング表示を即座に更新（通知なし）
                const newsItem = document.querySelector(`[data-news-id="${newsId}"]`);
                if (newsItem) {
                    const ratingControlInline = newsItem.querySelector('.rating-control-inline');
                    if (ratingControlInline) {
                        ratingControlInline.outerHTML = this.createInlineRatingControl(newsId, rating);
                    }
                }
            } else {
                // エラー時のみ通知表示
                this.showNotification(result.error || 'レーティング設定に失敗しました', 'error');
            }
        } catch (error) {
            console.error('レーティング設定エラー:', error);
            this.showNotification('レーティング設定中にエラーが発生しました', 'error');
        }
    }
    
    async clearRatingInline(newsId) {
        try {
            const result = await eel.clear_news_rating(newsId)();
            
            if (result.success) {
                // 一覧画面のレーティング表示を即座に更新（通知なし）
                const newsItem = document.querySelector(`[data-news-id="${newsId}"]`);
                if (newsItem) {
                    const ratingControlInline = newsItem.querySelector('.rating-control-inline');
                    if (ratingControlInline) {
                        ratingControlInline.outerHTML = this.createInlineRatingControl(newsId, null);
                    }
                }
            } else {
                // エラー時のみ通知表示
                this.showNotification(result.error || 'レーティングクリアに失敗しました', 'error');
            }
        } catch (error) {
            console.error('レーティングクリアエラー:', error);
            this.showNotification('レーティングクリア中にエラーが発生しました', 'error');
        }
    }
    
    // 高評価ニュース通知機能
    setupHighImportanceNotifications() {
        // 通知インジケーターを初期化
        this.updateNotificationIndicator();
        
        // Eelでエクスポーズされた関数として登録（Python側から呼び出し可能にする）
        window.eel.expose(this.receiveHighImportanceNotification.bind(this), 'notify_high_importance_news');
        window.eel.expose(this.receiveDatabaseUpdateNotification.bind(this), 'notify_database_update');
    }
    
    receiveHighImportanceNotification(notificationData) {
        console.log('高評価ニュース通知受信:', notificationData);
        
        // 通知データを配列に追加
        this.highImportanceNotifications.unshift(notificationData);
        this.notificationCount++;
        
        // 通知インジケーターを更新
        this.updateNotificationIndicator();
        
        // トースト通知を表示
        this.showHighImportanceToast(notificationData);
    }
    
    receiveDatabaseUpdateNotification(updateData) {
        console.log('データベース更新通知受信:', updateData);
        
        // パッシブモードのデータベース更新トーストを表示
        this.showDatabaseUpdateToast(updateData);
        
        // 現在表示中のタブが最新ニュースの場合、自動更新
        if (this.currentTab === 'latest') {
            setTimeout(() => {
                this.loadLatestNews();
            }, 2000); // 2秒後に更新（ユーザーがトーストを読む時間を与える）
        }
    }
    
    updateNotificationIndicator() {
        const indicator = document.getElementById('notificationIndicator');
        const countElement = document.getElementById('notificationCount');
        
        if (this.notificationCount > 0) {
            indicator.style.display = 'flex';
            countElement.textContent = this.notificationCount;
        } else {
            indicator.style.display = 'none';
        }
    }
    
    showHighImportanceToast(notificationData) {
        // 既存のトーストを削除
        const existingToast = document.querySelector('.high-importance-toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        // トースト要素を作成
        const toast = document.createElement('div');
        toast.className = 'high-importance-toast';
        toast.onclick = () => {
            this.openNewsDetail(notificationData.news_id);
            this.removeToast(toast);
        };
        
        const score = notificationData.importance_score || 0;
        const scoreStars = '★'.repeat(Math.min(Math.floor(score / 2), 5));
        
        toast.innerHTML = `
            <button class="toast-close" onclick="event.stopPropagation(); this.parentElement.remove();">
                <i class="fas fa-times"></i>
            </button>
            <div class="toast-header">
                <i class="fas fa-star toast-importance-icon"></i>
                <span>高評価ニュース検出</span>
                <div class="toast-score">スコア: ${score}/10</div>
            </div>
            <div class="toast-title">${notificationData.title}</div>
            <div class="toast-meta">
                <span>ソース: ${notificationData.source}</span>
                <span>${scoreStars}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // 7秒後に自動削除
        setTimeout(() => {
            this.removeToast(toast);
        }, 7000);
    }
    
    showDatabaseUpdateToast(updateData) {
        // 既存のデータベース更新トーストを削除
        const existingToast = document.querySelector('.database-update-toast');
        if (existingToast) {
            existingToast.remove();
        }
        
        // トースト要素を作成
        const toast = document.createElement('div');
        toast.className = 'database-update-toast';
        toast.onclick = () => {
            // 最新ニュースタブに切り替え
            this.switchTab('latest');
            this.removeToast(toast);
        };
        
        toast.innerHTML = `
            <button class="toast-close" onclick="event.stopPropagation(); this.parentElement.remove();">
                <i class="fas fa-times"></i>
            </button>
            <div class="toast-header">
                <i class="fas fa-database toast-update-icon"></i>
                <span>ニュース更新</span>
            </div>
            <div class="toast-title">${updateData.new_count}件の新しいニュースがあります</div>
            <div class="toast-meta">
                <span>クリックして最新ニュースを表示</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // 5秒後に自動削除
        setTimeout(() => {
            this.removeToast(toast);
        }, 5000);
    }
    
    removeToast(toast) {
        if (toast && toast.parentElement) {
            toast.classList.add('toast-fade-out');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        }
    }
    
    showHighImportanceNotifications() {
        if (this.highImportanceNotifications.length === 0) {
            this.showNotification('高評価ニュースの通知はありません', 'info');
            return;
        }
        
        // 最新の高評価ニュースでフィルタ実行
        const latestNotification = this.highImportanceNotifications[0];
        
        // 高評価（スコア8以上）でフィルタリング
        document.getElementById('ratingFilter').value = '';
        document.getElementById('sortFilter').value = 'rating_desc';
        
        // 検索実行
        this.performSearch();
        
        // 通知カウントをリセット
        this.notificationCount = 0;
        this.updateNotificationIndicator();
        
        this.showNotification(`${this.highImportanceNotifications.length}件の高評価ニュースを表示しました`, 'success');
    }
    
}

// グローバル関数
async function deleteNews(newsId) {
    if (!confirm('このニュースを削除しますか？')) {
        return;
    }
    
    try {
        const result = await eel.delete_manual_news(newsId)();
        
        if (result.success) {
            newsWatcher.showSuccess('ニュースを削除しました');
            newsWatcher.closeModal('newsModal');
            newsWatcher.refreshCurrentTab();
        } else {
            newsWatcher.showError('削除に失敗しました: ' + result.error);
        }
    } catch (error) {
        newsWatcher.showError('削除に失敗しました: ' + error.message);
    }
}


// アプリケーション初期化
let newsWatcher;

document.addEventListener('DOMContentLoaded', () => {
    newsWatcher = new NewsWatcher();
    
    // 設定ボタンのイベントリスナー追加
    document.getElementById('saveSettingsBtn').addEventListener('click', () => {
        newsWatcher.saveDisplaySettings();
    });
    
    // フィルタ設定読み込み
    setTimeout(() => {
        newsWatcher.loadFilterSettings();
    }, 100);
});

// 通知スタイルを動的に追加
const notificationStyles = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 1rem;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    .notification-success {
        background: #27ae60;
    }
    
    .notification-error {
        background: #e74c3c;
    }
    
    .notification-info {
        background: #3498db;
    }
    
    .notification button {
        background: none;
        border: none;
        color: white;
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0;
        line-height: 1;
    }
`;

const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);