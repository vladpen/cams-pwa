class Player extends Base {
    _lock = false;
    _timerId;

    start = (id, hash) => {
        this._id = id;
        this._videoBox = document.getElementById(id);
        this._liveUrl = '/?live=1&dt={dt}&hash=' + hash;
        this._rangeUrl = '/?range={range}&dt={dt}&hash=' + hash;
        this._nextUrl = '/?next={step}&dt={dt}&hash=' + hash;

        const active = this._videoBox.querySelector('.active');
        const hidden = this._videoBox.querySelector('.hidden');
        active.dataset.dt = '';
        hidden.dataset.dt = '';

        this._setLiveMode();
        this._fetch(this._liveUrl);

        active.ontimeupdate = this._onTimeUpdate;
        hidden.ontimeupdate = this._onTimeUpdate;
        active.onended = this._onEnded;
        hidden.onended = this._onEnded;

        if (!window.frameLoading) {
            window.frameLoading = {}
        }
        window.frameLoading[this._id] = 1
    }

    seek = (step) => {
        this._fetchNext(this._nextUrl, { step: step });
    }

    onRangeChange = (val) => {
        this._lock = false;
        this._videoBox.querySelector('.active').dataset.dt = '';
        this._fetchNext(this._rangeUrl, { range: val });
    }

    onRangeInput = (e) => {
        this._lock = true;
        const hidden = this._videoBox.querySelector('.hidden');

        if (hidden.dataset.ready == 1) {  // this._isSrcSet
            return
        }
        this._playMode = 'arch';
        this._playThreshold = 0.5;
        this._fetchNext(this._rangeUrl, { range: e.target.value });
    }

    _onTimeUpdate = (e) => {
        const active = e.target;
        const hidden = this._videoBox.querySelector('.hidden');

        if (hidden.dataset.ready || !active.src || active.buffered.length < 1 || !active.classList.contains('active')) {
            return;
        }
        if (active.currentTime / active.buffered.end(0) > this._playThreshold) {
            if (this._playMode == 'live') {
                this._fetch(this._liveUrl);
            } else {
                this._fetch(this._nextUrl, { step: 1 });
            }
        }
    }

    _onEnded = () => {
        this._videoBox.querySelector('.active').dataset.ready = '';
        this._playNext();
    }

    _playNext = () => {
        const active = this._videoBox.querySelector('.active');
        const hidden = this._videoBox.querySelector('.hidden');

        if (active.dataset.ready || hidden.dataset.ready < '2') {
            return;
        }
        if (this.btnPause && this.btnPause.classList.contains('hidden')) {
            return;
        }
        active.classList.remove('active');
        hidden.classList.add('active');
        hidden.classList.remove('hidden');
        active.classList.add('hidden');

        active.dataset.ready = '';

        if (!this._lock) {
            hidden.play().catch(e => {
                console.error(e.message);
                this.showPlayBtn();
            });
        }
        if (this.btnSpeed && this.btnSpeed.classList.contains('selected')) {
            hidden.playbackRate = this.speedRange.value;
        }
    }

    _setLiveMode = () => {
        this._playMode = 'live'
        this._playThreshold = 0.8;
        if (this.timeRange) {
            this.timeRange.value = this.timeRange.max;
            this.btnSpeed.classList.remove('selected');
            this.btnMotion.classList.remove('selected');
            this.speedRange.classList.add('hidden');
            this.motionRange.classList.add('hidden');
            for (const e of this.footer.querySelectorAll('.arch')) {
                e.classList.add('disabled');
            }
        }
    }

    _getSrc = (url, args = {}) => {
        Object.entries(args).forEach(([key, val]) => {
            url = url.replace('{' + key + '}', val);
        });
        url = url.replace('{dt}', this._videoBox.querySelector('.active').dataset.dt);
        if (this.btnMotion && this.btnMotion.classList.contains('selected')) {
            url += '&md=' + this.motionRange.value;
        }
        return url;
    }

    _fetchNext = (url, args) => {
        this._videoBox.querySelector('.active').pause();
        const hidden = this._videoBox.querySelector('.hidden');
        const active = this._videoBox.querySelector('.active');

        this._playMode = 'arch';
        this._playThreshold = 0.5;

        active.pause();
        active.dataset.ready = '';

        this._fetch(url, args);

        for (const e of this.footer.querySelectorAll('.arch')) {
            e.classList.remove('disabled');
        }
    }

    _fetch = (url, args = {}) => {
        this._videoBox.querySelector('.hidden').dataset.ready = 1;
        clearTimeout(this._timerId);

        let datetime, rng;
        fetch(this._getSrc(url, args))
            .then(r => {
                datetime = r.headers.get('x-datetime');
                rng = r.headers.get('x-range');
                return r.blob();
            })
            .then(data => {
                if (!data.size && !this._lock) {
                    window.frameLoading[this._id] = 1;
                    this.loader.classList.remove('hidden');
                    if (this.btnPause && this.btnPause.classList.contains('hidden')) {
                        return;
                    }
                    this._timerId = setTimeout(() => {
                        this._fetch(url, args);
                    }, 1000);
                    return;
                }
                const hidden = this._videoBox.querySelector('.hidden');
                if (!data.size) {
                    hidden.dataset.ready = '';
                    return;
                }
                delete window.frameLoading[this._id];
                if (!Object.keys(window.frameLoading).length) {
                    this.loader.classList.add('hidden');
                }
                hidden.src = window.URL.createObjectURL(data);
                hidden.dataset.dt = datetime;

                if (!rng && this._playMode != 'live') {
                    this._setLiveMode();
                }
                if (rng && !this._lock) {
                    this.timeRange.value = rng;
                }
                hidden.dataset.ready = 2;
                this._playNext();
            })
            .catch(e => {
                console.error('Fetch error:', e)
            });
    }
}
