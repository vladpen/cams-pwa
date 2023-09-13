class Cam extends Base {
    constructor(video, camInfo, days) {
        super();
        this._video = video;
        this._days = days;
        const urlParams = new URLSearchParams(window.location.search);
        this._hash = urlParams.get('hash');
        this._player = new Player(video, this._hash, camInfo)
    }

    run = () => {
        this.header.querySelector('.back-btn').onclick = this.back;
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = e => {
            if (e.target.type != 'range') {
                this.hideBars();
            }
        }
        window.onresize = this._onResize;
        this._onResize();

        this._player.start();

        this.btnPlay.onclick = this._togglePlay;
        this.btnPause.onclick = this._togglePlay;

        this.timeRange.onmousedown = this._onRangeDown;
        this.timeRange.ontouchstart = this._onRangeDown;
        this.timeRange.onmouseup = this._onRangeChange;
        this.timeRange.ontouchend = this._onRangeChange;
        this.timeRange.oninput = this._player.onRangeInput;

        if ('userAgentData' in navigator && navigator.userAgentData.mobile) {
            this.speedRange.max = this.MAX_SPEED_MOBILE;
        }
        this.header.onmousedown = this.showBars;
        this.header.ontouchstart = this.showBars;
        this.header.onmouseup = this.fadeBars;
        this.header.ontouchend = this.fadeBars;
        this.footer.onmousedown = this.showBars;
        this.footer.ontouchstart = this.showBars;
        this.footer.onmouseup = this.fadeBars;
        this.footer.ontouchend = this.fadeBars;

        this.footer.querySelector('.rwd').onclick = this._seek;
        this.footer.querySelector('.fwd').onclick = this._seek;
        this.footer.querySelector('.range-box').style.backgroundSize = 100 / this._days + "% 50px";
        this.btnMotion.onclick = this._toggleMotion;
        this.btnSpeed.onclick = this._toggleSpeed;

        this.speedRange.onchange = () => {
            localStorage.setItem('speed_' + this._hash, this.speedRange.value);
        };
        this.motionRange.onchange = () => {
            localStorage.setItem('motion_' + this._hash, this.motionRange.value);
        };
        if (localStorage.getItem('speed_' + this._hash)) {
            this.speedRange.value = localStorage.getItem('speed_' + this._hash);
        }
        if (localStorage.getItem('motion_' + this._hash)) {
            this.motionRange.value = localStorage.getItem('motion_' + this._hash);
        }
        this.header.querySelector('.link-btn').onclick = () => {
            this.loader.classList.remove('hidden');
            document.location.replace(`/?page=events&hash=${this._hash}`);
        }
        Bell.wakeLock();
    }

    _onRangeDown = () => {
        this._video.pause();
        this._player.onRangeDown();
    }

    _onRangeChange = () => {
        this._player.onRangeChange(this.timeRange.value);
        this._setArchMode();
    }

    _togglePlay = () => {
        if (!this.btnPlay.classList.contains('hidden')) {
            this._video.play();
            this.showPauseBtn();
            if (this.btnSpeed.classList.contains('selected')) {
                this._video.playbackRate = this.speedRange.value;
            }
            Bell.wakeLock();
        } else {
            // this._video.play();
            this._video.pause();
            this.showPlayBtn();
            Bell.wakeRelease();
        }
    }

    _toggleMotion = () => {
        if (this.btnMotion.closest('.disabled')) {
            return;
        }
        if (this.btnMotion.classList.contains('selected')) {
            this.btnMotion.classList.remove('selected');
            this.motionRange.classList.add('hidden');
        } else {
            this.btnMotion.classList.add('selected');
            this.motionRange.classList.remove('hidden');
        }
    }

    _toggleSpeed = () => {
        if (this.btnSpeed.closest('.disabled')) {
            return;
        }
        if (this.btnSpeed.classList.contains('selected')) {
            this.btnSpeed.classList.remove('selected');
            this._video.playbackRate = 1;
            this.speedRange.classList.add('hidden');
        } else {
            this.btnSpeed.classList.add('selected');
            this._video.playbackRate = this.speedRange.value;
            this.speedRange.classList.remove('hidden');
        }
    }

    _onResize = () => {
        this.hideBars();
        if (window.innerWidth / window.innerHeight < this.ASPECT_RATIO) {
            this._video.parentElement.classList.add('fit-width');  // top & bottom margins, width = 100%
            this._video.parentElement.classList.remove('fit-height');
        } else {
            this._video.parentElement.classList.add('fit-height');  // left & right margins, height = 100%
            this._video.parentElement.classList.remove('fit-width');
        }
        this.resizeBars();
    }

    _seek = (e) => {
        if (e.target.closest('.disabled')) {
            return;
        }
        this._video.pause();
        this._player.seek(e.target.closest('svg').dataset.step);
        this._setArchMode();
    }

    _setArchMode = () => {
        this.btnPlay.classList.add('hidden');
        this.btnPause.classList.remove('hidden');
        for (const e of this.footer.querySelectorAll('.arch')) {
            e.classList.remove('disabled');
        }
        this.header.querySelector('.loader').classList.remove('hidden');
        document.body.classList.add('arch');
    }
}
