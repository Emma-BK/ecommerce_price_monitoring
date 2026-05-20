document.addEventListener('DOMContentLoaded', () => {
    // === DOM Elements ===
    const healthText = document.getElementById('health-text');
    const productsContainer = document.getElementById('products-container');
    const totalProductsEl = document.getElementById('total-products');
    
    const emptyDetail = document.getElementById('empty-detail');
    const productIntel = document.getElementById('product-intel');
    
    // Nav Elements
    const navDashboard = document.getElementById('nav-dashboard');
    const navProducts = document.getElementById('nav-products');
    const navAnalytics = document.getElementById('nav-analytics');
    const navAlerts = document.getElementById('nav-alerts');

    const views = {
        dashboard: document.getElementById('view-dashboard'),
        products: document.getElementById('view-products'),
        analytics: document.getElementById('view-analytics'),
        alerts: document.getElementById('view-alerts')
    };
    
    // Products Table View
    const fullProductsTable = document.getElementById('full-products-table');
    const productCountBadge = document.getElementById('product-count-badge');
    
    // Detail View Elements
    const detailName = document.getElementById('detail-name');
    const detailUrl = document.getElementById('detail-url');
    const detailPrice = document.getElementById('detail-price');
    const detailImg = document.getElementById('detail-img');
    const volatilityVal = document.getElementById('volatility-val');
    const forecastTrend = document.getElementById('forecast-trend');
    
    // Action Buttons
    const btnTrain = document.getElementById('btn-train');
    const btnFav = document.getElementById('btn-fav');
    const favIcon = document.getElementById('fav-icon');
    
    // Analytics Elements
    const marketTrendVal = document.getElementById('market-trend-val');
    const favoriteCount = document.getElementById('favorite-count');
    const lastSyncTime = document.getElementById('last-sync-time');
    const categoryStatsList = document.getElementById('category-stats-list');
    
    // Alerts Elements
    const alertCountBadge = document.getElementById('alert-count-badge');
    const alertsTableBody = document.getElementById('alerts-table-body');

    // Modal Elements
    const addModal = document.getElementById('add-modal');
    const btnAddProduct = document.getElementById('add-product-btn');
    const btnCloseModal = document.getElementById('close-modal');
    const addForm = document.getElementById('add-form');

    // === State ===
    let currentProductId = null;
    let priceChart = null;
    let categoryChart = null;
    let productsList = [];

    // === Initialization ===
    init();

    async function init() {
        await checkHealth();
        await loadProducts();
        setupEventListeners();
        loadGlobalStats();
    }

    // === UI Utilities ===
    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span class="material-symbols-outlined">${type === 'success' ? 'check_circle' : 'error'}</span>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // === API Calls ===
    async function checkHealth() {
        try {
            const res = await fetch('/api/v1/health');
            if (res.ok) {
                const data = await res.json();
                healthText.textContent = `System API ${data.status}`;
            } else {
                healthText.textContent = 'System Offline';
            }
        } catch (e) {
            healthText.textContent = 'Connection Error';
            console.error('Health Check Error', e);
        }
    }

    async function loadProducts() {
        try {
            productsContainer.innerHTML = '<div class="loading">Fetching products...</div>';
            const res = await fetch('/api/v1/products');
            productsList = await res.json();
            
            totalProductsEl.textContent = productsList.length;
            renderProducts(productsList);
        } catch (e) {
            productsContainer.innerHTML = '<div class="loading">Error loading products.</div>';
        }
    }

    async function loadProductDetails(product) {
        currentProductId = product.id;
        
        // UI Updates
        emptyDetail.classList.add('hidden');
        productIntel.classList.remove('hidden');
        detailName.textContent = product.name;
        detailUrl.href = product.url;
        detailImg.src = product.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=300&q=80';
        detailImg.onerror = () => { detailImg.src = 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=300&q=80'; };
        detailPrice.textContent = '...';
        volatilityVal.textContent = '...';
        forecastTrend.textContent = '...';
        
        // Update Favorite State
        favIcon.textContent = product.is_favorite ? 'favorite' : 'favorite_border';
        btnFav.classList.toggle('active', product.is_favorite);

        // Update selection state
        document.querySelectorAll('.product-item').forEach(el => {
            el.classList.remove('selected');
            if (el.dataset.id == product.id) el.classList.add('selected');
        });

        // 1. Fetch Latest Price & History
        try {
            const histRes = await fetch(`/api/v1/products/${product.id}/prices`);
            const history = await histRes.json();
            
            if (history && history.length > 0) {
                detailPrice.textContent = history[0].price.toFixed(2);
            } else {
                detailPrice.textContent = 'N/A';
            }

            // Draw Chart
            renderChart(history);
        } catch(e) { console.error('History Error', e); }

        // 2. Fetch Volatility
        try {
            const volRes = await fetch(`/api/v1/analytics/${product.id}/volatility`);
            const volData = await volRes.json();
            if (volData["30_day_volatility"] !== undefined) {
                volatilityVal.textContent = volData["30_day_volatility"].toFixed(2) + ' €';
            }
        } catch (e) { console.error('Volatility Error', e); }
    }

    async function toggleFavorite() {
        if (!currentProductId) return;
        try {
            const res = await fetch(`/api/v1/products/${currentProductId}/favorite`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                favIcon.textContent = data.is_favorite ? 'favorite' : 'favorite_border';
                btnFav.classList.toggle('active', data.is_favorite);
                showToast(data.is_favorite ? "Added to Followed Items" : "Removed from Followed Items");
                loadProducts(); // Refresh list to update favorite flags
                loadGlobalStats();
            }
        } catch (e) { showToast("Failed to update favorite status", "error"); }
    }

    function exportCSV() {
        if (!currentProductId) return;
        window.location.href = `/api/v1/products/${currentProductId}/export`;
        showToast("Exporting price history...");
    }

    async function triggerTraining() {
        if (!currentProductId) return;
        
        const originalText = btnTrain.innerHTML;
        btnTrain.innerHTML = '<span class="material-symbols-outlined spin">sync</span> AI Thinking...';
        btnTrain.disabled = true;

        try {
            const trainRes = await fetch(`/api/v1/predict/train/${currentProductId}`, { method: 'POST' });
            
            if(trainRes.ok) {
                const predRes = await fetch(`/api/v1/predict/${currentProductId}`);
                const predictions = await predRes.json();
                
                if (predictions && predictions.length > 0) {
                    const latestPriceText = detailPrice.textContent.replace('€', '').trim();
                    const latestPrice = parseFloat(latestPriceText);
                    
                    if (!isNaN(latestPrice)) {
                        const avgForecast = predictions.reduce((sum, p) => sum + p.predicted_price, 0) / predictions.length;
                        const diff = ((avgForecast - latestPrice) / latestPrice) * 100;
                        
                        if (diff > 0.5) {
                            forecastTrend.textContent = `↑ ${diff.toFixed(1)}% (Forecast €${avgForecast.toFixed(2)})`;
                            forecastTrend.style.color = '#ff4d88';
                        } else if (diff < -0.5) {
                            forecastTrend.textContent = `↓ ${Math.abs(diff).toFixed(1)}% (Forecast €${avgForecast.toFixed(2)})`;
                            forecastTrend.style.color = '#ff85a1';
                        } else {
                            forecastTrend.textContent = `Stable (Forecast €${avgForecast.toFixed(2)})`;
                        }
                    } else {
                        forecastTrend.textContent = 'Predictions available';
                    }
                    
                    addPredictionsToChart(predictions);
                    showToast("AI Model trained & projections updated");
                } else {
                    showToast("Model trained but not enough data for 7-day forecast", "error");
                }
            } else {
                showToast("Insufficient data for AI model", "error");
            }
        } catch (e) {
            console.error("Training Error", e);
            showToast("Training failed", "error");
        } finally {
            btnTrain.innerHTML = originalText;
            btnTrain.disabled = false;
        }
    }

    // === Global Analytics & Alerts ===
    async function loadGlobalStats() {
        try {
            const res = await fetch('/api/v1/analytics/global');
            const data = await res.json();
            
            const totalEl = document.getElementById('total-products');
            const discEl = document.getElementById('active-discounts');
            const trainedEl = document.getElementById('models-trained');
            
            if (totalEl) totalEl.textContent = data.total_products;
            if (discEl) discEl.textContent = data.active_discounts;
            if (trainedEl) trainedEl.textContent = data.models_trained;
        } catch(e) { console.error("Global Stats Error", e); }
    }

    async function loadAnalytics() {
        try {
            const res = await fetch('/api/v1/analytics/categories');
            const data = await res.json();
            
            // Render category chart
            renderCategoryChart(data);
            
            // Render list
            categoryStatsList.innerHTML = data.map(c => `
                <div class="category-stat-item">
                    <span>${c.category}</span>
                    <div class="stat-values">
                        <span class="count">${c.count} items</span>
                        <span class="price">avg €${c.avg_price}</span>
                    </div>
                </div>
            `).join('');
        } catch(e) {}
    }

    async function loadAlerts() {
        try {
            const res = await fetch('/api/v1/alerts');
            const alerts = await res.json();
            
            alertCountBadge.textContent = `${alerts.length} Alerts`;
            alertsTableBody.innerHTML = alerts.map(a => `
                <tr>
                    <td><strong>${a.name}</strong></td>
                    <td>€${a.old_avg}</td>
                    <td style="color:var(--pink); font-weight:700">€${a.price}</td>
                    <td><span class="badge" style="background:#ff85a1">- ${a.drop_percent}%</span></td>
                    <td>${new Date(a.timestamp).toLocaleDateString()}</td>
                    <td><button class="btn-view" data-id="${a.product_id}">View</button></td>
                </tr>
            `).join('');

            document.querySelectorAll('.btn-view').forEach(btn => {
                btn.addEventListener('click', () => {
                    const product = productsList.find(p => p.id == btn.dataset.id);
                    if (product) {
                        switchTab(navDashboard, views.dashboard);
                        loadProductDetails(product);
                    }
                });
            });
        } catch(e) {}
    }

    // === Renderers ===
    function renderProducts(products) {
        if(products.length === 0) {
            productsContainer.innerHTML = '<div class="loading">No products tracked yet.</div>';
            return;
        }

        productsContainer.innerHTML = products.map(p => `
            <div class="product-item" data-id="${p.id}">
                <div class="product-thumb">
                    <img src="${p.image_url || 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=50&q=80'}" 
                         onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=50&q=80'" 
                         alt="">
                </div>
                <div class="product-meta">
                    <p>${p.name} ${p.is_favorite ? '❤️' : ''}</p>
                    <span>${p.category || 'General'}</span>
                </div>
                <div class="product-price">
                    <span class="material-symbols-outlined">chevron_right</span>
                </div>
            </div>
        `).join('');

        document.querySelectorAll('.product-item').forEach(el => {
            el.addEventListener('click', () => {
                const product = products.find(p => p.id == el.dataset.id);
                loadProductDetails(product);
            });
        });

        renderProductsTable(products);
    }

    function renderProductsTable(products) {
        if(!fullProductsTable) return;
        productCountBadge.textContent = `${products.length} Products`;
        
        fullProductsTable.innerHTML = products.map(p => `
            <tr>
                <td>#${p.id}</td>
                <td style="font-weight:600">${p.name}</td>
                <td><span class="tag">${p.category || 'General'}</span></td>
                <td><span id="table-price-${p.id}">---</span></td>
                <td><a href="${p.url}" target="_blank" class="external-link">Link</a></td>
                <td>
                    <button class="btn-delete" data-id="${p.id}"><span class="material-symbols-outlined">delete</span></button>
                </td>
            </tr>
        `).join('');

        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = btn.dataset.id;
                if(confirm(`Are you sure you want to stop tracking product #${id}?`)) {
                    await deleteProduct(id);
                }
            });
        });

        products.forEach(async p => {
            try {
                const res = await fetch(`/api/v1/products/${p.id}/prices/latest`);
                if(res.ok) {
                   const price = await res.json();
                   const el = document.getElementById(`table-price-${p.id}`);
                   if(el) el.textContent = `${price.price.toFixed(2)} €`;
                }
            } catch(e) {}
        });
    }

    async function deleteProduct(id) {
        try {
            const res = await fetch(`/api/v1/products/${id}`, { method: 'DELETE' });
            if (res.ok) {
                showToast("Product deleted successfully");
                await loadProducts();
                if (currentProductId == id) {
                    productIntel.classList.add('hidden');
                    emptyDetail.classList.remove('hidden');
                }
            }
        } catch (e) { showToast("Failed to delete product", "error"); }
    }

    function renderChart(historyData) {
        const ctx = document.getElementById('priceChart').getContext('2d');
        if (priceChart) priceChart.destroy();

        const sorted = [...historyData].reverse();
        const labels = sorted.map(h => {
            const d = new Date(h.timestamp);
            return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${d.getMinutes()}`;
        });
        const data = sorted.map(h => h.price);

        priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Historical Price (€)',
                    data: data,
                    borderColor: '#ff4d88',
                    backgroundColor: 'rgba(255, 77, 136, 0.1)',
                    borderWidth: 3,
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: '#ff4d88'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#9e8d95' }, grid: { display: false } },
                    y: { ticks: { color: '#9e8d95' }, grid: { color: 'rgba(0,0,0,0.03)' } }
                }
            }
        });
    }

    function addPredictionsToChart(predictions) {
        if (!priceChart) return;
        if (priceChart.data.datasets.length > 1) priceChart.data.datasets.pop();

        const histLength = priceChart.data.labels.length;
        const predDataArray = Array(histLength - 1).fill(null);
        predDataArray.push(priceChart.data.datasets[0].data[histLength - 1]);

        predictions.forEach(p => {
            priceChart.data.labels.push(p.date.substring(5));
            predDataArray.push(p.predicted_price);
        });

        priceChart.data.datasets.push({
            label: 'AI Forecast',
            data: predDataArray,
            borderColor: '#9650ff',
            borderDash: [5, 5],
            borderWidth: 2,
            tension: 0.3,
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#9650ff'
        });
        priceChart.update();
    }

    function renderCategoryChart(data) {
        const ctx = document.getElementById('categoryChart').getContext('2d');
        if (categoryChart) categoryChart.destroy();
        
        categoryChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.category),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: ['#ff4d88', '#9650ff', '#ff85a1', '#e0c8d0', '#ffc2d1'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } } }
            }
        });
    }

    // === Navigation Logic ===
    function switchTab(activeNav, activeView) {
        Object.values(views).forEach(v => v.classList.add('hidden'));
        [navDashboard, navProducts, navAnalytics, navAlerts].forEach(n => n.classList.remove('active'));
        
        activeNav.classList.add('active');
        activeView.classList.remove('hidden');

        if (activeView === views.analytics) loadAnalytics();
        if (activeView === views.alerts) loadAlerts();
        if (activeView === views.dashboard) loadGlobalStats();
    }

    // === Events ===
    function setupEventListeners() {
        navDashboard.addEventListener('click', (e) => { e.preventDefault(); switchTab(navDashboard, views.dashboard); });
        navProducts.addEventListener('click', (e) => { e.preventDefault(); switchTab(navProducts, views.products); });
        navAnalytics.addEventListener('click', (e) => { e.preventDefault(); switchTab(navAnalytics, views.analytics); });
        navAlerts.addEventListener('click', (e) => { e.preventDefault(); switchTab(navAlerts, views.alerts); });

        btnTrain.addEventListener('click', triggerTraining);
        btnFav.addEventListener('click', toggleFavorite);
        
        btnAddProduct.addEventListener('click', () => addModal.classList.remove('hidden'));
        btnCloseModal.addEventListener('click', () => addModal.classList.add('hidden'));

        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                name: document.getElementById('input-name').value,
                url: document.getElementById('input-url').value,
                category: document.getElementById('input-cat').value || 'General'
            };

            try {
                const res = await fetch('/api/v1/products', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    showToast("Product added to tracker");
                    addModal.classList.add('hidden');
                    addForm.reset();
                    await loadProducts();
                    switchTab(navDashboard, views.dashboard);
                } else {
                    const err = await res.json();
                    showToast(err.detail, "error");
                }
            } catch (e) { showToast("Network error", "error"); }
        });
    }
});
