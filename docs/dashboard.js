// Sakana Dashboard Script - Vanilla JS
let currentCourse = 'kinan';
// let historyData = []; (removed)
let logData = [];
let seatChartInstance = null;
let dayChartInstance = null;

// Pagination state
let timelineExpanded = false;
let logsExpanded = false;

// Consts
const courseNames = {
    'kinan': 'WEST EXPRESS 銀河（紀南コース）',
    'sanin': 'WEST EXPRESS 銀河（山陰コース）',
    'sunrise': 'サンライズ出雲・瀬戸'
};
const weekdayKanji = ["日", "月", "火", "水", "木", "金", "土"];
const CHART_COLORS = ['#C55A11', '#E2A03F', '#F6C879', '#F9E0B7', '#2D3748', '#718096', '#CBD5E0', '#E2E8F0', '#EDF2F7', '#F7FAFC'];

// Init
let autoRefreshTimer = null;
document.addEventListener('DOMContentLoaded', () => {
    setupTheme();
    setupSidebar();
    loadData();
    startAutoRefresh();
});

function setupTheme() {
    const themeCheckbox = document.getElementById('theme-checkbox');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (prefersDark) {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeCheckbox.checked = true;
        Chart.defaults.color = '#F7FAFC';
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        themeCheckbox.checked = false;
        Chart.defaults.color = '#718096';
    }

    themeCheckbox.addEventListener('change', (e) => {
        const isDark = e.target.checked;
        document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
        
        
        Chart.defaults.color = isDark ? '#F7FAFC' : '#718096';
        if (seatChartInstance) seatChartInstance.update();
        if (dayChartInstance) {
            dayChartInstance.options.scales.x.ticks.color = Chart.defaults.color;
            dayChartInstance.options.scales.y.ticks.color = Chart.defaults.color;
            dayChartInstance.update();
        }
    });
}

function startAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = setInterval(() => {
        loadData();
    }, 300000); // 5 minutes
}

function setupSidebar() {
    const tabs = document.querySelectorAll('.tab-btn');
    const displayTitle = document.getElementById('display-title');
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.currentTarget.classList.add('active');
            currentCourse = e.currentTarget.dataset.course;
            displayTitle.textContent = courseNames[currentCourse];
            timelineExpanded = false;
            logsExpanded = false;
            
            // Close mobile menu
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
            
            loadData();
        });
    });

    menuToggle.addEventListener('click', () => {
        sidebar.classList.add('open');
        overlay.classList.add('show');
    });

    overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    });
}

async function loadData() {
    try {
        // history.json is merged into logData

        // Load log_{course}.json
        const logRes = await fetch(`log_${currentCourse}.json`);
        if (logRes.ok) {
            logData = await logRes.json();
        } else {
            logData = [];
        }

        updateDashboard();
    } catch (e) {
        console.error('Error loading data:', e);
        document.getElementById('last-updated').textContent = 'データ取得エラー';
    }
}

function updateDashboard() {
    updateLastUpdated();
    renderStatusTable();
    renderCharts();
    renderTimeline();
    renderLogs();
}

function formatDateStr(dateStr) {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    const y = dateStr.substring(0, 4);
    const m = parseInt(dateStr.substring(4, 6), 10);
    const d = parseInt(dateStr.substring(6, 8), 10);
    const dateObj = new Date(y, m - 1, d);
    const w = weekdayKanji[dateObj.getDay()];
    return `${m}/${d}(${w})`;
}

function formatISODate(isoStr) {
    const date = new Date(isoStr);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    const s = String(date.getSeconds()).padStart(2, '0');
    return `${y}-${m}-${d} ${h}:${min}:${s}`;
}

function updateLastUpdated() {
    if (logData.length > 0) {
        const lastLog = logData[logData.length - 1];
        document.getElementById('last-updated').textContent = `最終更新: ${formatISODate(lastLog.timestamp)}`;
    } else {
        document.getElementById('last-updated').textContent = 'データなし';
    }
}

/* ---------------------------------
   Status Table
--------------------------------- */
function renderStatusTable() {
    const tbody = document.querySelector('#status-table tbody');
    const theadTr = document.getElementById('status-table-header');
    
    tbody.innerHTML = '';
    theadTr.innerHTML = '';

    if (logData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">最近のデータがありません</td></tr>';
        return;
    }

    const latestTimestamp = logData[logData.length - 1].timestamp;
    const latestLogs = logData.filter(log => log.timestamp === latestTimestamp);

    const grouped = {};
    const seatTypes = new Set();

    latestLogs.forEach(log => {
        const key = `${log.train}_${log.target_date}_${log.depart}_${log.arrive}`;
        if (!grouped[key]) {
            grouped[key] = { train: log.train, date: log.target_date, depart: log.depart, arrive: log.arrive, seats: {} };
        }
        grouped[key].seats[log.seat_type] = log.result;
        seatTypes.add(log.seat_type);
    });

    const seatArray = Array.from(seatTypes);

    // Header
    let headHtml = '<th>列車名</th><th>対象日</th><th>区間</th>';
    seatArray.forEach(seat => {
        headHtml += `<th>${seat}</th>`;
    });
    theadTr.innerHTML = headHtml;

    // Body
    const sortedKeys = Object.keys(grouped).sort();
    
    const createRowHTML = (item) => {
        let html = `<tr><td data-label="列車名">${item.train}</td><td data-label="対象日"><strong>${formatDateStr(item.date)}</strong></td><td data-label="区間">${item.depart} → ${item.arrive}</td>`;
        seatArray.forEach(seat => {
            html += `<td data-label="${seat}">${getStatusBadge(item.seats[seat])}</td>`;
        });
        html += `</tr>`;
        return html;
    };

    const limit = 5;
    const topKeys = sortedKeys.slice(0, limit);
    
    topKeys.forEach(key => {
        tbody.innerHTML += createRowHTML(grouped[key]);
    });

    const card = tbody.closest('.card');
    let existingBtn = card.querySelector('.more-btn-container');
    if (existingBtn) existingBtn.remove();

    if (sortedKeys.length > limit) {
        const btnContainer = document.createElement('div');
        btnContainer.className = 'more-btn-container';
        btnContainer.style.textAlign = 'center';
        btnContainer.style.marginTop = '15px';
        const btn = document.createElement('button');
        btn.textContent = 'もっと見る';
        btn.className = 'btn-outline';
        btn.onclick = () => {
            let fullHtml = `<div class="table-container"><table><thead><tr>${headHtml}</tr></thead><tbody>`;
            sortedKeys.forEach(key => {
                fullHtml += createRowHTML(grouped[key]);
            });
            fullHtml += `</tbody></table></div>`;
            openModal('最近の空席状況', fullHtml);
        };
        btnContainer.appendChild(btn);
        card.appendChild(btnContainer);
    }
}

function getStatusBadge(status) {
    if (!status) return `<span class="status-badge status-err">-</span>`;
    const s = status.trim();
    if (s === '○' || s === '〇') return `<span class="status-badge status-o">〇</span>`;
    if (s === '△') return `<span class="status-badge status-tri">△</span>`;
    if (s === '×' || s.includes('なし')) return `<span class="status-badge status-x">×</span>`;
    return `<span class="status-badge status-err">!</span>`;
}

/* ---------------------------------
   Charts
--------------------------------- */
function renderCharts() {
    // Seat availability aggregation
    const seatCounts = {};
    const dayCounts = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 }; // Sun=0 to Sat=6
    const dayTotals = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 };

    logData.forEach(res => {
        // Seat Donut Data
        if (!seatCounts[res.seat_type]) {
            seatCounts[res.seat_type] = { total: 0, available: 0 };
        }
        seatCounts[res.seat_type].total++;
        
        const isAvail = (res.result === '○' || res.result === '〇' || res.result === '△');
        if (isAvail) seatCounts[res.seat_type].available++;

        // Day of Week Data (target date day of week)
        if (res.target_date && res.target_date.length === 8) {
            const y = parseInt(res.target_date.substring(0, 4), 10);
            const m = parseInt(res.target_date.substring(4, 6), 10) - 1;
            const d = parseInt(res.target_date.substring(6, 8), 10);
            const dayOfWeek = new Date(y, m, d).getDay();
            
            dayTotals[dayOfWeek]++;
            if (isAvail) {
                dayCounts[dayOfWeek]++;
            }
        }
    });

    // Donut Chart Setup
    const seatLabels = Object.keys(seatCounts);
    const seatData = seatLabels.map(label => {
        const d = seatCounts[label];
        return d.total > 0 ? ((d.available / d.total) * 100).toFixed(1) : 0;
    });

    if (seatChartInstance) seatChartInstance.destroy();
    const ctxSeat = document.getElementById('seatChart').getContext('2d');
    seatChartInstance = new Chart(ctxSeat, {
        type: 'doughnut',
        data: {
            labels: seatLabels,
            datasets: [{
                data: seatData,
                backgroundColor: CHART_COLORS,
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: { position: 'right', labels: { usePointStyle: true, font: { family: 'Inter' } } },
                tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.raw}%` } }
            }
        }
    });

    // Bar Chart Setup
    const dayLabels = ["日", "月", "火", "水", "木", "金", "土"];
    const dayData = [0,1,2,3,4,5,6].map(i => {
        return dayTotals[i] > 0 ? ((dayCounts[i] / dayTotals[i]) * 100).toFixed(1) : 0;
    });

    if (dayChartInstance) dayChartInstance.destroy();
    const ctxDay = document.getElementById('dayChart').getContext('2d');
    dayChartInstance = new Chart(ctxDay, {
        type: 'bar',
        data: {
            labels: dayLabels,
            datasets: [{
                label: '空席検知率 (%)',
                data: dayData,
                backgroundColor: '#C55A11',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: Math.max(...dayData) < 10 ? 10 : undefined, grid: { color: 'rgba(0,0,0,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

/* ---------------------------------
   Timeline
--------------------------------- */
function renderTimeline() {
    const container = document.getElementById('timeline-container');
    container.innerHTML = '';

    const events = [];
    logData.forEach(res => {
        if (res.result === '○' || res.result === '〇' || res.result === '△') {
            events.push({
                time: new Date(res.timestamp),
                dateStr: formatDateStr(res.target_date),
                seat: res.seat_type,
                status: res.result,
                dir: res.direction === 'kudari' ? '下り' : (res.direction === 'nobori' ? '上り' : ''),
                url: res.url
            });
        }
    });

    events.sort((a, b) => b.time - a.time);
    const limit = 5;
    const topEvents = events.slice(0, limit);

    if (topEvents.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:14px;">最近検知された空席はありません。</p>';
        return;
    }

    const createItemHTML = (ev) => {
        return `
            <div class="timeline-item">
                <div class="timeline-marker"></div>
                <span class="timeline-time">${formatISODate(ev.time.toISOString())}</span>
                <div class="timeline-content">
                    <strong>${ev.dateStr} ${ev.dir}</strong> の <strong>${ev.seat}</strong> に空き（${ev.status}）を検知しました。
                    <a href="${ev.url || 'https://e5489.jr-odekake.net/e5489/cspc/CBTopMenuPC'}" target="_blank" style="display: inline-block; margin-top: 5px; color: var(--primary); text-decoration: underline; font-size: 0.9em; font-weight: bold;"><i class="fa-solid fa-arrow-up-right-from-square"></i> 確認</a>
                </div>
            </div>
        `;
    };

    topEvents.forEach(ev => {
        container.innerHTML += createItemHTML(ev);
    });

    const card = container.closest('.card');
    let existingBtn = card.querySelector('.more-btn-container');
    if (existingBtn) existingBtn.remove();

    if (events.length > limit) {
        const btnContainer = document.createElement('div');
        btnContainer.className = 'more-btn-container';
        btnContainer.style.textAlign = 'center';
        btnContainer.style.marginTop = '15px';
        const btn = document.createElement('button');
        btn.textContent = 'もっと見る';
        btn.className = 'btn-outline';
        btn.onclick = () => {
            let fullHtml = `<div class="timeline" style="padding-top:10px;">`;
            events.forEach(ev => {
                fullHtml += createItemHTML(ev);
            });
            fullHtml += `</div>`;
            openModal('検知タイムライン', fullHtml);
        };
        btnContainer.appendChild(btn);
        card.appendChild(btnContainer);
    }
}

/* ---------------------------------
   Logs & Pagination
--------------------------------- */
function renderLogs() {
    const tbody = document.querySelector('#log-table tbody');
    tbody.innerHTML = '';

    if (logData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">ログデータがありません</td></tr>';
        document.getElementById('pagination-controls').innerHTML = '';
        return;
    }

    const groups = {};
    const sortedLogs = [...logData].reverse();
    const groupOrder = [];

    sortedLogs.forEach(log => {
        if (!groups[log.timestamp]) {
            groups[log.timestamp] = [];
            groupOrder.push(log.timestamp);
        }
        groups[log.timestamp].push(log);
    });

    const limit = 5;
    const currentGroupKeys = groupOrder.slice(0, limit);

    const createGroupHTML = (ts) => {
        const logsInGroup = groups[ts];
        const trainName = logsInGroup[0].train;
        const totalQueries = logsInGroup.length;
        const availableCount = logsInGroup.filter(l => l.result === '○' || l.result === '〇' || l.result === '△').length;
        
        let html = `
        <tr class="log-group-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? '' : 'none'; this.classList.toggle('open');">
            <td data-label="取得日時"><strong>${formatISODate(ts)}</strong></td>
            <td data-label="列車名">${trainName}</td>
            <td data-label="結果概要" colspan="3">照会数: ${totalQueries}件 / 空席検知: <strong style="color:var(--primary)">${availableCount}件</strong></td>
            <td data-label="詳細" style="text-align: right;"><i class="fa-solid fa-chevron-down"></i></td>
        </tr>
        <tr class="log-group-details" style="display: none;">
            <td colspan="6" style="padding:0; border:none;">
                <table style="margin: 0; box-shadow: none;"><tbody>
        `;
        logsInGroup.forEach(log => {
            html += `
                <tr>
                    <td data-label="区間">${log.depart} → ${log.arrive}</td>
                    <td data-label="対象日">${formatDateStr(log.target_date)}</td>
                    <td data-label="席種">${log.seat_type}</td>
                    <td data-label="結果">${getStatusBadge(log.result)}</td>
                </tr>
            `;
        });
        html += `</tbody></table></td></tr>`;
        return html;
    };

    currentGroupKeys.forEach((ts) => {
        tbody.innerHTML += createGroupHTML(ts);
    });

    const controls = document.getElementById('pagination-controls');
    controls.innerHTML = '';
    controls.style.display = 'flex';
    controls.style.justifyContent = 'center';
    controls.style.marginTop = '15px';

    if (groupOrder.length > limit) {
        const btn = document.createElement('button');
        btn.textContent = 'もっと見る';
        btn.className = 'btn-outline';
        btn.onclick = () => {
            let fullHtml = `<div class="table-container"><table><thead><tr><th>取得日時</th><th>列車名</th><th colspan="3">結果概要</th><th>詳細</th></tr></thead><tbody>`;
            groupOrder.forEach(ts => {
                fullHtml += createGroupHTML(ts);
            });
            fullHtml += `</tbody></table></div>`;
            openModal('アクセスログ', fullHtml);
        };
        controls.appendChild(btn);
    }
}

/* ---------------------------------
   Modal Logic
--------------------------------- */
function openModal(title, contentHtml) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = contentHtml;
    const overlay = document.getElementById('modal-overlay');
    overlay.style.display = 'flex';
    void overlay.offsetWidth; // trigger reflow
    overlay.classList.add('show');
}

function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    overlay.classList.remove('show');
    setTimeout(() => {
        overlay.style.display = 'none';
        document.getElementById('modal-body').innerHTML = ''; // clean up
    }, 300);
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('modal-close')?.addEventListener('click', closeModal);
    document.getElementById('modal-overlay')?.addEventListener('click', (e) => {
        if (e.target.id === 'modal-overlay') closeModal();
    });
});
