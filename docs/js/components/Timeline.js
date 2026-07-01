import store from '../store.js';
import { formatISODate, formatDateStr } from '../utils.js';
import { showModal } from './Modal.js';

export function renderTimeline() {
    const container = document.getElementById('timeline-container');
    const { logs } = store.state;

    const events = [];
    logs.forEach(res => {
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
        container.innerHTML = '<p style="color:var(--text-tertiary);font-size:0.875rem;">最近検知された空席はありません。</p>';
        return;
    }

    const renderEvents = (evs) => evs.map(ev => `
        <div class="timeline-item">
            <div class="timeline-marker"></div>
            <span class="timeline-time">${formatISODate(ev.time.toISOString())}</span>
            <div class="timeline-content">
                <strong>${ev.dateStr} ${ev.dir}</strong> の <strong>${ev.seat}</strong> に空き（${ev.status}）を検知しました。<br>
                <a href="${ev.url || '#'}" target="_blank" style="color: var(--brand-primary); text-decoration: none; font-weight: 600; font-size: 0.75rem; margin-top: 4px; display: inline-block;">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> 予約サイトへ
                </a>
            </div>
        </div>
    `).join('');

    let html = `<div class="timeline">${renderEvents(topEvents)}</div>`;

    if (events.length > limit) {
        html += `<div style="text-align: center; margin-top: 16px;">
            <button id="timeline-more-btn" class="btn btn-outline">もっと見る</button>
        </div>`;
    }

    container.innerHTML = html;

    const btn = document.getElementById('timeline-more-btn');
    if (btn) {
        btn.addEventListener('click', () => {
            showModal('検知タイムライン', `<div class="timeline" style="padding-top: 10px;">${renderEvents(events)}</div>`);
        });
    }
}

export function initTimeline() {
    store.subscribe(() => {
        renderTimeline();
    });
}
