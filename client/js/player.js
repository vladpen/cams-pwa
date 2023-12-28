class Player extends Base {
    constructor(video, hash, camInfo) {
        super();
        this._video = video;
        this._hash = hash;
        this._liveUrl = '/?video=live&dt={dt}&hash=' + hash;
        this._rangeUrl = '/?video=range&range={range}&dt={dt}&hash=' + hash;
        this._nextUrl = '/?video=next&step={step}&dt={dt}&hash=' + hash;
        this._datetime = '';
        this._lock = false;
        this._setTime = 0;
        this._progress = false;
        this._abortController;
        this._sourceBuffer;
        this._sourceType = `video/mp4; codecs="${camInfo['codecs']}"`;
        this._mediaSource = new MediaSource();
        this._fetchTimeoutId;
    }

    start = () => {
        this._setLiveMode();

        if ('MediaSource' in window && MediaSource.isTypeSupported(this._sourceType)) {
            this._mediaSource.addEventListener('sourceopen', this._onSourceOpen, { once: true });
            this._video.src = URL.createObjectURL(this._mediaSource);
            this._video.addEventListener('timeupdate', this._onTimeUpdate);
        } else {
            console.error('Unsupported MIME type or codec:', this._sourceType);
            return;
        }
        if (!window.frameLoading) {
            window.frameLoading = {};
        }
        window.frameLoading[this._hash] = 1;
    }

    seek = step => {
        if (this._playMode != 'live' && this._progress) {
            return;
        }
        this._video.removeEventListener('timeupdate', this._onTimeUpdate);
        this._abortController.abort();
        this._fetchArch(this._nextUrl, { step: step }, () => {
            this._video.play();
            this._video.addEventListener('timeupdate', this._onTimeUpdate);
        }, true);
    }

    onRangeDown = () => { // push down
        this._lock = true;
        this._abortController.abort();
    }

    onRangeInput = e => {
        this._lock = true; // move
        this._fetchArch(this._rangeUrl, { range: e.target.value });
    }

    onRangeChange = val => { // release
        this._lock = false;
        this._abortController.abort();
        this._video.play();
        this._datetime = '';  // prevent empty response & force loading
        this._fetchArch(this._rangeUrl, { range: val }, null, true);
    }

    _onSourceOpen = () => {
        this._sourceBuffer = this._mediaSource.addSourceBuffer(this._sourceType);
        this._sourceBuffer.mode = 'sequence';
        this._fetch(this._liveUrl, {}, () => {
            this._video.play().catch(e => {
                console.error(e.message);
                this.showPlayBtn();
            });
        });
    }

    _onTimeUpdate = () => {
        if (this._lock || this._progress || this._sourceBuffer.timestampOffset - this._video.currentTime > 0) {
            return;
        }
        if (this._playMode == 'live') {
            this._fetch(this._liveUrl, {});
        } else {
            this._fetch(this._nextUrl, { step: 1 });
        }
    }

    _setCurrentTime = () => {
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

    _getUrl = (url, args = {}) => {
        Object.entries(args).forEach(([key, val]) => {
            url = url.replace('{' + key + '}', val);
        });
        url = url.replace('{dt}', this._datetime);
        if (this.btnMotion && this.btnMotion.classList.contains('selected')) {
            url += '&md=' + this.motionRange.value;
        }
        return url;
    }

    _fetchArch = (url, args, callback, force = false) => {
        this._playMode = 'arch';
        this._setTime = 1;
        this._fetch(url, args, callback, force);
        for (const e of this.footer.querySelectorAll('.arch')) {
            e.classList.remove('disabled');
        }
    }

    _fetch = (url, args, callback = null, force = false) => {
        if (!force && (this._progress || this._sourceBuffer.updating)) {
            return;
        }
        url = this._getUrl(url, args);
        this._progress = true;
        let datetime, rng;
        this._abortController = new AbortController();
        fetch(url, {
            cache: 'no-store',
            signal: this._abortController.signal
        })
            .then(r => {
                datetime = r.headers.get('x-datetime');
                rng = r.headers.get('x-range');
                return r.arrayBuffer();
            })
            .then(data => {
                if (!data.byteLength) { // retry after camera failure
                    clearTimeout(this._fetchTimeoutId);
                    this._fetchTimeoutId = window.setTimeout(() => {
                        this._progress = false;
                        this._fetch(url, args, callback, force);
                    }, 4000);
                    return;
                }
                this._progress = false;
                delete window.frameLoading[this._hash];
                if (!Object.keys(window.frameLoading).length) {
                    this.loader.classList.add('hidden');
                }
                this._sourceBuffer.appendBuffer(data);
                this._datetime = datetime;
                if (this._playMode != 'live' && rng > this.MAX_RANGE) {
                    this._setLiveMode();
                }
                if (this.timeRange && !this._lock) {
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
            .catch(error => {
                this._progress = false;
            });
    }
}
