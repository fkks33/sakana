import store from './store.js';
import { formatISODate } from './utils.js';

// Components
import { initSidebar } from './components/Sidebar.js';
import { initStatusTable } from './components/StatusTable.js';
import { initCharts } from './components/Charts.js';
import { initTimeline } from './components/Timeline.js';
import { initAccessLogs } from './components/AccessLogs.js';
import { initModal } from './components/Modal.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all components
    initModal();
    initSidebar();
    initStatusTable();
    initCharts();
    initTimeline();
    initAccessLogs();

    // Subscribe to update last-updated string
    store.subscribe((state) => {
        const lastUpdatedEl = document.getElementById('last-updated');
        if (state.logs && state.logs.length > 0) {
            const lastLog = state.logs[state.logs.length - 1];
            lastUpdatedEl.textContent = `最終更新: ${formatISODate(lastLog.timestamp)}`;
        } else {
            lastUpdatedEl.textContent = 'データなし';
        }
    });

    // Initial fetch
    store.fetchLogs();
    
    // Auto refresh every 5 minutes
    setInterval(() => {
        store.fetchLogs();
    }, 300000);
});
