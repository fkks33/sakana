// Ginga Availability Dashboard Script
let historyData = [];
let currentCourse = 'kinan';
let seatChart = null;
let timeChart = null;

// 日本語の曜日マッピング
const weekdayKanji = ["日", "月", "火", "水", "木", "金", "土"];

document.addEventListener('DOMContentLoaded', () => {
    // タブクリックイベントの設定
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            tabButtons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentCourse = e.target.dataset.course;
            updateDashboard();
        });
    });

    // データの読み込み
    fetchHistoryData();
});

async function fetchHistoryData() {
    try {
        const response = await fetch('history.json');
        if (!response.ok) {
            throw new Error('履歴データの取得に失敗しました。');
        }
        historyData = await response.json();
        
        // 最終更新時間の更新
        if (historyData.length > 0) {
            const lastRun = historyData[historyData.length - 1];
            const lastUpdatedTime = new Date(lastRun.timestamp);
            document.getElementById('last-updated').textContent = 
                `最終更新: ${formatDate(lastUpdatedTime)}`;
        } else {
            document.getElementById('last-updated').textContent = 'データなし';
        }

        updateDashboard();
    } catch (error) {
        console.error('Error fetching history:', error);
        document.getElementById('last-updated').textContent = 'ロードエラー';
        showTableMessage('データのロードに失敗しました。');
    }
}

function updateDashboard() {
    // 指定コースのデータのみフィルタリング
    const courseData = historyData.filter(d => d.course === currentCourse);
    
    if (courseData.length === 0) {
        showTableMessage('このコースの履歴データはありません。');
        clearCharts();
        clearTimeline();
        return;
    }

    // 最新の空席状況テーブルを描画
    renderStatusTable(courseData);

    // 席種別の空席出現率を描画
    renderSeatChart(courseData);

    // 時間帯別の空席傾向を描画
    renderTimeChart(courseData);

    // 空席タイムラインを描画
    renderTimeline(courseData);
}

function showTableMessage(message) {
    const tbody = document.querySelector('#current-status-table tbody');
    tbody.innerHTML = `<tr><td colspan="6" class="text-center">${message}</td></tr>`;
}

function formatDate(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    const s = String(date.getSeconds()).padStart(2, '0');
    const w = weekdayKanji[date.getDay()];
    return `${y}-${m}-${d}(${w}) ${h}:${min}:${s}`;
}

function renderStatusTable(courseData) {
    const tbody = document.querySelector('#current-status-table tbody');
    tbody.innerHTML = '';

    // 最も新しい実行データを使用
    const lastRun = courseData[courseData.length - 1];
    
    // 日付と方向ごとに座席ステータスをマッピング
    // キー: {date}_{direction}
    const grouped = {};

    lastRun.results.forEach(res => {
        const key = `${res.date}_${res.direction}`;
        if (!grouped[key]) {
            grouped[key] = {
                date: res.date,
                direction: res.direction,
                seats: {}
            };
        }
        grouped[key].seats[res.seat] = res.status;
    });

    // 曜日の計算とキー順での並び替え
    const sortedKeys = Object.keys(grouped).sort();

    if (sortedKeys.length === 0) {
        showTableMessage('有効な最新データがありません。');
        return;
    }

    sortedKeys.forEach(key => {
        const item = grouped[key];
        const dateObj = new Date(
            parseInt(item.date.substring(0, 4)),
            parseInt(item.date.substring(4, 6)) - 1,
            parseInt(item.date.substring(6, 8))
        );
        const weekday = weekdayKanji[dateObj.getDay()];
        const dateStr = `${item.date.substring(4, 6)}/${item.date.substring(6, 8)}(${weekday})`;
        const directionStr = item.direction === 'kudari' ? '京都 → 新宮 (下り)' : '新宮 → 京都 (上り)';
        const directionClass = item.direction === 'kudari' ? 'kudari-route' : 'nobori-route';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${dateStr}</strong></td>
            <td><span class="route-label ${directionClass}">${directionStr}</span></td>
            <td>${getStatusIndicator(item.seats['クシェット'])}</td>
            <td>${getStatusIndicator(item.seats['ファーストシート'])}</td>
            <td>${getStatusIndicator(item.seats['プレミアルーム1'])}</td>
            <td>${getStatusIndicator(item.seats['プレミアルーム2'])}</td>
        `;
        tbody.appendChild(tr);
    });
}

function getStatusIndicator(status) {
    if (!status) return '<span class="seat-status-indicator unavailable">-</span>';
    
    // 全角半角の揺れを考慮
    const s = status.trim();
    if (s === '○' || s === '〇') {
        return '<span class="seat-status-indicator available">○</span>';
    } else if (s === '△') {
        return '<span class="seat-status-indicator few">△</span>';
    } else if (s === '×') {
        return '<span class="seat-status-indicator unavailable">×</span>';
    } else if (s === '取得エラー') {
        return '<span class="seat-status-indicator error">!</span>';
    } else {
        return `<span class="seat-status-indicator unavailable" title="${status}">-</span>`;
    }
}

function renderSeatChart(courseData) {
    const seatCounts = {
        'クシェット': { total: 0, available: 0 },
        'ファーストシート': { total: 0, available: 0 },
        'プレミアルーム1': { total: 0, available: 0 },
        'プレミアルーム2': { total: 0, available: 0 }
    };

    // 過去のすべての実行結果を巡回
    courseData.forEach(run => {
        run.results.forEach(res => {
            const seatName = res.seat;
            if (seatCounts[seatName]) {
                seatCounts[seatName].total++;
                if (res.status === '○' || res.status === '〇' || res.status === '△') {
                    seatCounts[seatName].available++;
                }
            }
        });
    });

    const labels = Object.keys(seatCounts);
    const dataValues = labels.map(label => {
        const seat = seatCounts[label];
        return seat.total > 0 ? Math.round((seat.available / seat.total) * 100) : 0;
    });

    if (seatChart) {
        seatChart.destroy();
    }

    const ctx = document.getElementById('seat-availability-chart').getContext('2d');
    seatChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataValues,
                backgroundColor: [
                    '#00e676', // クシェット
                    '#0070f3', // ファーストシート
                    '#00f5ff', // プレミアルーム1
                    '#ffea00'  // プレミアルーム2
                ],
                borderWidth: 2,
                borderColor: '#111b3d'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#8a99ad',
                        font: { family: 'Inter' }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: 空席率 ${context.raw}%`;
                        }
                    }
                }
            }
        }
    });
}

function renderTimeChart(courseData) {
    // 2時間ごとの時間帯（6:00, 8:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00）を集計
    // 空席が検知された回数を集計
    const hours = ['06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'];
    const timeCounts = Array(hours.length).fill(0);

    courseData.forEach(run => {
        // 実行日時の「時」を取得
        const timeObj = new Date(run.timestamp);
        const hour = timeObj.getHours();

        // 最も近い時間枠のインデックスを見つける
        let matchIndex = -1;
        let minDiff = 24;

        hours.forEach((hStr, idx) => {
            const hVal = parseInt(hStr.split(':')[0]);
            const diff = Math.abs(hour - hVal);
            if (diff < minDiff) {
                minDiff = diff;
                matchIndex = idx;
            }
        });

        if (matchIndex !== -1 && minDiff <= 1) { // 1時間以内のズレのみ許容
            // その回で空席が1つでもあったかどうか
            let hasAvailable = false;
            run.results.forEach(res => {
                if (res.status === '○' || res.status === '〇' || res.status === '△') {
                    hasAvailable = true;
                }
            });

            if (hasAvailable) {
                timeCounts[matchIndex]++;
            }
        }
    });

    if (timeChart) {
        timeChart.destroy();
    }

    const ctx = document.getElementById('time-availability-chart').getContext('2d');
    timeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hours,
            datasets: [{
                label: '空席検知回数',
                data: timeCounts,
                backgroundColor: 'rgba(0, 112, 243, 0.4)',
                borderColor: '#0070f3',
                borderWidth: 1.5,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#8a99ad', stepSize: 1 }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#8a99ad' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

function renderTimeline(courseData) {
    const list = document.getElementById('timeline-list');
    list.innerHTML = '';

    const timelineItems = [];

    // 過去のデータを走査し、空席（○ or △）のレコードを抽出
    courseData.forEach(run => {
        const runTime = new Date(run.timestamp);
        
        run.results.forEach(res => {
            if (res.status === '○' || res.status === '〇' || res.status === '△') {
                const dateObj = new Date(
                    parseInt(res.date.substring(0, 4)),
                    parseInt(res.date.substring(4, 6)) - 1,
                    parseInt(res.date.substring(6, 8))
                );
                const dateStr = `${res.date.substring(4, 6)}/${res.date.substring(6, 8)}(${weekdayKanji[dateObj.getDay()]})`;
                const directionStr = res.direction === 'kudari' ? '京都→新宮' : '新宮→京都';

                timelineItems.push({
                    timestamp: runTime,
                    content: `【空席検知】 ${dateStr} ${directionStr} の <strong>${res.seat}</strong> に空き（${res.status}）を検知しました。`
                });
            }
        });
    });

    // タイムスタンプ降順でソート
    timelineItems.sort((a, b) => b.timestamp - a.timestamp);

    // 最大15件表示
    const displayItems = timelineItems.slice(0, 15);

    if (displayItems.length === 0) {
        list.innerHTML = '<li class="timeline-empty">過去30日以内に検知された空席はありません。</li>';
        return;
    }

    displayItems.forEach(item => {
        const li = document.createElement('li');
        li.className = 'timeline-item';
        li.innerHTML = `
            <span class="timeline-time">${formatDate(item.timestamp)}</span>
            <span class="timeline-content">${item.content}</span>
        `;
        list.appendChild(li);
    });
}

function clearCharts() {
    if (seatChart) {
        seatChart.destroy();
        seatChart = null;
    }
    if (timeChart) {
        timeChart.destroy();
        timeChart = null;
    }
}

function clearTimeline() {
    const list = document.getElementById('timeline-list');
    list.innerHTML = '<li class="timeline-empty">過去30日以内に検知された空席はありません。</li>';
}
