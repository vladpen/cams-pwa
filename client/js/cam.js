class Cam extends Base {
    run = (id, days) => {
        this._videoBox = document.getElementById(id);

        const urlParams = new URLSearchParams(window.location.search),
            hash = urlParams.get('hash');

        this.header.querySelector('.back').onclick = () => {
            const group = urlParams.get('grp')
            if (group) {
                document.location.href = `/?page=group&hash=${group}`;
            } else {
                document.location.href = '/';
            }
        }
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = (e) => {
            if (e.target.type != 'range') {
                this.hideBars();
            }
        }
        window.onresize = this._onResize;
        this._onResize();

        this._player = new Player()
        this._player.start(id, hash);

        this.showPauseBtn();
        this.btnPlay.onclick = this._togglePlay;
        this.btnPause.onclick = this._togglePlay;

        this.timeRange.onmousedown = this._stop;
        this.timeRange.ontouchstart = this._stop;
        this.timeRange.onmouseup = this._onRangeChange;
        this.timeRange.ontouchend = this._onRangeChange;

        for (const e of this.footer.querySelectorAll('.arch-range')) {
            e.onmousedown = this.showBars;
            e.ontouchstart = this.showBars;
            e.onmouseup = this.fadeBars;
            e.ontouchend = this.fadeBars;
        }

        if (!navigator.userAgentData.mobile) {
            this.timeRange.oninput = this._player.onRangeInput;
        } else {
            this.speedRange.max = this.MAX_SPEED_MOBILE;
        }
        this.footer.querySelector('.rwd').onclick = this._rwd;
        this.footer.querySelector('.fwd').onclick = this._fwd;
        this.footer.querySelector('.range-box').style.backgroundSize = 100 / days + "% 50px";
        this.btnMotion.onclick = this._toggleMotion;
        this.btnSpeed.onclick = this._toggleSpeed;

        if (localStorage.getItem('speed_' + hash)) {
            this.speedRange.value = localStorage.getItem('speed_' + hash);
        }
        if (localStorage.getItem('motion_' + hash)) {
            this.motionRange.value = localStorage.getItem('motion_' + hash);
        }
    }

    _onRangeChange = () => {
        this.showBars();
        this._player.onRangeChange(this.timeRange.value);
        this._setArchMode();
    }

    _togglePlay = () => {
        const active = this._videoBox.querySelector('.active');
        this.showBars();
        if (!this.btnPlay.classList.contains('hidden')) {
            active.play().then(this.fadeBars);
            this.showPauseBtn();
            if (this.btnSpeed.classList.contains('selected')) {
                active.playbackRate = this.speedRange.value;
            }
        } else {
            active.play().then(this.fadeBars);
            active.pause();
            this.showPlayBtn();
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
            this._videoBox.querySelector('.active').playbackRate = 1;
            this.speedRange.classList.add('hidden');
        } else {
            this.btnSpeed.classList.add('selected');
            this._videoBox.querySelector('.active').playbackRate = this.speedRange.value;
            this.speedRange.classList.remove('hidden');
        }
    }

    _onResize = () => {
        this.hideBars();
        const scale = window.outerWidth / window.visualViewport.width;
        if (window.innerWidth / window.innerHeight < this.ASPECT_RATIO) { // vertical
            let width = window.innerWidth * scale;
            this._videoBox.style.width = width + 'px';
            this._videoBox.style.height = width / this.ASPECT_RATIO + 'px';
        } else {
            let heihgt = window.innerHeight * scale;
            this._videoBox.style.height = heihgt + 'px';
            this._videoBox.style.width = heihgt * this.ASPECT_RATIO + 'px';
        }
        this.resizeBars();
    }

    _stop = () => {
        this.showBars();
        this._videoBox.querySelector('.active').pause();
    }

    _rwd = (e) => {
        this._camSeek(e, -1);
    }

    _fwd = (e) => {
        if (e.target.closest('.disabled')) {
            return;
        }
        this._camSeek(e, 1);
    }

    _camSeek = (e, direction) => {
        this._stop();
        const btn = e.target.closest('.arrow');
        const rect = btn.getBoundingClientRect();
        let mouseX = e.clientX - rect.left;
        if (direction < 0) {
            mouseX -= rect.width;
        }
        let step = parseInt(mouseX * 4 / rect.width) + direction;
        this._player.seek(step);
        this._setArchMode();
    }

    _setArchMode = () => {
        this.btnPlay.classList.add('hidden');
        this.btnPause.classList.remove('hidden');
        for (const e of this.footer.querySelectorAll('.arch')) {
            e.classList.remove('disabled');
        }
        this.header.querySelector('.loader').classList.remove('hidden');
        this.fadeBars();
    }
}
