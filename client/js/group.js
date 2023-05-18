class Group extends Base {
    constructor(cams) {
        super();
        this._cams = cams;
    }

    run = () => {
        const box = document.querySelector('.group-box');
        for (let hash in this._cams) {
            const frame = document.createElement('div');
            frame.classList.add('video-box');
            const video = document.createElement('video');
            frame.append(video);
            box.append(frame);

            frame.onclick = () => {
                const urlParams = new URLSearchParams(window.location.search);
                document.location.href = `/?page=cam&hash=${hash}&grp=${urlParams.get('hash')}`;
                let overlay = document.createElement('div');
                frame.append(overlay);
            }
            const player = new Player(video, hash, this._cams[hash]);
            player.start();
        }
        document.querySelector('main').onclick = this.resizeBars;
        document.onscroll = this.hideBars;
        document.ontouchmove = this.hideBars;

        this.header.querySelector('.back').onclick = () => {
            document.location.href = '/';
        }
        window.onresize = this._onResize;
        this._onResize();

        this.btnPlay.classList.add('hidden');
        this.btnPlay.onclick = () => {
            for (const video of document.querySelectorAll('video')) {
                video.play();
            }
            this.footer.remove();
        }
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
