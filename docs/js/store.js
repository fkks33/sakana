export const courseNames = {
    kinan: 'WEST EXPRESS 銀河（紀南コース）',
    sanin: 'WEST EXPRESS 銀河（山陰コース）',
    sunrise: 'サンライズ出雲・瀬戸'
};

const store = {
    state: {
        currentCourse: 'kinan',
        logs: [],
        theme: localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
        isSidebarOpen: false
    },
    listeners: [],

    subscribe(listener) {
        this.listeners.push(listener);
    },

    notify() {
        for (const listener of this.listeners) {
            listener(this.state);
        }
    },

    setState(newState) {
        this.state = { ...this.state, ...newState };
        this.notify();
    },

    async fetchLogs() {
        try {
            const res = await fetch(`./log_${this.state.currentCourse}.json`);
            if (res.ok) {
                const data = await res.json();
                this.setState({ logs: data });
            } else {
                this.setState({ logs: [] });
            }
        } catch (err) {
            console.error('Error fetching logs', err);
            this.setState({ logs: [] });
        }
    },

    setCourse(course) {
        if (this.state.currentCourse !== course) {
            this.setState({ currentCourse: course });
            this.fetchLogs();
        }
    },

    toggleTheme() {
        const newTheme = this.state.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('theme', newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
        this.setState({ theme: newTheme });
    },

    toggleSidebar() {
        this.setState({ isSidebarOpen: !this.state.isSidebarOpen });
    }
};

// Initialize theme
document.documentElement.setAttribute('data-theme', store.state.theme);

export default store;
