class Group extends Base {
    constructor(cams) {
        super();
        this._cams = cams;
    }

    run = () => {
        const box = document.querySelector('.group-box');
        const frame_template = box.querySelector('.video-box');
        const hashes = Object.keys(this._cams);

        for (let i = 1; i < hashes.length; i++) {
            box.appendChild(frame_template.cloneNode(true));
        }
        const frames = box.querySelectorAll('.video-box');
        frames.forEach((frame, i) => {
            const video = frame.querySelector('video');
            const hash = hashes[i];

            frame.onclick = () => {
                frame.classList.add('blink');
                document.location.href = `/?page=cam&hash=${hash}`;
            }
            const player = new Player(video, hash, this._cams[hash]);
            player.start();
        });
        box.onwheel = e => {
            this.onWheel(box, e);
        }
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = this.hideBars;

        this.header.querySelector('.back-btn').onclick = e => {
            e.target.classList.add('blink');
            document.location.href = '/';
        }
        this.header.onmousedown = this.showBars;
        this.header.ontouchstart = this.showBars;
        this.header.onmouseup = this.fadeBars;
        this.header.ontouchend = this.fadeBars;
        this.footer.onmousedown = this.showBars;
        this.footer.ontouchstart = this.showBars;
        this.footer.onmouseup = this.fadeBars;
        this.footer.ontouchend = this.fadeBars;

        this.btnPlay.classList.add('hidden');
        this.btnPlay.onclick = () => {
            for (const video of document.querySelectorAll('video')) {
                video.play();
            }
            this.btnPlay.classList.add('hidden');
        }
        window.onresize = this._onResize;
        this._onResize();

        const urlParams = new URLSearchParams(window.location.search);
        sessionStorage.setItem('group_hash', urlParams.get('hash'));
        Bell.wakeLock();
    }

    _onResize = () => {
        this.hideBars();
        const box = document.querySelector('.group-box');
        const frames = box.querySelectorAll('.video-box');
        const width = document.body.clientWidth;
        const height = document.body.clientHeight;

        let cellQty = 1;
        if (width < height) { // vertical screen
            cellQty = Math.max(4, frames.length - 5 / frames.length) / 4; // 1 column for up to 5 cells
        } else {
            cellQty = frames.length; // horizontal screen
        }
        const columnCount = Math.ceil(Math.sqrt(cellQty));
        const rowCount = Math.ceil(frames.length / columnCount);
        const rootAspectRatio = width / height;
        const videoAspectRatio = this.ASPECT_RATIO * columnCount / rowCount;

        box.style.aspectRatio = videoAspectRatio;
        if (rootAspectRatio > videoAspectRatio) {
            box.classList.remove('fit-width');
            box.classList.add('fit-height');
        } else {
            box.classList.remove('fit-height');
            box.classList.add('fit-width');
        }
        const w = 100 / columnCount + '%';
        for (const frame of frames) {
            frame.style.width = w;
        }
        this.resizeBars();
    }
}
