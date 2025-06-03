class Base {
    ASPECT_RATIO = 16 / 9;
    MAX_SPEED_DESKTOP = 10;
    MAX_SPEED_MOBILE = 3;
    MAX_RANGE = 2000;

    header = document.querySelector('header');
    footer = document.querySelector('footer');
    btnPlay = this.footer.querySelector('.play');
    btnPause = this.footer.querySelector('.pause');
    btnMotion = this.footer.querySelector('.motion');
    btnSpeed = this.footer.querySelector('.speed');
    speedRange = this.footer.querySelector('.speed-range');
    motionRange = this.footer.querySelector('.motion-range');
    timeRange = this.footer.querySelector('.time-range');
    loader = document.querySelector('.loader');

    resizeBars = () => {
        this.showBars();

        const vp = window.visualViewport;
        let scale = 1;
        if ('userAgentData' in navigator && navigator.userAgentData.mobile) {
            scale = window.outerWidth / vp.width;
            this.header.style.transform = 'scale(' + 1 / scale + ')';
            this.footer.style.transform = 'scale(' + 1 / scale + ')';
        }
        this.header.style.left = vp.pageLeft + 'px';
        this.header.style.top = vp.pageTop + 'px';
        this.footer.style.left = vp.pageLeft + 'px';
        this.footer.style.top = vp.pageTop + vp.height - this.footer.offsetHeight / scale + 'px';

        if (this.speedRange) {
            this.speedRange.classList.add('hidden');
        }
        if (this.motionRange) {
            this.motionRange.classList.add('hidden');
        }
        this.fadeBars();
    }

    hideBars = () => {
        for (const bar of document.querySelectorAll('.bar')) {
            bar.classList.add('hidden');
        }
    }

    showBars = () => {
        for (const bar of document.querySelectorAll('.bar')) {
            bar.classList.remove('hidden', 'invisible');
        }
    }

    fadeBars = () => {
        for (const bar of document.querySelectorAll('.bar')) {
            bar.classList.add('invisible');
        }
    }

    showPlayBtn = () => {
        if (this.btnPause) {
            this.btnPause.classList.add('hidden');
        }
        this.btnPlay.classList.remove('hidden');
    }

    showPauseBtn = () => {
        this.btnPlay.classList.add('hidden');
        if (this.btnPause) {
            this.btnPause.classList.remove('hidden');
        }
    }

    back = () => {
        this.header.querySelector('.back-btn').classList.add('blink');
        const group_hash = sessionStorage.getItem('group_hash');
        if (group_hash) {
            document.location.href = `/?page=group&hash=${group_hash}`;
        } else {
            document.location.href = '/';
        }
    }

    replaceLocation = href => {
        this.header.querySelector('.link-btn').classList.add('blink');
        document.location.replace(href);
    }

    onWheel = (box, e) => {
        e.preventDefault();
        let step = 1.1;
        let dir = 1;
        if (e.wheelDelta < 0) {
            step = 0.9;
            dir = -1;
        }
        const rect = box.getBoundingClientRect();
        const aspectRatio = rect.width / rect.height;
        if (window.innerWidth / window.innerHeight > aspectRatio) {
            if (e.wheelDelta > 0 && box.scrollHeight >= window.innerHeight * 10)
                return;
            if (e.wheelDelta < 0 && box.scrollHeight * step <= window.innerHeight) {
                box.style.height = '100vh';
                return;
            }
            box.style.height = Math.round(box.scrollHeight * step) + 'px';
        } else {
            if (e.wheelDelta > 0 && box.scrollWidth >= window.innerWidth * 10)
                return;
            if (e.wheelDelta < 0 && box.scrollWidth * step <= window.innerWidth) {
                box.style.width = '100vw';
                return;
            }
            box.style.width = Math.round(box.scrollWidth * step) + 'px';
        }
        window.scroll(
            window.scrollX + (e.clientX - rect.left) / 10 * dir,
            window.scrollY + (e.clientY - rect.top) / 10 * dir
        );
    }
}
