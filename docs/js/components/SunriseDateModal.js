import store from '../store.js';
import { showModal, hideModal } from './Modal.js';

let modalDates = [];

function getTodayStr() {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function getMaxDateStr() {
    const d = new Date();
    d.setMonth(d.getMonth() + 1);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatDateDisplay(dStr) {
    if (!dStr || dStr.length !== 8) return dStr;
    const y = dStr.substring(0, 4);
    const m = dStr.substring(4, 6);
    const d = dStr.substring(6, 8);
    const dateObj = new Date(Number(y), Number(m) - 1, Number(d));
    const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
    const w = weekdays[dateObj.getDay()];
    return `${y}/${m}/${d} (${w})`;
}

export async function openSunriseDateModal() {
    await store.fetchConfig();
    const config = store.state.config || {};
    const sunriseConf = config.sunrise || {};
    const existingDates = Array.isArray(sunriseConf.target_dates) 
        ? [...sunriseConf.target_dates] 
        : (Array.isArray(sunriseConf) ? [...sunriseConf] : []);
    
    modalDates = existingDates.filter(d => typeof d === 'string' && d.length === 8);

    showModal('🌅 サンライズ 取得対象日設定', getModalHtml());
    attachModalEvents();
}

function getModalHtml() {
    const todayYMD = getTodayStr().replace(/-/g, '');
    const hasToken = !!store.state.githubToken;
    const minDate = getTodayStr();
    const maxDate = getMaxDateStr();

    return `
        <div class="date-modal-container">
            <p class="date-modal-desc">
                サンライズ出雲・瀬戸の空席照会対象日を管理できます。<br>
                <strong>「当日の便」は毎日自動的に対象</strong>となります。別便を監視したい場合は以下に対象日を追加してください。
            </p>

            <div class="modal-section">
                <label class="section-label"><i class="fa-solid fa-list-check"></i> 現在のスクレイピング対象日</label>
                <div id="date-tag-list" class="date-tag-list">
                    <div class="date-tag default-tag">
                        <i class="fa-solid fa-calendar-day"></i> 当日便 (${formatDateDisplay(todayYMD)}) [自動対象]
                    </div>
                    ${modalDates.map(d => `
                        <div class="date-tag custom-tag" data-date="${d}">
                            <i class="fa-solid fa-calendar-plus"></i> ${formatDateDisplay(d)}
                            <button type="button" class="tag-delete-btn" data-delete="${d}" title="削除"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                    `).join('')}
                    ${modalDates.length === 0 ? '<div class="no-extra-dates">追加指定日なし（当日便のみ取得中）</div>' : ''}
                </div>
            </div>

            <div class="modal-section">
                <label class="section-label"><i class="fa-solid fa-plus-circle"></i> 別日を追加する</label>
                <div class="date-add-bar">
                    <input type="date" id="new-target-date" min="${minDate}" max="${maxDate}" class="date-input" value="${minDate}">
                    <button type="button" id="add-date-btn" class="btn btn-primary">
                        <i class="fa-solid fa-plus"></i> リストに追加
                    </button>
                </div>
                <div id="date-add-msg" class="modal-msg"></div>
            </div>

            <div class="modal-section github-token-section">
                <div class="token-header">
                    <label class="section-label">
                        <i class="fa-brands fa-github"></i> GitHub 連携設定
                    </label>
                    <span class="token-badge ${hasToken ? 'badge-connected' : 'badge-disconnected'}">
                        ${hasToken ? '<i class="fa-solid fa-check"></i> 設定済み' : '<i class="fa-solid fa-triangle-exclamation"></i> 未設定'}
                    </span>
                </div>
                <p class="token-desc">
                    ダッシュボードからリポジトリ (<code>fkks33/sakana</code>) を直接更新するために、GitHub Personal Access Token (repo権限) を使用します。トークンはブラウザのみに安全に保存されます。
                </p>
                <div class="token-input-group">
                    <input type="password" id="github-token-input" class="token-input" placeholder="ghp_xxxxxxxxxxxx" value="${store.state.githubToken || ''}">
                    <button type="button" id="save-token-btn" class="btn btn-outline">保存</button>
                    ${hasToken ? '<button type="button" id="clear-token-btn" class="btn btn-outline text-danger" title="トークン削除"><i class="fa-solid fa-trash"></i></button>' : ''}
                </div>
                <div class="token-help-links">
                    <a href="https://github.com/settings/tokens/new?scopes=repo&description=Sakana%20Insight%20Dashboard" target="_blank" rel="noopener">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> GitHub Token を新規発行する (repo権限)
                    </a>
                </div>
            </div>

            <div id="modal-action-status" class="modal-status-box" style="display: none;"></div>

            <div class="modal-footer-actions">
                <div class="footer-left">
                    <a href="https://github.com/fkks33/sakana/edit/main/config.json" target="_blank" class="btn-link" title="GitHub上のconfig.jsonを直接ブラウザで編集">
                        <i class="fa-solid fa-pen-to-square"></i> GitHubで直接編集
                    </a>
                </div>
                <div class="footer-right">
                    <button type="button" id="save-config-btn" class="btn btn-primary btn-save">
                        <i class="fa-solid fa-cloud-arrow-up"></i> GitHubに保存して反映
                    </button>
                    <button type="button" id="trigger-actions-btn" class="btn btn-outline" style="display: none;">
                        <i class="fa-solid fa-play"></i> 今すぐスクレイピング実行
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderModalContent() {
    const container = document.getElementById('modal-body');
    if (container) {
        container.innerHTML = getModalHtml();
    }
}

function attachModalEvents() {
    const addBtn = document.getElementById('add-date-btn');
    const dateInput = document.getElementById('new-target-date');
    const addMsg = document.getElementById('date-add-msg');
    const saveTokenBtn = document.getElementById('save-token-btn');
    const clearTokenBtn = document.getElementById('clear-token-btn');
    const tokenInput = document.getElementById('github-token-input');
    const saveConfigBtn = document.getElementById('save-config-btn');
    const triggerActionsBtn = document.getElementById('trigger-actions-btn');
    const statusBox = document.getElementById('modal-action-status');

    if (addBtn && dateInput) {
        addBtn.addEventListener('click', () => {
            const rawVal = dateInput.value;
            if (!rawVal) {
                showAddMsg('日付を選択してください', 'error');
                return;
            }
            const ymd = rawVal.replace(/-/g, '');
            const todayYMD = getTodayStr().replace(/-/g, '');

            if (ymd === todayYMD) {
                showAddMsg('当日の便はすでに自動対象となっています。', 'info');
                return;
            }
            if (modalDates.includes(ymd)) {
                showAddMsg('この日付はすでに追加されています。', 'warning');
                return;
            }

            modalDates.push(ymd);
            modalDates.sort();
            showAddMsg(`${formatDateDisplay(ymd)} を追加しました。反映するには「GitHubに保存」を押してください。`, 'success');
            renderModalContent();
            attachModalEvents();
        });
    }

    document.querySelectorAll('.tag-delete-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetDate = btn.dataset.delete;
            modalDates = modalDates.filter(d => d !== targetDate);
            renderModalContent();
            attachModalEvents();
        });
    });

    if (saveTokenBtn && tokenInput) {
        saveTokenBtn.addEventListener('click', () => {
            const val = tokenInput.value.trim();
            store.setGithubToken(val);
            renderModalContent();
            attachModalEvents();
            showStatus('GitHub Tokenを保存しました。', 'success');
        });
    }

    if (clearTokenBtn) {
        clearTokenBtn.addEventListener('click', () => {
            if (confirm('GitHub Tokenを削除しますか？')) {
                store.setGithubToken('');
                renderModalContent();
                attachModalEvents();
                showStatus('GitHub Tokenを解除しました。', 'info');
            }
        });
    }

    if (saveConfigBtn) {
        saveConfigBtn.addEventListener('click', async () => {
            if (!store.state.githubToken) {
                showStatus('GitHub Personal Access Token を入力・保存してください。', 'error');
                tokenInput?.focus();
                return;
            }

            saveConfigBtn.disabled = true;
            saveConfigBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 保存中...';
            showStatus('GitHub リポジトリに config.json をコミット中...', 'info');

            try {
                await store.saveSunriseDates(modalDates);
                showStatus('✅ config.json の更新コミットが完了しました！次回の定期実行から反映されます。', 'success');
                if (triggerActionsBtn) {
                    triggerActionsBtn.style.display = 'inline-flex';
                }
            } catch (err) {
                console.error(err);
                showStatus(`❌ 保存に失敗しました: ${err.message}`, 'error');
            } finally {
                saveConfigBtn.disabled = false;
                saveConfigBtn.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> GitHubに保存して反映';
            }
        });
    }

    if (triggerActionsBtn) {
        triggerActionsBtn.addEventListener('click', async () => {
            triggerActionsBtn.disabled = true;
            triggerActionsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 実行要求中...';
            try {
                await store.triggerWorkflow('sunrise-checker.yml');
                showStatus('🚀 GitHub Actions の実行を開始しました！数分後にログが更新されます。', 'success');
            } catch (err) {
                showStatus(`❌ Actions実行失敗: ${err.message}`, 'error');
            } finally {
                triggerActionsBtn.disabled = false;
                triggerActionsBtn.innerHTML = '<i class="fa-solid fa-play"></i> 今すぐスクレイピング実行';
            }
        });
    }

    function showAddMsg(msg, type = 'info') {
        if (!addMsg) return;
        addMsg.textContent = msg;
        addMsg.className = `modal-msg msg-${type}`;
    }

    function showStatus(msg, type = 'info') {
        if (!statusBox) return;
        statusBox.style.display = 'block';
        statusBox.textContent = msg;
        statusBox.className = `modal-status-box status-${type}`;
    }
}
