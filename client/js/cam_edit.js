class CamEdit extends Config {
    constructor() {
        super();
        const urlParams = new URLSearchParams(window.location.search);
        this._id = urlParams.get('id');

        this._cams = this.getCams();
        this._form = document.querySelector('.edit-form');
        this._inputName = this._form.querySelector('input[name="name"]');
        this._inputKey = this._form.querySelector('input[name="key"]');
    }

    run = () => {
        document.querySelector('header .back-btn').onclick = this.back;
        const deleteLink = this._form.querySelector('.delete');

        if (this._id && this._id in this._cams) {
            this._inputName.value = this._cams[this._id].name;
            this._inputKey.value = this._cams[this._id].key;
        }
        if (!this._id) {
            deleteLink.classList.add('hidden');
        }
        this._form.onsubmit = e => {
            this._save(e);
        }
        deleteLink.onclick = this._delete;
    }

    _save = e => {
        e.preventDefault();
        const name = this._inputName.value.trim();
        const key = this._inputKey.value.trim();

        this._inputName.classList.remove('error');
        this._inputKey.classList.remove('error');

        let error = false;
        if (!this._id || (this._id && name != this._cams[this._id].name)) {  // new name
            for (const id in this._cams) {
                if (name != this._cams[id].name) {
                    continue;
                }
                this._inputName.classList.add('error');
                error = true;
            }
        }
        if (!this._id || (this._id && key != this._cams[this._id].key)) {  // new key
            for (const id in this._cams) {
                if (key != this._cams[id].key) {
                    continue;
                }
                this._inputKey.classList.add('error');
                error = true;
            }
        }
        if (error) {
            this._form.querySelector('form div.error').innerHTML = i18n['Already exists'];
            return;
        }
        if (!this._id) {
            this._id = this.nextId(Object.keys(this._cams));
        }
        this._cams[this._id] = {
            'name': name,
            'key': key
        }
        localStorage.setItem('cams', JSON.stringify(this._cams));

        this.back();
    }

    _delete = () => {
        if (!confirm(i18n['Delete'] + ' "' + this._cams[this._id].name + '"?')) {
            return;
        }
        delete this._cams[this._id];
        localStorage.setItem('cams', JSON.stringify(this._cams));

        let groups = this.getGroups();

        for (const id in groups) {
            let cams = groups[id].cams.split(',');
            if (!cams.includes(this._id)) {
                continue;
            }
            cams = cams.filter(item => item != this._id);
            groups[id].cams = cams.join(',');
            localStorage.setItem('groups', JSON.stringify(groups));
        }
        document.location.href = '/';
    }
}
