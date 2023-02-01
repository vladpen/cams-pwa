class Player extends Base {
    _isSrcSet = false;
    _lock = false;
    _isSrcSet = false;
    _active_date_time;

    start = (videoBox, hash) => {
        this._videoBox = videoBox;
        this._liveUrl = '/?live=1&hash=' + hash;
        this._rangeUrl = '/?range={range}&hash=' + hash;
        this._nextUrl = '/?next={step}&dt={dt}&hash=' + hash;

        const active = this._videoBox.querySelector('.active');
        const hidden = this._videoBox.querySelector('.hidden');

        hidden.src = this._liveUrl;
        this._isSrcSet = true;

        active.onloadedmetadata = this._onLoadedData;
        hidden.onloadedmetadata = this._onLoadedData;
        active.ontimeupdate = this._onTimeUpdate;
        hidden.ontimeupdate = this._onTimeUpdate;
        active.onended = this._onEnded;
        hidden.onended = this._onEnded;

        window.frameCount = document.querySelectorAll('.video-box').length;

        this._setLiveMode();
    }

    seek = (step) => {
        this._setNextSrc(this._nextUrl.replace('{step}', step).replace('{dt}', this._active_date_time));
    }

    onRangeChange = (val) => {
        this._setNextSrc(this._rangeUrl.replace('{range}', val));
    }

    onRangeInput = (e) => {
        this._lock = true;
        if (this._isSrcSet) {
            return
        }
        this._videoBox.querySelector('.hidden').src = this._getSrc(this._rangeUrl.replace('{range}', e.target.value));
        this._isSrcSet = true;
        this._playMode = 'arch';
        this._playThreshold = 0.5;
    }

    _onLoadedData = (e) => {
        if (!e.target.classList.contains('hidden')) {
            return;
        }
        this._playNext();
        if (window.frameCount > 1) {
            window.frameCount--;
        } else {
            this.loader.classList.add('hidden');
        }
        if (!this._lock && this._playMode == 'arch') {
            const range = this.getCookie('rng');
            if (range == '' || range == undefined) {
                this._setLiveMode();
            } else {
                this.inputRange.value = range;
            }
        }
    }

    _onEnded = () => {
        this._playNext();
    }

    _onTimeUpdate = (e) => {
        const active = e.target;
        if (this._isSrcSet || !active.classList.contains('active')) {
            return;
        }
        if (active.currentTime / active.buffered.end(0) > this._playThreshold) {
            this._isSrcSet = true;
            const hidden = this._videoBox.querySelector('.hidden');

            if (this._playMode == 'arch') {
                hidden.src = this._getSrc(this._nextUrl.replace('{step}', 1).replace('{dt}', this._active_date_time));
            } else {
                hidden.src = this._liveUrl;
            }
            this._isSrcSet = true;
        }
    }

    _playNext = () => {
        const active = this._videoBox.querySelector('.active');
        const hidden = this._videoBox.querySelector('.hidden');

        if (!this._lock && (!active.paused || hidden.readyState < 1)) {
            return;  // paused == ended || paused
        }
        active.classList.remove('active');
        hidden.classList.add('active');
        hidden.classList.remove('hidden');
        active.classList.add('hidden');

        if (!this._lock) {
            hidden.play().catch(e => {
                console.error(e.message);
                this.showPlayBtn();
            });
        }
        this._isSrcSet = false;
        this._active_date_time = this.getCookie('dt')

        if (this.btnSpeed && this.btnSpeed.classList.contains('selected')) {
            hidden.playbackRate = this.MAX_PLAYBACK_RATE;
        }
    }

    _setLiveMode = () => {
        this._playMode = 'live'
        this._playThreshold = 0.8;
        if (this.inputRange) {
            this.inputRange.value = this.inputRange.max;
            this.btnSpeed.classList.remove('selected');
            this.btnMotion.classList.remove('selected');
            for (const i of this.footer.querySelectorAll('.arch')) {
                i.classList.add('disabled');
            }
        }
    }

    _setNextSrc = (src) => {
        this._videoBox.querySelector('.active').pause();
        const hidden = this._videoBox.querySelector('.hidden')
        hidden.src = this._getSrc(src);
        this._isSrcSet = true;
        for (const i of this.footer.querySelectorAll('.arch')) {
            i.classList.remove('disabled');
        }
        this._playMode = 'arch';
        this._playThreshold = 0.5;
        this._lock = false;
    }

    _getSrc = (src) => {
        if (this.btnMotion.classList.contains('selected')) {
            return src + '&md=' + this.MD_SENS;
        }
        return src;
    }
}
