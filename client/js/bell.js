class Bell extends Config {
    static _eventSource = null;

    constructor() {
        super();
        const cams = this.getCams();
        this._cams = {};
        for (const id in cams) {
            this._cams[cams[id].key] = id;
        }
        this._btnBell = document.querySelector('header .bell-btn');
        this._btnEvents = document.querySelector('.cam-header .link-btn');
        this._fadeTimeoutId = null;
    }

    run = () => {
        if (!Object.keys(this._cams).length) {
            return;
        }
        if (sessionStorage.getItem('bell')) {
            this._btnBell.classList.add('selected');
        }
        this._btnBell.onclick = this._toggleBtn;

        this._runSse();
    }

    _runSse = () => {
        this._close_sse();

        this._screenSaver();
        document.body.onclick = this._screenSaver;

        Bell._eventSource = new EventSource(
            '/?bell=' + Number(sessionStorage.getItem('bell')) +
            '&uid=' + this.getUid() +
            '&keys=' + Object.keys(this._cams).join(','));

        Bell._eventSource.onmessage = evt => {
            try {
                const data = JSON.parse(evt.data);

                if (data.action == 'init') {
                    this._handle_init(data.cams);
                } else if (data.action == 'bell') {
                    this._handle_bell(data.cams);
                }
                if (this._cams) {
                    this._btnBell.classList.remove('hidden');
                }
            } catch (err) {
                console.error('SSE onMessage:', err);
            }
        }

        Bell._eventSource.onerror = evt => {
            console.error('SSE onError: readyState=' + evt.target.readyState);
        }
    }

    _handle_init = cams => {
        let available_cams = {}
        for (const key in cams) {
            const events = Number(cams[key].events);
            const time = cams[key].time;

            const id = this._cams[key];
            if (time) {
                this._updateNavList(id, this._formatTime(time));
            }
            if (events && this._btnEvents && id == this._btnEvents.dataset.id) {
                this._btnEvents.classList.remove('hidden');
            }
        }

        if (!this._btnBell) {
            return
        }
        if (sessionStorage.getItem('bell')) {
            this._btnBell.classList.add('selected');
        } else {
            this._close_sse();
        }
    }

    _handle_bell = cams => {
        let msg = '\r\n';
        const all_cams = this.getCams();

        for (const key in cams) {
            const id = this._cams[key];
            this._updateNavList(id, this._formatTime(cams[key]));

            msg += '\r\n' + all_cams[id].name;
        }
        this._showNotification(msg);
    }

    _close_sse = () => {
        if (Bell._eventSource) {
            Bell._eventSource.close();
            Bell._eventSource = null;
        }
    }

    _formatTime = time => {
        return time.slice(-6, -4) + ':' + time.slice(-4, -2);
    }

    _toggleBtn = () => {
        if (this._btnBell.classList.contains('selected')) {
            this._btnBell.classList.remove('selected');
            sessionStorage.setItem('bell', '');
            this.wakeRelease();
        } else {
            Notification.requestPermission(res => {
                if (res != 'granted') {
                    console.error('Bell notification permission:', res);
                }
            });
            this._btnBell.classList.add('selected');
            sessionStorage.setItem('bell', '1');
            this.wakeLock();
        }
        this._runSse();
    }

    _updateNavList = (id, hm) => {
        const nav = document.querySelector('main .nav');
        if (!nav) {
            return;
        }
        for (const row of nav.querySelectorAll('li')) {
            if (row.dataset.id != id) continue;
            row.querySelector('i').textContent = hm;
            break;
        }
    }

    _showNotification = msg => {
        navigator.serviceWorker.getRegistration()
            .then(reg => {
                if (!reg) {
                    console.error('Bell: no active Service Worker Registration found.');
                    return;
                }
                reg.showNotification(document.documentElement.dataset.title, {
                    body: msg,
                    icon: '/img/icon.svg',
                    tag: 'cams-pwa-event',
                    renotify: true,
                    // requireInteraction: true
                });
            })
            .catch(e => {
                console.error('Bell: Service Worker Registration:', e);
            });
        this._screenSaver();
    }

    _screenSaver = () => {
        clearTimeout(this._fadeTimeoutId);
        document.body.style.setProperty('--brightness', 1);

        if (!sessionStorage.getItem('bell')) return;

        this._timeoutId = setTimeout(() => {
            document.body.style.setProperty('--brightness', 0.5);
        }, 300000); // 5 minutes
    }
}
