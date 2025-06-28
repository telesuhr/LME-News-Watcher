// LME News Watcher - JavaScript Application

class NewsWatcher {
    constructor() {
        this.currentPage = 1;
        this.newsPerPage = 50;
        this.currentTab = 'latest';
        this.autoRefreshInterval = null;
        this.isAutoRefreshEnabled = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupTabs();
        this.loadLatestNews();
        this.loadFilters();
        this.loadStats();
        this.setupAutoRefresh();
    }
    
    setupEventListeners() {
        // 基本操作
        document.getElementById('refreshBtn').addEventListener('click', () => this.refreshCurrentTab());
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('searchKeyword').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        
        // フィルター
        document.getElementById('sourceFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('metalFilter').addEventListener('change', () => this.performSearch());
        document.getElementById('typeFilter').addEventListener('change', () => this.performSearch());
        
        // 過去ニュース
        document.getElementById('dateSearchBtn').addEventListener('click', () => this.searchArchive());
        
        // 手動登録
        document.getElementById('manualNewsForm').addEventListener('submit', (e) => this.submitManualNews(e));
        
        // モーダル
        document.getElementById('modalClose').addEventListener('click', () => this.closeModal('newsModal'));
        document.getElementById('settingsBtn').addEventListener('click', () => this.openSettings());
        document.getElementById('settingsModalClose').addEventListener('click', () => this.closeModal('settingsModal'));
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        
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
        // タブボタンの状態更新
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // タブコンテンツの表示切替
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
        
        this.currentTab = tabName;
        
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
            this.updatePagination(response.total_count, response.current_page);
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
        this.showLoading();
        
        try {
            const searchParams = {
                keyword: document.getElementById('searchKeyword').value,
                source: document.getElementById('sourceFilter').value,
                metal: document.getElementById('metalFilter').value,
                is_manual: document.getElementById('typeFilter').value,
                page: this.currentPage,
                per_page: this.newsPerPage
            };
            
            const response = await eel.search_news(searchParams)();
            this.displayNewsList(response.news, 'newsList');
            this.updatePagination(response.total_count, response.current_page);
        } catch (error) {
            this.showError('検索に失敗しました: ' + error.message);
        }
    }
    
    async searchArchive() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        if (!startDate || !endDate) {
            this.showError('開始日と終了日を指定してください');
            return;
        }
        
        try {
            const searchParams = {
                start_date: startDate,
                end_date: endDate,
                keyword: document.getElementById('searchKeyword').value,
                page: 1,
                per_page: this.newsPerPage
            };
            
            const response = await eel.search_archive(searchParams)();
            this.displayNewsList(response.news, 'archiveList');
        } catch (error) {
            this.showError('アーカイブ検索に失敗しました: ' + error.message);
        }
    }
    
    displayNewsList(news, containerId) {
        const container = document.getElementById(containerId);
        
        if (!news || news.length === 0) {
            container.innerHTML = '<div class="no-results">ニュースが見つかりませんでした</div>';
            return;
        }
        
        container.innerHTML = news.map(item => this.createNewsItemHTML(item)).join('');
        
        // ニュースアイテムのクリックイベント設定
        container.querySelectorAll('.news-item').forEach(item => {
            item.addEventListener('click', () => {
                const newsId = item.getAttribute('data-news-id');
                this.showNewsDetail(newsId);
            });
        });
    }
    
    createNewsItemHTML(news) {
        const publishTime = new Date(news.publish_time).toLocaleString('ja-JP');
        const acquireTime = new Date(news.acquire_time).toLocaleString('ja-JP');
        const isManual = news.is_manual;
        const preview = news.body ? news.body.substring(0, 200) + '...' : '';
        const metals = news.related_metals ? news.related_metals.split(',').map(m => m.trim()) : [];
        
        return `
            <div class="news-item" data-news-id="${news.news_id}">
                <div class="news-header">
                    <div class="news-title">${this.escapeHtml(news.title)}</div>
                    <div class="news-badges">
                        <span class="badge ${isManual ? 'badge-manual' : 'badge-refinitiv'}">
                            ${isManual ? '手動登録' : 'Refinitiv'}
                        </span>
                    </div>
                </div>
                
                <div class="news-meta">
                    <span class="news-source">${this.escapeHtml(news.source)}</span>
                    <span class="news-date">${publishTime}</span>
                </div>
                
                ${preview ? `<div class="news-preview">${this.escapeHtml(preview)}</div>` : ''}
                
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
                    </div>
                    
                    <div class="news-detail-body">
                        <h4>本文</h4>
                        <div class="news-body-content">
                            ${this.escapeHtml(news.body).replace(/\n/g, '<br>')}
                        </div>
                    </div>
                    
                    ${isManual ? `
                        <div class="news-actions">
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
    
    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
    }
    
    updatePagination(totalCount, currentPage) {
        const totalPages = Math.ceil(totalCount / this.newsPerPage);
        const pagination = document.getElementById('pagination');
        
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
        this.currentPage = page;
        this.performSearch();
    }
    
    updateStatus(message, type = 'success') {
        const statusText = document.getElementById('statusText');
        const statusDot = document.querySelector('.status-dot');
        
        statusText.textContent = message;
        statusDot.className = `status-dot ${type}`;
    }
    
    showLoading() {
        const container = document.getElementById('newsList');
        container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> 読み込み中...</div>';
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
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
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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