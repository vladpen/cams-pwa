class Cam extends Base {
    constructor(video, days) {
        super();
        this._video = video;
        this._days = days;
        const urlParams = new URLSearchParams(window.location.search);
        this._id = urlParams.get('id');
        const cams = this.getCams();
        this._cam = this._id && this._id in cams ? cams[this._id] : null;
    }

    run = () => {
        this.header.querySelector('.back-btn').onclick = this.back;

        if (!this._cam) {
            this.loader.classList.add('hidden');
            return false;
        }
        this._player = new Player(this._video, this._cam.key);

        document.title = this._cam.name;
        document.querySelector('header .title').innerHTML = this._cam.name;

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

        const box = this._video.parentElement;
        box.onwheel = e => {
            this.onWheel(box, e);
        }
        this.btnPlay.onclick = this._togglePlay;
        this.btnPause.onclick = this._togglePlay;

        this.timeRange.onmousedown = this._onRangeDown;
        this.timeRange.ontouchstart = this._onRangeDown;
        this.timeRange.onmouseup = this._onRangeChange;
        this.timeRange.ontouchend = this._onRangeChange;
        this.timeRange.oninput = this._player.onRangeInput;

        if ('userAgentData' in navigator && navigator.userAgentData.mobile) {
            this.speedRange.max = this.MAX_SPEED_MOBILE;
        } else {
            this.speedRange.max = this.MAX_SPEED_DESKTOP;
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
        this.footer.querySelector('.range-box').style.backgroundSize = (100 / this._days + 1) + "% 50px";
        this.btnMotion.onclick = this._toggleMotion;
        this.btnSpeed.onclick = this._toggleSpeed;

        this.speedRange.onchange = () => {
            this._setPlaybackRate();
            sessionStorage.setItem('cam_speed', this.speedRange.value);
        };
        this.motionRange.onchange = () => {
            sessionStorage.setItem('cam_motion', this.motionRange.value);
        };
        if (sessionStorage.getItem('cam_speed')) {
            this.speedRange.value = sessionStorage.getItem('cam_speed');
        }
        if (sessionStorage.getItem('cam_motion')) {
            this.motionRange.value = sessionStorage.getItem('cam_motion');
        }
        const btnLink = this.header.querySelector('.link-btn');
        const svgLink = this.header.querySelector('.link-svg');
        btnLink.append(svgLink);
        btnLink.setAttribute('data-id', this._id);
        btnLink.onclick = () => {
            btnLink.classList.add('blink');
            document.location.replace(`/?page=events&id=${this._id}`);
        }
        this.isPlaying = true;
        this.wakeLock();

        return true;
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
            this._setPlaybackRate();
            this.isPlaying = true;
            this.wakeLock();
        } else {
            this._video.pause();
            this.showPlayBtn();
            this.isPlaying = false;
            this.wakeRelease();
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

    _onResize = (e) => {
        this.hideBars();
        if (window.innerWidth / window.innerHeight > this.ASPECT_RATIO) {
            this._video.parentElement.classList.add('fit-height');  // left & right margins, height = 100%
            this._video.parentElement.classList.remove('fit-width');
        } else {
            this._video.parentElement.classList.add('fit-width');  // top & bottom margins, width = 100%
            this._video.parentElement.classList.remove('fit-height');
        }
        this.resizeBars();
    }

    _seek = e => {
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
        document.body.classList.add('arch');
    }

    _setPlaybackRate = () => {
        if (this.btnSpeed.classList.contains('selected')) {
            this._video.playbackRate = this.speedRange.value;
        }
    }
}
