import store from '../store.js';
import { formatDateStr, getStatusBadge } from '../utils.js';
import { showModal } from './Modal.js';
import { openSunriseDateModal } from './SunriseDateModal.js';

function getSunriseBannerHtml() {
    const { currentCourse, config } = store.state;
    if (currentCourse !== 'sunrise') return '';

    const sunriseConf = config?.sunrise || {};
    const extraDates = Array.isArray(sunriseConf.target_dates) 
        ? sunriseConf.target_dates 
        : (Array.isArray(sunriseConf) ? sunriseConf : []);

    return `
        <div class="sunrise-target-bar">
            <div class="target-bar-left">
                <span class="target-bar-label"><i class="fa-solid fa-calendar-check"></i> 取得対象日:</span>
                <span class="target-badge default"><i class="fa-solid fa-bolt"></i> 当日の便 (自動)</span>
                ${extraDates.map(d => `<span class="target-badge custom"><i class="fa-solid fa-calendar-day"></i> ${formatDateStr(d)}</span>`).join('')}
                ${extraDates.length === 0 ? '<span class="target-hint">※ 追加指定日なし</span>' : ''}
            </div>
            <button type="button" id="open-sunrise-modal-btn" class="btn btn-sm btn-outline">
                <i class="fa-solid fa-calendar-plus"></i> 対象日を追加・管理
            </button>
        </div>
    `;
}

function attachBannerEvent() {
    const btn = document.getElementById('open-sunrise-modal-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            openSunriseDateModal();
        });
    }
}

export function renderStatusTable() {
    const container = document.getElementById('status-table-container');
    const { logs } = store.state;
    const bannerHtml = getSunriseBannerHtml();

    if (!logs || logs.length === 0) {
        container.innerHTML = bannerHtml + '<p style="color: var(--text-tertiary); text-align: center; padding: 20px;">データがありません</p>';
        attachBannerEvent();
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

    container.innerHTML = bannerHtml + html;
    attachBannerEvent();

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
