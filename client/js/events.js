class Events extends Base {
    constructor() {
        super();
        this._image = document.querySelector('.image-box img');
        const urlParams = new URLSearchParams(window.location.search);
        this._id = urlParams.get('id');
        const cams = this.getCams();
        this._cam = this._id in cams ? cams[this._id] : {};
        this._timeoutId;
        this._slider = new Slider(this._image, this._cam.key);
    }

    run = () => {
        this.header.querySelector('.back-btn').onclick = this._back;
        const btnLink = this.header.querySelector('.link-btn');
        const svgLink = this.header.querySelector('.link-svg');
        btnLink.append(svgLink);
        btnLink.classList.remove('hidden');
        btnLink.onclick = this._back;
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = e => {
            if (e.target.type != 'range') {
                this.hideBars();
            }
        }
        document.querySelector('header .title').innerHTML = this._cam.name;

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
            sessionStorage.setItem('events_speed', this.speedRange.value);
        };
        if (sessionStorage.getItem('events_speed')) {
            this.speedRange.value = sessionStorage.getItem('events_speed');
        }
        this._plotCart();
    }

    _back = e => {
        e.target.classList.add('blink');
        document.location.href = `/?page=cam&id=${this._id}`;
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
            this.wakeLock();
        } else {
            clearTimeout(this._timeoutId);
            this.showPlayBtn();
            this.wakeRelease();
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

    _plotCart = () => {
        fetch('/?chart=' + this._cam.key)
            .then(r => {
                if (!r.ok) {
                    throw new Error(`fetch status: ${r.status}`);
                }
                return r.json();
            })
            .then(points => {
                if (points.length < 3) {
                    return;
                }
                const svg = this.footer.querySelector('.chart svg');
                const barWidth = 100 / points.length;
                const rectWidth = barWidth / 2;
                const maxCount = Math.max(...points);
                const minCount = Math.min(...points);
                const chartData = [];
                let offsetX = barWidth / 4;
                for (const cnt of points) {
                    const rectHeight = (cnt - minCount) * 100 / maxCount;
                    const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    bar.setAttribute('x', `${offsetX}%`);
                    bar.setAttribute('y', '100%');
                    bar.setAttribute('height', `${rectHeight}%`);
                    bar.setAttribute('width', `${rectWidth}%`);
                    svg.append(bar);
                    offsetX += barWidth;
                    chartData.push([bar, 100 - rectHeight]);
                }
                setTimeout(() => {
                    for (const bar of chartData) {
                        bar[0].setAttribute('y', `${bar[1]}%`);
                    }
                }, 100);
            })
            .catch(e => {
                console.error(e);
            });
    }
}
