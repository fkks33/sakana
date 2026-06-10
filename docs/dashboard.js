// Sakana Dashboard Script - Vanilla JS
let currentCourse = 'sanin';
let historyData = [];
let logData = [];
let seatChartInstance = null;
let dayChartInstance = null;

// Pagination state
let currentPage = 1;
const itemsPerPage = 100;

// Consts
const courseNames = {
    'kinan': 'WEST EXPRESS 銀河（紀南コース）',
    'sanin': 'WEST EXPRESS 銀河（山陰コース）',
    'sunrise': 'サンライズ出雲・瀬戸'
};
const weekdayKanji = ["日", "月", "火", "水", "木", "金", "土"];
const CHART_COLORS = ['#C55A11', '#E2A03F', '#F6C879', '#F9E0B7', '#2D3748', '#718096', '#CBD5E0', '#E2E8F0', '#EDF2F7', '#F7FAFC'];

// Init
document.addEventListener('DOMContentLoaded', () => {
    setupSidebar();
    loadData();
});

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
            currentPage = 1;
            
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
        // Load history.json (for status, charts, timeline)
        const histRes = await fetch('history.json');
        if (histRes.ok) {
            historyData = await histRes.json();
        } else {
            historyData = [];
        }

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
    const courseHist = historyData.filter(d => d.course === currentCourse);
    const tbody = document.querySelector('#status-table tbody');
    const theadTr = document.getElementById('status-table-header');
    
    tbody.innerHTML = '';
    theadTr.innerHTML = '';

    if (courseHist.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">最近のデータがありません</td></tr>';
        return;
    }

    const lastRun = courseHist[courseHist.length - 1];
    const grouped = {};
    const seatTypes = new Set();

    lastRun.results.forEach(res => {
        const key = `${res.date}_${res.direction}`;
        if (!grouped[key]) {
            grouped[key] = { date: res.date, direction: res.direction, seats: {} };
        }
        grouped[key].seats[res.seat] = res.status;
        seatTypes.add(res.seat);
    });

    const seatArray = Array.from(seatTypes);

    // Header
    let headHtml = '<th>対象日</th><th>方向</th>';
    seatArray.forEach(seat => {
        headHtml += `<th>${seat}</th>`;
    });
    theadTr.innerHTML = headHtml;

    // Body
    const sortedKeys = Object.keys(grouped).sort();
    sortedKeys.forEach(key => {
        const item = grouped[key];
        const tr = document.createElement('tr');
        
        const dirStr = item.direction === 'kudari' ? '下り' : (item.direction === 'nobori' ? '上り' : 'ー');
        let html = `<td><strong>${formatDateStr(item.date)}</strong></td><td>${dirStr}</td>`;
        
        seatArray.forEach(seat => {
            html += `<td>${getStatusBadge(item.seats[seat])}</td>`;
        });
        
        tr.innerHTML = html;
        tbody.appendChild(tr);
    });
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
    const courseHist = historyData.filter(d => d.course === currentCourse);
    
    // Seat availability aggregation
    const seatCounts = {};
    const dayCounts = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 }; // Sun=0 to Sat=6
    const dayTotals = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 };

    courseHist.forEach(run => {
        run.results.forEach(res => {
            // Seat Donut Data
            if (!seatCounts[res.seat]) {
                seatCounts[res.seat] = { total: 0, available: 0 };
            }
            seatCounts[res.seat].total++;
            
            const isAvail = (res.status === '○' || res.status === '〇' || res.status === '△');
            if (isAvail) seatCounts[res.seat].available++;

            // Day of Week Data (target date day of week)
            if (res.date && res.date.length === 8) {
                const y = parseInt(res.date.substring(0, 4), 10);
                const m = parseInt(res.date.substring(4, 6), 10) - 1;
                const d = parseInt(res.date.substring(6, 8), 10);
                const dayOfWeek = new Date(y, m, d).getDay();
                
                dayTotals[dayOfWeek]++;
                if (isAvail) {
                    dayCounts[dayOfWeek]++;
                }
            }
        });
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
    const courseHist = historyData.filter(d => d.course === currentCourse);
    const container = document.getElementById('timeline-container');
    container.innerHTML = '';

    const events = [];
    courseHist.forEach(run => {
        const time = new Date(run.timestamp);
        run.results.forEach(res => {
            if (res.status === '○' || res.status === '〇' || res.status === '△') {
                events.push({
                    time: time,
                    dateStr: formatDateStr(res.date),
                    seat: res.seat,
                    status: res.status,
                    dir: res.direction === 'kudari' ? '下り' : (res.direction === 'nobori' ? '上り' : '')
                });
            }
        });
    });

    events.sort((a, b) => b.time - a.time);
    const topEvents = events.slice(0, 10);

    if (topEvents.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:14px;">最近検知された空席はありません。</p>';
        return;
    }

    topEvents.forEach(ev => {
        const item = document.createElement('div');
        item.className = 'timeline-item';
        item.innerHTML = `
            <div class="timeline-marker"></div>
            <span class="timeline-time">${formatISODate(ev.time.toISOString())}</span>
            <div class="timeline-content">
                <strong>${ev.dateStr} ${ev.dir}</strong> の <strong>${ev.seat}</strong> に空き（${ev.status}）を検知しました。
            </div>
        `;
        container.appendChild(item);
    });
}

/* ---------------------------------
   Logs & Pagination
--------------------------------- */
function renderLogs() {
    // logData is already filtered to the course by loadData()
    // Sort reverse chronological
    const sortedLogs = [...logData].reverse();
    
    const totalItems = sortedLogs.length;
    const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
    
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIdx = (currentPage - 1) * itemsPerPage;
    const endIdx = startIdx + itemsPerPage;
    const currentLogs = sortedLogs.slice(startIdx, endIdx);

    const tbody = document.querySelector('#log-table tbody');
    tbody.innerHTML = '';

    if (currentLogs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">ログデータがありません</td></tr>';
    } else {
        currentLogs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${formatISODate(log.timestamp)}</td>
                <td>${log.train}</td>
                <td>${log.depart} → ${log.arrive}</td>
                <td>${formatDateStr(log.target_date)}</td>
                <td>${log.seat_type}</td>
                <td>${getStatusBadge(log.result)}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    renderPagination(totalPages);
}

function renderPagination(totalPages) {
    const controls = document.getElementById('pagination-controls');
    controls.innerHTML = '';

    if (totalPages <= 1) return;

    // Prev
    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn';
    prevBtn.innerHTML = '<i class="fa-solid fa-chevron-left"></i>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => { currentPage--; renderLogs(); };
    controls.appendChild(prevBtn);

    // Info
    const info = document.createElement('span');
    info.className = 'page-info';
    info.textContent = `${currentPage} / ${totalPages} ページ`;
    controls.appendChild(info);

    // Next
    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn';
    nextBtn.innerHTML = '<i class="fa-solid fa-chevron-right"></i>';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => { currentPage++; renderLogs(); };
    controls.appendChild(nextBtn);
}
