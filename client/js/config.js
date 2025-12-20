class Config {
    static _storedCams = null;
    static _storeGroups = null;
    static _uid = null;
    static isPlaying = false;

    getCams = () => {
        if (this._storedCams) {
            return this._storedCams;
        }
        this._storedCams = {}
        const cams = localStorage.getItem('cams');
        if (cams) {
            try {
                this._storedCams = JSON.parse(cams);
            } catch (e) {
                console.error('Invalid cams JSON:', e);
            }
        }
        return this._storedCams;
    }

    getGroups = () => {
        if (this._storeGroups) {
            return this._storeGroups;
        }
        this._storeGroups = {}
        const groups = localStorage.getItem('groups');
        if (groups) {
            try {
                this._storeGroups = JSON.parse(groups);
            } catch (e) {
                console.error('Invalid groups JSON:', e);
            }
        }
        return this._storeGroups;
    }

    getUid = () => {
        if (this._uid) {
            return this._uid;
        }
        this._uid = localStorage.getItem('uid');
        if (!this._uid) {
            const now = new Date();
            this._uid = now.getMonth() + '' + now.getDate() + '-' + now.getHours() + '' + now.getMinutes()
                + '-' + Math.random().toString(36).slice(2, 8);
            localStorage.setItem('uid', this._uid);
        }
        return this._uid;
    }

    nextId = ids => {
        if (!ids.length) return 1;
        let id = Math.max(...ids);
        return id ? id + 1 : Date.now().toString().slice(2, -2);
    }

    back = () => {
        document.querySelector('header .back-btn').classList.add('blink');
        document.location.href = '/';
    }

    wakeLock = () => {
        if (!'wakeLock' in navigator || !navigator.wakeLock ||
            ('userAgentData' in navigator && !navigator.userAgentData.mobile)) {
            return;
        }
        navigator.wakeLock.request('screen').then(wls => {
            this._wakeLockSentinel = wls;
        });
    }

    wakeRelease = () => {
        if (this._wakeLockSentinel && !sessionStorage.getItem('bell') && !this.isPlaying) {
            this._wakeLockSentinel.release();
        }
    }
}
