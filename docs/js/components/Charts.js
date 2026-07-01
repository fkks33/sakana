import store from '../store.js';

let seatChartInstance = null;
let dayChartInstance = null;

const CHART_COLORS = ['#C55A11', '#E2A03F', '#F6C879', '#F9E0B7', '#2D3748', '#718096', '#CBD5E0'];

export function renderCharts() {
    const { logs, theme } = store.state;
    
    const isDark = theme === 'dark';
    Chart.defaults.color = isDark ? '#94A3B8' : '#475569';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

    const seatCounts = {};
    const dayCounts = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 };
    const dayTotals = { 0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0 };

    logs.forEach(res => {
        if (!seatCounts[res.seat_type]) {
            seatCounts[res.seat_type] = { total: 0, available: 0 };
        }
        seatCounts[res.seat_type].total++;
        
        const isAvail = (res.result === '○' || res.result === '〇' || res.result === '△');
        if (isAvail) seatCounts[res.seat_type].available++;

        if (res.target_date && res.target_date.length === 8) {
            const y = parseInt(res.target_date.substring(0, 4), 10);
            const m = parseInt(res.target_date.substring(4, 6), 10) - 1;
            const d = parseInt(res.target_date.substring(6, 8), 10);
            const dayOfWeek = new Date(y, m, d).getDay();
            
            dayTotals[dayOfWeek]++;
            if (isAvail) dayCounts[dayOfWeek]++;
        }
    });

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
                legend: { position: 'right', labels: { usePointStyle: true } },
                tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.raw}%` } }
            }
        }
    });

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
                y: { beginAtZero: true, grid: { color: gridColor } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

export function initCharts() {
    store.subscribe(() => {
        renderCharts();
    });
}
