class Events extends Base {
    constructor(image, camInfo, chartData) {
        super();
        this._image = image;
        const urlParams = new URLSearchParams(window.location.search);
        this._hash = urlParams.get('hash');
        this._timeoutId;
        this._slider = new Slider(image, this._hash, camInfo);
        this._chartData = chartData;
    }

    run = () => {
        this.header.querySelector('.back-btn').onclick = this.back;
        this.header.querySelector('.link-btn').onclick = () => {
            this.loader.classList.remove('hidden');
            document.location.replace(`/?page=cam&hash=${this._hash}`);
        }
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = e => {
            if (e.target.type != 'range') {
                this.hideBars();
            }
        }
        window.onresize = this._onResize;
        this._onResize();

        this._slider.run();

        this.btnPlay.onclick = this._togglePlay;
        this.btnPause.onclick = this._togglePlay;

        this.timeRange.onmousedown = this._onRangeDown;
        this.timeRange.ontouchstart = this._onRangeDown;
        this.timeRange.onmouseup = this._onRangeChange;
        this.timeRange.ontouchend = this._onRangeChange;
        this.timeRange.oninput = this._onRangeInput;

        this.header.onmousedown = this.showBars;
        this.header.ontouchstart = this.showBars;
        this.header.onmouseup = this.fadeBars;
        this.header.ontouchend = this.fadeBars;
        this.footer.onmousedown = this.showBars;
        this.footer.ontouchstart = this.showBars;
        this.footer.onmouseup = this.fadeBars;
        this.footer.ontouchend = this.fadeBars;

        this.footer.querySelector('.rwd .arrow').onclick = this._seek;
        this.footer.querySelector('.fwd .arrow').onclick = this._seek;

        this.btnSpeed.onclick = this._toggleSpeed;

        this.speedRange.onchange = () => {
            localStorage.setItem('events_speed_' + this._hash, this.speedRange.value);
        };
        if (localStorage.getItem('events_speed_' + this._hash)) {
            this.speedRange.value = localStorage.getItem('events_speed_' + this._hash);
        }
        this._plotCart(this._chartData);
    }

    _onRangeDown = () => {
        clearTimeout(this._timeoutId);
        this._slider.onRangeDown();
        this.footer.querySelector('.rwd').classList.remove('disabled');
        this.footer.querySelector('.fwd').classList.remove('disabled');
    }

    _onRangeInput = e => {
        this._slider.onRangeInput(e.target.value);
    }

    _onRangeChange = () => {
        this._slider.onRangeChange(this._next);
    }

    _onResize = () => {
        this.hideBars();
        if (window.innerWidth / window.innerHeight < this.ASPECT_RATIO) {
            this._image.parentElement.classList.add('fit-width');  // top & bottom margins, width = 100%
            this._image.parentElement.classList.remove('fit-height');
        } else {
            this._image.parentElement.classList.add('fit-height');  // left & right margins, height = 100%
            this._image.parentElement.classList.remove('fit-width');
        }
        this.resizeBars();
    }

    _togglePlay = () => {
        if (this.footer.querySelector('.fwd').classList.contains('disabled')) {
            return;
        }
        if (!this.btnPlay.classList.contains('hidden')) {
            this.showPauseBtn();
            this._next();
            Bell.wakeLock();
        } else {
            clearTimeout(this._timeoutId);
            this.showPlayBtn();
            Bell.wakeRelease();
        }
    }

    _toggleSpeed = () => {
        if (this.btnSpeed.closest('.disabled')) {
            return;
        }
        if (this.btnSpeed.classList.contains('selected')) {
            this.btnSpeed.classList.remove('selected');
            this.speedRange.classList.add('hidden');
        } else {
            this.btnSpeed.classList.add('selected');
            this.speedRange.classList.remove('hidden');
        }
    }

    _seek = e => {
        if (e.target.closest('.disabled')) {
            return;
        }
        this.loader.classList.remove('hidden');
        this._slider.seek(e.target.closest('svg').dataset.step, this._next);
    }

    _next = () => {
        if (!this.btnPlay.classList.contains('hidden')) {
            return;
        }
        clearTimeout(this._timeoutId);
        this._timeoutId = setTimeout(this._nextSlide, this._getSpeed());
    }

    _nextSlide = () => {
        if (this.footer.querySelector('.fwd').classList.contains('disabled')) {
            return;
        }
        this._slider.seek(1, this._next);
    }

    _getSpeed = () => {
        if (this.btnSpeed.classList.contains('selected')) {
            return 1000 / this.speedRange.value;
        }
        return 1000;
    }

    _plotCart = (rawData) => {
        if (rawData.length < 3) {
            return;
        }
        const svg = this.footer.querySelector('.chart svg');
        const barWidth = 100 / rawData.length;
        const rectWidth = barWidth / 2;
        const maxCount = Math.max(...rawData);
        const minCount = Math.min(...rawData);
        const chartData = [];
        let offsetX = barWidth / 4;
        rawData.forEach(cnt => {
            const rectHeight = (cnt - minCount) * 100 / maxCount;
            const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            bar.setAttribute('x', `${offsetX}%`);
            bar.setAttribute('y', '100%');
            bar.setAttribute('height', `${rectHeight}%`);
            bar.setAttribute('width', `${rectWidth}%`);
            svg.appendChild(bar);
            offsetX += barWidth;
            chartData.push([bar, 100 - rectHeight]);
        });
        setTimeout(() => {
            chartData.forEach(bar => {
                bar[0].setAttribute('y', `${bar[1]}%`);
            });
        }, 100);
    }
}
