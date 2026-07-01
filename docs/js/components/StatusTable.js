import store from '../store.js';
import { formatDateStr, getStatusBadge } from '../utils.js';
import { showModal } from './Modal.js';

export function renderStatusTable() {
    const container = document.getElementById('status-table-container');
    const { logs } = store.state;

    if (!logs || logs.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); text-align: center; padding: 20px;">データがありません</p>';
        return;
    }

    const latestTimestamp = logs[logs.length - 1].timestamp;
    const latestLogs = logs.filter(l => l.timestamp === latestTimestamp);

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
    const sortedKeys = Object.keys(grouped).sort();

    const renderRows = (keys) => keys.map(key => {
        const item = grouped[key];
        let row = `<tr>
            <td>${item.train}</td>
            <td><strong>${formatDateStr(item.date)}</strong></td>
            <td>${item.depart} → ${item.arrive}</td>`;
        seatArray.forEach(seat => {
            row += `<td>${getStatusBadge(item.seats[seat])}</td>`;
        });
        row += '</tr>';
        return row;
    }).join('');

    const limit = 5;
    const topKeys = sortedKeys.slice(0, limit);

    let html = `
        <div class="table-responsive">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>列車名</th><th>対象日</th><th>区間</th>
                        ${seatArray.map(s => `<th>${s}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>${renderRows(topKeys)}</tbody>
            </table>
        </div>
    `;

    if (sortedKeys.length > limit) {
        html += `<div style="text-align: center; margin-top: 16px;">
            <button id="status-more-btn" class="btn btn-outline">もっと見る</button>
        </div>`;
    }

    container.innerHTML = html;

    const btn = document.getElementById('status-more-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            const fullHtml = `
                <div class="table-responsive">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>列車名</th><th>対象日</th><th>区間</th>
                                ${seatArray.map(s => `<th>${s}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>${renderRows(sortedKeys)}</tbody>
                    </table>
                </div>
            `;
            showModal('最近の空席状況', fullHtml);
        });
    }
}

export function initStatusTable() {
    store.subscribe(() => {
        renderStatusTable();
    });
}
