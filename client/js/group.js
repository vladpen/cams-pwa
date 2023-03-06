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
        window.onclick = this.resizeBars;
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
        const frames = document.querySelectorAll('.group-box .video-box');

        let cellQty = 1,
            width = document.body.clientWidth,
            height = document.body.clientHeight;

        if (width < height) { // vertical
            cellQty = Math.max(4, frames.length - 5 / frames.length) / 4; // 1 column for up to 5 cells
        } else {
            cellQty = frames.length; // horizontal
        }
        let columnCount = Math.ceil(Math.sqrt(cellQty));
        let rowCount = Math.ceil(frames.length / columnCount);
        let frameHeight = 0;
        let rootAspectRatio = width / height;
        let videoAspectRatio = this.ASPECT_RATIO * columnCount / rowCount;

        if (rootAspectRatio > videoAspectRatio) { // vertical margins
            frameHeight = height / rowCount;
        } else {
            frameHeight = width / columnCount / this.ASPECT_RATIO; // horizontal margins
        }
        let frameWidth = frameHeight * this.ASPECT_RATIO;

        for (const frame of frames) {
            frame.style.height = frameHeight + 'px';
            frame.style.width = frameWidth + 'px';
        }
        this.resizeBars();
    }
}
