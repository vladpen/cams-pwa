class GroupEdit extends Config {
    constructor() {
        super();
        const urlParams = new URLSearchParams(window.location.search);
        this._id = urlParams.get('id');
        this._groups = this.getGroups();
        this._cams = this.getCams();
        this._selectedCams = this._id ? (this._groups[this._id].cams).split(',') : [];
        this._form = document.querySelector('.edit-form');
        this._camList = this._form.querySelector('.cam-list');
        this._camTemplate = this._camList.querySelector('li');
        this._select = this._form.querySelector('select');
        this._inputName = this._form.querySelector('input[name="name"]');
    }

    run = () => {
        document.querySelector('header .back-btn').onclick = this.back;
        const deleteLink = this._form.querySelector('.delete');

        if (this._id && this._id in this._groups) {
            this._inputName.value = this._groups[this._id].name;
        }
        if (!this._id) {
            deleteLink.classList.add('hidden');
        }
        for (const camId of this._selectedCams) {
            this._appendCam(camId);
        }
        for (const camId in this._cams) {
            let opt = document.createElement('option');
            opt.value = camId;
            opt.innerHTML = this._cams[camId].name;
            if (this._selectedCams.includes(camId)) {
                opt.hidden = true;
                opt.disabled = true;
            }
            this._select.append(opt);
        }
        this._select.onchange = this._addCam;

        this._form.onsubmit = e => {
            this._save(e);
        }
        deleteLink.onclick = this._delete;
    }

    _appendCam = id => {
        if (!(id in this._cams)) {
            return;
        }
        let camEl = this._camTemplate.cloneNode(true);
        camEl.querySelector('span').innerHTML = this._cams[id].name;
        camEl.classList.remove('hidden');
        this._camList.append(camEl);
        camEl.onclick = () => {
            this._removeCam(id, camEl);
        }
    }

    _addCam = () => {
        const id = this._select.value;
        this._appendCam(id);
        const opt = this._select.querySelector(`option[value="${id}"]`);
        opt.hidden = true;
        opt.disabled = true;
        this._select.value = '';

        if (this._select.querySelectorAll('option:not(:disabled)').length == 0) {
            this._select.disabled = true;
        }
        this._selectedCams.push(id);
    }

    _removeCam = (id, camEl) => {
        camEl.remove();
        const opt = this._select.querySelector(`option[value="${id}"]`);
        opt.hidden = false;
        opt.disabled = false;
        this._select.disabled = false;

        this._selectedCams = this._selectedCams.filter(item => item != id);
    }

    _save = e => {
        e.preventDefault();
        const name = this._inputName.value.trim();
        const formError = this._form.querySelector('div.error');

        if (this._selectedCams.length < 2) {
            formError.innerHTML = i18n['At least 2 cameras'];
            return;
        }
        if (!this._id || (this._id && name != this._groups[this._id].name)) {
            for (const id in this._groups) {
                if (name != this._groups[id].name) {
                    continue;
                }
                formError.innerHTML = i18n['Group already exists'];
                this._inputName.classList.add('error');
                return;
            }
        }
        if (!this._id) {
            this._id = this.nextId(Object.keys(this._groups));
        }
        this._groups[this._id] = {'name': name, 'cams': this._selectedCams.join(',')};
        localStorage.setItem('groups', JSON.stringify(this._groups));

        this.back();
    }

    _delete = () => {
        if (this._id in this._groups && !confirm(i18n['Delete'] + ' "' + this._groups[this._id].name + '"?')) {
            return;
        }
        delete this._groups[this._id];
        localStorage.setItem('groups', JSON.stringify(this._groups));
        document.location.href = '/';
    }
}
