export const weekdayKanji = ["日", "月", "火", "水", "木", "金", "土"];

export function formatDateStr(dateStr) {
    if (!dateStr || dateStr.length !== 8) return dateStr;
    const y = dateStr.substring(0, 4);
    const m = parseInt(dateStr.substring(4, 6), 10);
    const d = parseInt(dateStr.substring(6, 8), 10);
    const dateObj = new Date(y, m - 1, d);
    const w = weekdayKanji[dateObj.getDay()];
    return `${m}/${d}(${w})`;
}

export function formatISODate(isoStr) {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    const s = String(date.getSeconds()).padStart(2, '0');
    return `${y}-${m}-${d} ${h}:${min}:${s}`;
}

export function getStatusBadge(status) {
    if (!status) return `<span class="badge badge-err">-</span>`;
    const s = status.trim();
    if (s === '○' || s === '〇') return `<span class="badge badge-o">〇</span>`;
    if (s === '△') return `<span class="badge badge-tri">△</span>`;
    if (s === '×' || s.includes('なし')) return `<span class="badge badge-x">×</span>`;
    return `<span class="badge badge-err">!</span>`;
}

export function createElementFromHTML(htmlString) {
    const div = document.createElement('div');
    div.innerHTML = htmlString.trim();
    return div.firstChild;
}
