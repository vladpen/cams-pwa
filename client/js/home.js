(() => {
    const cfg = new Config();
    const cams = cfg.getCams();
    const groups = cfg.getGroups();
    const ids = Object.keys(cams);
    const navBox = document.querySelector('ul.nav');
    const navRowTemplate = navBox.querySelector('li');

    if (ids.length < 2) {
        document.querySelector('.group-edit-link').classList.add('hidden');
    }

    if (ids.length < 1) {
        document.querySelector('.export-link').classList.add('hidden');
    }

    const checkItem = (data, fields) => {
        for (const f of fields) if (!(f in data)) return false;
        return true;
    }

    const appendRow = (id, name, kind) => {
        const li = navRowTemplate.cloneNode(true);
        const a = li.querySelector('a');
        const b = li.querySelector('b');
        a.innerHTML = name + '<i></i>';
        a.href = `/?page=${kind}&id=${id}`;
        li.classList.add(kind);
        li.dataset.id = id;
        li.classList.remove('hidden');
        navBox.append(li);
        b.onclick = () => {
            b.classList.add('blink');
            document.location.href = `/?page=${kind}_edit&id=${id}`;
        }
    }

    let camsCount = 0;
    for (const id in Object.keys(cams), cams) {
        if (checkItem(cams[id], ['name', 'key'])) {
            appendRow(id, cams[id].name, 'cam');
            camsCount++;
        }
    }

    for (const id in groups) {
        if (checkItem(groups[id], ['name', 'cams'])) {
            appendRow(id, groups[id].name, 'group');
        }
    }

    if (!camsCount) {
        document.querySelector('main .nav').classList.add('hidden');
        document.querySelector('main .empty-home').classList.remove('hidden');
    }

    document.querySelector('main').onclick = () => {
        document.querySelector('#menu-toggle').checked = false;
    }

    document.querySelector('.export-link a').onclick = e => {
        document.querySelector('#menu-toggle').checked = false;
        const date = new Date()
        const fileName = `cams-pwa-${date.toISOString().split('T')[0]}.cfg`
        if (!confirm(i18n['Export settings to'] + '\n' + fileName + '?')) {
            e.preventDefault();
            return;
        }
        const content = localStorage.getItem('cams') + '\n' + localStorage.getItem('groups');
        const a = document.querySelector('.export-link a');
        const file = new Blob([content], {type: 'text/plain'});
        a.href = URL.createObjectURL(file);
        a.download = fileName;
    }

    const importCfg = e => {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.readAsText(file,'UTF-8');
        reader.onload = evt => {
            document.querySelector('#menu-toggle').checked = false;

            const content = evt.target.result;
            const cfg = content.split('\n', 2);
            const rawCams = cfg[0];
            const rawGroups = cfg[1];
            try {
                const cams = JSON.parse(rawCams);
                const groups = rawGroups ? JSON.parse(rawGroups) : { };
                let error = false;
                for (const id in cams) {
                    if (!checkItem(cams[id], ['name', 'key'])) {
                        throw new Error('invalid cams');
                    }
                }
                for (const id in groups) {
                    if (!checkItem(groups[id], ['name', 'cams'])) {
                        throw new Error('invalid groups');
                    }
                }
            } catch (e) {
                console.error('Invalid config:', e);
                alert(i18n['Invalid data']);
                return;
            }
            if (camsCount && !confirm(i18n['Replace'])) {
                return;
            }
            localStorage.setItem('cams', rawCams);
            localStorage.setItem('groups', rawGroups);

            location.reload();
        }
    }
    for (const inp of document.querySelectorAll('.import-link input')) {
        inp.onchange = importCfg;
    }
    sessionStorage.removeItem('group_id');
})();
