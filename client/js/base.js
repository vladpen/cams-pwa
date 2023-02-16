class Base {
    ASPECT_RATIO = 16 / 9;
    MAX_PLAYBACK_RATE = 5.0;
    MD_SENS = 50;

    header = document.querySelector('header');
    footer = document.querySelector('footer');
    btnPlay = this.footer.querySelector('.play');
    btnPause = this.footer.querySelector('.pause');
    btnMotion = this.footer.querySelector('.motion');
    btnSpeed = this.footer.querySelector('.speed');
    inputRange = this.footer.querySelector('.range');
    loader = document.querySelector('.loader');

    resizeBars = () => {
        this.showBars();

        const vp = window.visualViewport;
        const scale = window.outerWidth / vp.width;

        this.header.style.left = vp.pageLeft + 'px';
        this.header.style.top = vp.pageTop + 'px';
        this.header.style.width = window.outerWidth + 'px';
        this.header.style.transform = 'scale(' + 1 / scale + ')';

        this.footer.style.left = vp.pageLeft + 'px';
        this.footer.style.top = vp.pageTop + vp.height - (this.footer.offsetHeight) / scale + 'px';
        this.footer.style.width = window.outerWidth + 'px';
        this.footer.style.transform = 'scale(' + 1 / scale + ')';

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

    getCookie = (name) => {
        const value = '; ' + document.cookie;
        const parts = value.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
    }
}
