class Player extends Base {
    constructor(video, key) {
        super();
        this._video = video;
        this._key = key;
        this._liveUrl = '/?video=live&dt={dt}&key=' + key;
        this._rangeUrl = '/?video=range&range={range}&dt={dt}&key=' + key;
        this._nextUrl = '/?video=next&step={step}&dt={dt}&key=' + key;
        this._datetime = '';
        this._lock = false;
        this._setTime = 0;
        this._progress = false;
        this._abortController;
        this._sourceBuffer;
        this._codecs = 'avc1.42001f';
        this._mediaSource = new MediaSource();
        this._networkState = true;
        this._events = false;
    }

    start = () => {
        this._setLiveMode();

        this._mediaSource.addEventListener('sourceopen', this._onSourceOpen, { once: true });
        this._video.src = URL.createObjectURL(this._mediaSource);
        this._video.addEventListener('timeupdate', this._onTimeUpdate);

        if (!window.frameLoading) {
            window.frameLoading = {};
        }
        window.frameLoading[this._key] = 1;
        setInterval(this._watchdog, 1000);
    }

    seek = step => {
        if (this._playMode != 'live' && this._progress) {
            return;
        }
        this._video.removeEventListener('timeupdate', this._onTimeUpdate);
        this._fetchArch(this._nextUrl, { step: step }, () => {
            this._video.play();
            this._video.addEventListener('timeupdate', this._onTimeUpdate);
        }, true);
    }

    onRangeDown = () => { // push down
        this._lock = true;
        this._abortController.abort();
        this._progress = false;
    }

    onRangeInput = e => {
        this._lock = true; // move
        this._fetchArch(this._rangeUrl, { range: e.target.value });
    }

    onRangeChange = val => { // release
        this._lock = false;
        this._video.play();
        this._fetchArch(this._rangeUrl, { range: val }, null, true);
    }

    _onSourceOpen = () => {
        this._fetch(this._liveUrl, {}, () => {
            this._video.play()
                .then(() => {
                    if (this._events) {
                        this.showLinkBtn();
                    }
                })
                .catch(e => {
                    console.error(e.message);
                    this.resizeBars();
                    this.showPlayBtn();
                });
        });
    }

    _onTimeUpdate = () => {
        if (this._lock ||
            this._progress ||
            !this._networkState ||
            this._sourceBuffer.timestampOffset - this._video.currentTime > 0) {
            return;
        }
        this._fetchRepeat();
    }

    _setCurrentTime = () => {
        if (!this._video.seekable.length) {
            return;
        }
        this._video.currentTime = this._video.seekable.end(this._video.seekable.length - 1);
    }

    _setLiveMode = () => {
        this._playMode = 'live'
        this._setTime = 2;
        this._video.playbackRate = 1;
        document.body.classList.remove('arch');
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

    _watchdog = () => {
        if (this._lock || this._progress || this._video.paused || this._video.readyState > 2) {
            return;
        }
        this._fetchRepeat();
    }

    _getUrl = (url, args = {}) => {
        for (const key in args) {
            url = url.replace('{' + key + '}', args[key]);
        }
        const dt = this._datetime ? this._datetime : '';
        url = url.replace('{dt}', dt);
        if (this.btnMotion && this.btnMotion.classList.contains('selected')) {
            url += '&md=' + this.motionRange.value;
        }
        return url;
    }

    _fetchRepeat = () => {
        if (this._playMode == 'live') {
            this._fetch(this._liveUrl);
        } else {
            this._fetch(this._nextUrl, { step: 1 });
        }
    }

    _fetchArch = (url, args, callback, force = false) => {
        this._playMode = 'arch';
        this._setTime = 1;
        this._fetch(url, args, callback, force);
        for (const e of this.footer.querySelectorAll('.arch')) {
            e.classList.remove('disabled');
        }
        this.loader.classList.remove('hidden');
    }

    _fetch = (url, args = {}, callback = null, force = false) => {
        if (!force && this._progress) {
            return;
        }
        if (this._abortController) {
            this._abortController.abort();
        }
        this._abortController = new AbortController();
        this._progress = true;

        let rng;

        fetch(this._getUrl(url, args), {
            cache: 'no-store',
            signal: this._abortController.signal
        })
        .then(r => {
            const datetime = r.headers.get('x-datetime');
            this._datetime = datetime ? datetime : this._datetime;
            rng = r.headers.get('x-range');
            const codecs = r.headers.get('x-codecs');
            this._codecs = codecs ? codecs : this._codecs;
            if (r.headers.get('x-events')) {
                this._events = true;
            }
            return r.arrayBuffer();
        })
        .then(data => {
            this._progress = false;
            this._networkState = true;

            delete window.frameLoading[this._key];
            if (!Object.keys(window.frameLoading).length) {
                this.loader.classList.add('hidden');
            }
            if (!data.byteLength) {
                if (this._playMode == 'live') { // camera failure, wait for watchdog
                    return;
                }
                // the same segment received (on rangeChange), fetch next one immediately
                return this._fetch(this._nextUrl, { step: 1 });
            }
            if (!this._sourceBuffer) {
                try {
                    const sourceType = `video/mp4; codecs="${this._codecs}"`;
                    this._sourceBuffer = this._mediaSource.addSourceBuffer(sourceType);
                    this._sourceBuffer.mode = 'sequence';
                } catch (e) {
                    console.error('Error adding SourceBuffer:', e);
                    return;
                }
            }
            this._sourceBuffer.appendBuffer(data);

            if (this._playMode != 'live' && rng > this.MAX_RANGE) {
                this._setLiveMode();
            }
            if (this.timeRange && !this._lock && rng) {
                this.timeRange.value = rng;
            }
            if (callback) {
                callback();
            }
            if (this._setTime > 0) {
                this._setTime -= 1;
                this._setCurrentTime();
            }
        })
        .catch(e => { // user abort or network failure
            if (e.name == 'AbortError') {
                return; // abort signal means that new fetch is in progress, do nothing
            }
            this._progress = false; // network failure, wait for watchdog
            this._networkState = false;
        });
    }
}
