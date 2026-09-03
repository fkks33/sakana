export const courseNames = {
    kinan: 'WEST EXPRESS 銀河（紀南コース）',
    sanin: 'WEST EXPRESS 銀河（山陰コース）',
    sunrise: 'サンライズ出雲・瀬戸'
};

const GITHUB_REPO = 'fkks33/sakana';

const store = {
    state: {
        currentCourse: 'kinan',
        logs: [],
        config: { sunrise: { target_dates: [] } },
        configSha: null,
        githubToken: localStorage.getItem('github_token') || '',
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

    setGithubToken(token) {
        token = token.trim();
        if (token) {
            localStorage.setItem('github_token', token);
        } else {
            localStorage.removeItem('github_token');
        }
        this.setState({ githubToken: token });
    },

    async fetchConfig() {
        // First try GitHub API to get latest content and commit SHA
        const headers = {
            'Accept': 'application/vnd.github.v3+json'
        };
        if (this.state.githubToken) {
            headers['Authorization'] = `Bearer ${this.state.githubToken}`;
        }

        try {
            const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/contents/config.json`, { headers });
            if (res.ok) {
                const data = await res.json();
                const jsonText = decodeURIComponent(escape(atob(data.content.replace(/\s/g, ''))));
                const parsed = JSON.parse(jsonText);
                this.setState({
                    config: parsed,
                    configSha: data.sha
                });
                return parsed;
            }
        } catch (err) {
            console.warn('GitHub API fetch failed, falling back to static config.json', err);
        }

        // Fallback to static config.json
        try {
            const fallbackRes = await fetch('./config.json');
            if (fallbackRes.ok) {
                const parsed = await fallbackRes.json();
                this.setState({ config: parsed });
                return parsed;
            }
        } catch (err) {
            console.error('Failed to load static config.json', err);
        }
        return this.state.config;
    },

    async saveSunriseDates(newDates) {
        if (!this.state.githubToken) {
            throw new Error('GitHub Personal Access Token が設定されていません。');
        }

        // Always ensure we have the latest SHA
        if (!this.state.configSha) {
            await this.fetchConfig();
        }

        const updatedConfig = { ...this.state.config };
        if (!updatedConfig.sunrise || typeof updatedConfig.sunrise !== 'object' || Array.isArray(updatedConfig.sunrise)) {
            updatedConfig.sunrise = { target_dates: newDates };
        } else {
            updatedConfig.sunrise.target_dates = newDates;
        }

        const contentString = JSON.stringify(updatedConfig, null, 2) + '\n';
        const contentBase64 = btoa(unescape(encodeURIComponent(contentString)));

        const payload = {
            message: `Update sunrise target dates: ${newDates.join(', ') || 'none'}`,
            content: contentBase64,
            sha: this.state.configSha
        };

        const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/contents/config.json`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${this.state.githubToken}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || `GitHub API エラー (${res.status})`);
        }

        const resData = await res.json();
        this.setState({
            config: updatedConfig,
            configSha: resData.content ? resData.content.sha : null
        });

        return resData;
    },

    async triggerWorkflow(workflowFileName = 'sunrise-checker.yml') {
        if (!this.state.githubToken) {
            throw new Error('GitHub Personal Access Token が必要です。');
        }

        const res = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${workflowFileName}/dispatches`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.state.githubToken}`,
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ref: 'main' })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || `ワークフロー実行エラー (${res.status})`);
        }

        return true;
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
