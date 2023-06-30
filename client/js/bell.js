class Bell {
    static run = () => {
        this._btnBell = document.querySelector('footer .bell-btn');
        if (this._btnBell.classList.contains('hidden')) {
            return;
        }
        this._audio = new Audio('/bell.mp3');
        this._fetchTimeoutId;
        this._dimmTimeoutId;
        this._lastDateTime = '0';
        this._modal = document.querySelector('.modal');
        this._abortController;
        this._pending = false;

        if (localStorage.getItem('bell')) {
            this._toggleBtn();
        }
        this._btnBell.onclick = this._toggleBtn;

        window.onclick = e => {
            this._modal.classList.add('hidden');
            this._dimmOff();
            if (e.target.tagName == 'A' || e.target.closest('.link')) {
                this._pending = true;
                if (this._abortController) {
                    this._abortController.abort();
                }
            } else {
                this._dimmOn();
            }
        }
        screen.orientation.onchange = this._dimmOn;
    }

    static wakeLock = () => {
        this._wakeLock();
        this._dimmOff();
        this._isPlaying = true;
    }

    static wakeRelease = () => {
        if (this._wakeLockSentinel && !this._btnBell.classList.contains('selected')) {
            this._wakeLockSentinel.release();
        }
        this._dimmOn();
        this._isPlaying = false; // playing is off
    }

    static _wakeLock = () => {
        if (!'wakeLock' in navigator || !navigator.wakeLock ||
            ('userAgentData' in navigator && !navigator.userAgentData.mobile)) {
            return;
        }
        navigator.wakeLock.request('screen').then(wls => {
            this._wakeLockSentinel = wls;
        });
    }

    static _toggleBtn= () => {
        if (this._btnBell.classList.contains('selected')) {
            this._btnBell.classList.remove('selected');
            localStorage.setItem('bell', '');
            this._dimmOff();
            if (this._wakeLockSentinel && !this._isPlaying) {
                this._wakeLockSentinel.release();
            }
        } else {
            this._btnBell.classList.add('selected');
            localStorage.setItem('bell', '1');
            this._fetch();
            this._dimmOn();
            this._wakeLock();
        }
    }

    static _dimmOff = () => {
        clearTimeout(this._dimmTimeoutId);
        document.body.classList.remove('dimmed');
    }

    static _dimmOn = () => {
        if (!this._btnBell.classList.contains('selected') || this._isPlaying ||
            ('userAgentData' in navigator && !navigator.userAgentData.mobile)) {
            return;
        }
        this._dimmOff();
        if (this._btnBell.classList.contains('selected')) {
            clearTimeout(this._dimmTimeoutId);
            this._dimmTimeoutId = window.setTimeout(() => {
                if (!this._isPlaying) {
                    document.body.classList.add('dimmed');
                }
            }, 30000);
        }
    }

    static _updateNavList = (hash, hm) => {
        const nav = document.querySelector('main .nav');
        if (!nav) {
            return;
        }
        for (const row of nav.querySelectorAll('li')) {
            if (row.dataset.hash == hash) {
                row.querySelector('i').textContent = hm;
                break;
            }
        }
    }

    static _fetch = () => {
        clearTimeout(this._fetchTimeoutId);
        if (!this._btnBell.classList.contains('selected')) {
            return;
        }
        this._abortController = new AbortController();
        fetch(`/?bell=1&dt=${this._lastDateTime}`, {
            cache: 'no-store',
            signal: this._abortController.signal
        })
            .then(r => {
                return r.json();
            })
            .then(data => {
                this._fetchTimeoutId = window.setTimeout(this._fetch);
                if (!Object.keys(data).length || !this._btnBell.classList.contains('selected')) {
                    return
                }
                let res = []
                Object.entries(data).forEach(([hash, row]) => {
                    if (row.dt <= this._lastDateTime) {
                        return;  // continue forEach
                    }
                    const hm = row.dt.slice(-6, -4) + ':' + row.dt.slice(-4, -2)
                    res.push(`<a href="/?page=cam&hash=${hash}">${row.name}</a><i>${hm}<i>`);
                    this._lastDateTime = row.dt;
                    this._updateNavList(hash, hm);
                });
                if (!res.length) {
                    return
                }
                this._audio.play();

                this._modal.querySelector('.content').innerHTML = res.join('<br>');
                this._modal.classList.remove('hidden');
                document.body.classList.add('dimmed');
            })
            .catch(() => {
                if (!this._pending) {
                    this._fetchTimeoutId = window.setTimeout(this._fetch, 10000);
                }
            });
    }
}
