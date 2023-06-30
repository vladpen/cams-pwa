class Slider extends Base {
    constructor(image, hash, camInfo) {
        super();
        this._image = image;
        this._hash = hash;
        this._rangeUrl = '/?image=range&range={range}&pos={position}&hash=' + hash;
        this._nextUrl = '/?image=next&step={step}&pos={position}&hash=' + hash;
        this._position = '';
        this._lock = false;
        this._loading = false;
        this._abortController;
    }

    run = () => {
        this.loader.classList.remove('hidden');
        this._fetch(this._nextUrl, { step: 0 });
    }

    seek = (step, callback = null) => {
        this._abortController.abort();
        this._fetch(this._nextUrl, { step: step }, () => {
            if (step < 0) {
                this.footer.querySelector('.fwd').classList.remove('disabled');
            }
            if (callback) {
                callback();
            }
        }, true);
    }

    onRangeDown = () => { // push down
        this._lock = true;
        this._abortController.abort();
    }

    onRangeInput = (range) => { // move
        this._lock = true;
        this._fetch(this._rangeUrl, { range: range });
    }

    onRangeChange = (callback) => { // release
        this._lock = false;
        callback();
    }

    _getUrl = (url, args = {}) => {
        Object.entries(args).forEach(([key, val]) => {
            url = url.replace('{' + key + '}', val);
        });
        url = url.replace('{position}', this._position);
        return url;
    }

    _fetch = (url, args, callback = null, force = false) => {
        if (!force && this._loading) {
            return;
        }
        url = this._getUrl(url, args);
        this._loading = true;
        let position, rng;
        this._abortController = new AbortController();
        fetch(url, {
            cache: 'no-store',
            signal: this._abortController.signal
        })
            .then(r => {
                position = r.headers.get('X-Position');
                rng = r.headers.get('X-Range');
                return r.blob();
            })
            .then(data => {
                this._loading = false;
                this.loader.classList.add('hidden');
                if (!data.size) {
                     return;
                }
                this._image.src = URL.createObjectURL(data);
                this._position = position;
                if (!this._lock) {
                    this.timeRange.value = rng;
                    if (rng > this.MAX_RANGE) {
                        this.footer.querySelector('.rwd').classList.remove('disabled');
                        this.footer.querySelector('.fwd').classList.add('disabled');
                        this.btnSpeed.classList.remove('selected');
                    } else if (rng < 0) {
                        this.footer.querySelector('.fwd').classList.remove('disabled');
                        this.footer.querySelector('.rwd').classList.add('disabled');
                    }
                    if (callback) {
                        callback();
                    }
                }
            })
            .catch(error => {
                this._loading = false;
            });
    }
}
