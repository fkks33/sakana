import store, { courseNames } from '../store.js';

export function renderSidebar() {
    const container = document.getElementById('sidebar-container');
    const { currentCourse } = store.state;
    
    container.innerHTML = `
        <div class="sidebar-header">
            <i class="fa-solid fa-fish"></i> Sakana Insight
        </div>
        <div class="sidebar-nav">
            <div class="nav-section">
                <div class="nav-section-title">Routes</div>
                
                <div class="nav-item ${currentCourse === 'sunrise' ? 'active' : ''}" data-course="sunrise">
                    <i class="fa-solid fa-moon"></i> サンライズ
                </div>
                
                <div class="nav-item" style="cursor: default;">
                    <i class="fa-solid fa-star"></i> 銀河
                </div>
                <div class="nav-sub-items">
                    <div class="nav-sub-item ${currentCourse === 'sanin' ? 'active' : ''}" data-course="sanin">山陰コース</div>
                    <div class="nav-sub-item ${currentCourse === 'kinan' ? 'active' : ''}" data-course="kinan">紀南コース</div>
                </div>
            </div>
            
            <div class="nav-section">
                <div class="nav-section-title">Settings & Docs</div>
                <div class="nav-item" id="theme-toggle">
                    <i class="fa-solid ${store.state.theme === 'dark' ? 'fa-sun' : 'fa-moon'}"></i> 
                    ${store.state.theme === 'dark' ? 'ライトモード' : 'ダークモード'}
                </div>
                <a href="./specification.html" target="_blank" class="nav-item" style="text-decoration: none; color: inherit; display: flex; align-items: center; gap: 0.75rem;">
                    <i class="fa-solid fa-book"></i> 技術仕様書
                    <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 0.75rem; margin-left: auto; opacity: 0.6;"></i>
                </a>
            </div>
        </div>
    `;

    // Attach Events
    container.querySelectorAll('[data-course]').forEach(el => {
        el.addEventListener('click', () => {
            store.setCourse(el.dataset.course);
            store.setState({ isSidebarOpen: false });
        });
    });

    container.querySelector('#theme-toggle').addEventListener('click', () => {
        store.toggleTheme();
    });
}

export function initSidebar() {
    store.subscribe(() => {
        renderSidebar();
        
        const { currentCourse, isSidebarOpen } = store.state;
        const container = document.getElementById('sidebar-container');
        const overlay = document.getElementById('mobile-overlay');
        const title = document.getElementById('page-title');
        
        title.textContent = courseNames[currentCourse];
        
        if (isSidebarOpen) {
            container.classList.add('open');
            overlay.classList.add('active');
        } else {
            container.classList.remove('open');
            overlay.classList.remove('active');
        }
    });

    document.getElementById('mobile-menu-btn').addEventListener('click', () => {
        store.toggleSidebar();
    });
    
    document.getElementById('mobile-overlay').addEventListener('click', () => {
        store.setState({ isSidebarOpen: false });
    });
    
    renderSidebar(); // initial render
}
