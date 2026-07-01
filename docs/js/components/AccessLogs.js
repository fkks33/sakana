import store from '../store.js';
import { formatISODate, formatDateStr, getStatusBadge } from '../utils.js';
import { showModal } from './Modal.js';

export function renderAccessLogs() {
    const container = document.getElementById('access-logs-container');
    const { logs } = store.state;

    if (logs.length === 0) {
        container.innerHTML = '<p style="color:var(--text-tertiary);text-align:center;">ログデータがありません</p>';
        return;
    }

    const groups = {};
    const sortedLogs = [...logs].reverse();
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
        
        const detailsHtml = logsInGroup.map(log => `
            <tr>
                <td>${log.depart} → ${log.arrive}</td>
                <td>${formatDateStr(log.target_date)}</td>
                <td>${log.seat_type}</td>
                <td>${getStatusBadge(log.result)}</td>
            </tr>
        `).join('');

        return `
            <tbody class="log-group">
                <tr class="log-group-header">
                    <td><strong>${formatISODate(ts)}</strong></td>
                    <td>${trainName}</td>
                    <td>照会数: ${totalQueries}件</td>
                    <td>空席検知: <strong style="color:var(--brand-primary)">${availableCount}件</strong></td>
                    <td style="text-align: right;"><i class="fa-solid fa-chevron-down icon-expand"></i></td>
                </tr>
                <tr class="log-group-details" style="display: none;">
                    <td colspan="5">
                        <div class="inner-table">
                            <table class="data-table">
                                <thead>
                                    <tr><th>区間</th><th>対象日</th><th>席種</th><th>結果</th></tr>
                                </thead>
                                <tbody>${detailsHtml}</tbody>
                            </table>
                        </div>
                    </td>
                </tr>
            </tbody>
        `;
    };

    let html = `
        <div class="table-responsive">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>取得日時</th><th>列車名</th><th colspan="2">結果概要</th><th>詳細</th>
                    </tr>
                </thead>
                ${currentGroupKeys.map(ts => createGroupHTML(ts)).join('')}
            </table>
        </div>
    `;

    if (groupOrder.length > limit) {
        html += `<div style="text-align: center; margin-top: 16px;">
            <button id="logs-more-btn" class="btn btn-outline">もっと見る</button>
        </div>`;
    }

    container.innerHTML = html;

    // Attach Accordion Events
    container.querySelectorAll('.log-group-header').forEach(el => {
        el.addEventListener('click', () => {
            el.classList.toggle('open');
            const details = el.nextElementSibling;
            details.style.display = details.style.display === 'none' ? '' : 'none';
        });
    });

    const btn = document.getElementById('logs-more-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            const fullHtml = `
                <div class="table-responsive">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>取得日時</th><th>列車名</th><th colspan="2">結果概要</th><th>詳細</th>
                            </tr>
                        </thead>
                        ${groupOrder.map(ts => createGroupHTML(ts)).join('')}
                    </table>
                </div>
            `;
            showModal('アクセスログ', fullHtml);
            
            // Re-attach events in modal
            const modalBody = document.getElementById('modal-body');
            modalBody.querySelectorAll('.log-group-header').forEach(el => {
                el.addEventListener('click', () => {
                    el.classList.toggle('open');
                    const details = el.nextElementSibling;
                    details.style.display = details.style.display === 'none' ? '' : 'none';
                });
            });
        });
    }
}

export function initAccessLogs() {
    store.subscribe(() => {
        renderAccessLogs();
    });
}
