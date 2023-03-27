class Bell {
    static run = (hash) => {
        this._audio = new Audio('/bell.mp3');
        this._wakeLock = null;
        this._fetchTimerID;
        this._dimmTimerID;
        this._lastDateTime = '0';
        this._modal = document.querySelector('.modal');
        this._btnBell = document.querySelector('header .bell-btn');

        if (localStorage.getItem('bell')) {
            this._toggleBtn();
        }
        this._btnBell.onclick = this._toggleBtn;

        window.onclick = e => {
            this._modal.classList.add('hidden');
            this._dimmOff();
            if (e.target.tagName != 'A') {
                this._dimmOn();
            }
        }
        window.onorientationchange = this._dimmOn;
    }

    static _toggleBtn= () => {
        if (this._btnBell.classList.contains('selected')) {
            this._btnBell.classList.remove('selected');
            if (this._wakeLock) {
                this._wakeLock.release().then(() => {
                    this._wakeLock = null;
                });
            }
            localStorage.setItem('bell', '');
            this._dimmOff();
        } else {
            this._btnBell.classList.add('selected');
            if ('wakeLock' in navigator) {
                navigator.wakeLock.request('screen').then(wakeLock => {
                    this._wakeLock = wakeLock;
                });
            }
            localStorage.setItem('bell', '1');
            this._fetch();
            this._dimmOn();
        }
    }

    static _dimmOff = () => {
        clearTimeout(this._dimmTimerID);
        document.body.classList.remove('dimmed');
    }

    static _dimmOn = () => {
        if (!navigator.userAgentData.mobile || !this._btnBell.classList.contains('selected')) {
            return;
        }
        this._dimmOff();
        if (this._btnBell.classList.contains('selected')) {
            clearTimeout(this._dimmTimerID);
            this._dimmTimerID = window.setTimeout(() => {
                document.body.classList.add('dimmed');
            }, 20000);
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
        clearTimeout(this._fetchTimerID);
        if (!this._btnBell.classList.contains('selected')) {
            return;
        }
        fetch(`/?bell=1&dt=${this._lastDateTime}`, { cache: 'no-store' })
            .then(r => {
                return r.json();
            })
            .then(data => {
                this._fetchTimerID = window.setTimeout(this._fetch);
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
            .catch(e => {
                console.error('Bell error:', e)
                this._fetchTimerID = window.setTimeout(this._fetch, 10000);
            });
    }
}
