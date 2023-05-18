class Player extends Base {
    _BUFFERED_TIME = 10;
    constructor(video, hash, camInfo) {
        super();
        this._video = video;
        this._hash = hash;
        this._liveUrl = '/?live=1&dt={dt}&hash=' + hash;
        this._rangeUrl = '/?range={range}&dt={dt}&hash=' + hash;
        this._nextUrl = '/?next={step}&dt={dt}&hash=' + hash;
        this._datetime = '';
        this._timestampOffset = -1;
        this._lock = false;
        this._setTime = 0;
        this._progress = false;
        this._abortController;
        this._sourceBuffer;
        this._sourceType = `video/mp4; codecs="${camInfo['codecs']}"`;
        this._mediaSource = new MediaSource();
    }

    start = () => {
        this._setLiveMode();

        if ('MediaSource' in window && MediaSource.isTypeSupported(this._sourceType)) {
            this._mediaSource.addEventListener('sourceopen', this._onSourceOpen, { once: true });
            this._video.src = URL.createObjectURL(this._mediaSource);
            this._video.ontimeupdate = this._onTimeUpdate;
        } else {
            console.error('Unsupported MIME type or codec:', this._sourceType);
            return;
        }
        if (!window.frameLoading) {
            window.frameLoading = {}
        }
        window.frameLoading[this._hash] = 1
    }

    seek = step => {
        this._abortController.abort();
        this._fetchArch(this._nextUrl, { step: step });
        this._video.play();
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
        this._video.play();
        this._fetchArch(this._rangeUrl, { range: val });
    }

    _onSourceOpen = () => {
        this._sourceBuffer = this._mediaSource.addSourceBuffer(this._sourceType);
        this._sourceBuffer.mode = 'sequence';
        this._fetch(this._getSrc(this._liveUrl), () => {
            this._video.play().catch(e => {
                console.error(e.message);
                this.showPlayBtn();
            });
        });
    }

    _onTimeUpdate = () => {
        if (this._lock || this._timestampOffset - this._video.currentTime > this._BUFFERED_TIME) {
            return;
        }
        this._timestampOffset = this._sourceBuffer.timestampOffset;
        if (this._playMode == 'live') {
            this._fetch(this._getSrc(this._liveUrl));
        } else {
            this._fetch(this._getSrc(this._nextUrl, { step: 1 }));
        }
    }

    _setCurrentTime = () => {
        this._video.currentTime = this._video.seekable.end(this._video.seekable.length - 1);
    }

    _setLiveMode = () => {
        this._playMode = 'live'
        this._setTime = 2;
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

    _getSrc = (url, args = {}) => {
        Object.entries(args).forEach(([key, val]) => {
            url = url.replace('{' + key + '}', val);
        });
        url = url.replace('{dt}', this._datetime);
        if (this.btnMotion && this.btnMotion.classList.contains('selected')) {
            url += '&md=' + this.motionRange.value;
        }
        return url;
    }

    _fetchArch = (url, args, callback = null) => {
        this._playMode = 'arch';
        this._fetch(this._getSrc(url, args), () => {
            this._setCurrentTime();
            if (callback) {
                callback();
            }
        });
        for (const e of this.footer.querySelectorAll('.arch')) {
            e.classList.remove('disabled');
        }
    }

    _fetch = (url, callback = null) => {
        if (this._progress || this._sourceBuffer.updating) {
            return;
        }
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
                this._progress = false;
                delete window.frameLoading[this._hash];
                if (!Object.keys(window.frameLoading).length) {
                    this.loader.classList.add('hidden');
                }
                if (!data.byteLength) {
                    return;
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
                if (this._setTime > 0) { //  && !this._video.paused
                    this._setTime -= 1;
                    this._video.currentTime = this._video.seekable.end(this._video.seekable.length - 1);
                }
            })
            .catch(error => {
                this._progress = false;
            });
    }
}
