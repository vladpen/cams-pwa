class Group extends Base {
    run = cams => {
        const box = document.querySelector('.group-box');
        for (let i = 0; i < cams.length; i++) { //  const hash of cams
            const hash = cams[i];
            const frame = document.createElement('div');
            frame.id = 'vb' + i;
            frame.classList.add('video-box');
            box.append(frame);
            const active = document.createElement('video');
            active.classList.add('active');
            const hidden = document.createElement('video');
            hidden.classList.add('hidden');
            frame.append(active, hidden);

            frame.onclick = () => {
                const urlParams = new URLSearchParams(window.location.search);
                document.location.href = `/?page=cam&hash=${hash}&grp=${urlParams.get('hash')}`;
                let overlay = document.createElement('div');
                frame.append(overlay);
            }
            const player = new Player();
            player.start(frame.id, hash);
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
            for (const active of document.querySelectorAll('.video-box .active')) {
                active.play();
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
