class Group extends Base {
    constructor() {
        super();
        const urlParams = new URLSearchParams(window.location.search);
        this._id = urlParams.get('id');
        this._cams = [];
        this._name = '';
        let groups = localStorage.getItem('groups');
        if (groups) {
            groups = JSON.parse(groups);
        }
        if (groups && this._id in groups) {
            this._cams = (groups[this._id].cams).split(',');
            this._name = groups[this._id].name;
        }
    }

    run = () => {
        this.header.querySelector('.back-btn').onclick = e => {
            this.wakeRelease();
            e.target.classList.add('blink');
            document.location.href = '/';
        }
        if (!this._cams || !this._name) {
            this.loader.classList.add('hidden');
            return;
        }
        document.title = this._name;
        document.querySelector('header .title').innerHTML = this._name;

        const box = document.querySelector('.group-box');
        const frameTemplate = box.querySelector('.video-box');

        for (let i = 1; i < this._cams.length; i++) {
            box.append(frameTemplate.cloneNode(true));
        }
        const cams = this.getCams();
        const frames = box.querySelectorAll('.video-box');
        frames.forEach((frame, i) => {
            const video = frame.querySelector('video');
            const id = this._cams[i];
            if (!id || !(id in cams)) {
                return;
            }
            frame.onclick = () => {
                frame.classList.add('blink');
                document.location.href = `/?page=cam&id=${id}`;
            }
            const player = new Player(video, cams[id].key);
            player.start();
        });
        box.onwheel = e => {
            this.onWheel(box, e);
        }
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = this.hideBars;

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

        sessionStorage.setItem('group_id', this._id);
        this.isPlaying = true;
        this.wakeLock();
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
