(function() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('preview');
    const previewImg = document.getElementById('previewImg');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resetBtn = document.getElementById('resetBtn');
    const status = document.getElementById('status');
    const scanbar = document.getElementById('scanbar');
    const resultsPanel = document.getElementById('resultsPanel');
    const resultsBody = document.getElementById('resultsBody');
    const readoutLine = document.getElementById('readoutLine');
    const visionPanel = document.getElementById('visionPanel');
    const visionBtn = document.getElementById('visionBtn');
    const visionStatus = document.getElementById('visionStatus');
    const visionOutput = document.getElementById('visionOutput');
    const apiKeyInput = document.getElementById('apiKey');

    let currentFile = null;


    function openStreetMapCard(lat, lon, prob){
        const card = document.createElement('div')
        card.className = 'result-card';

        const probHtml = (prob !== null) ? `<span class="prob">prob ${(prob * 100).toFixed(1)}%</span>` :'';
        const mapSrc = `https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.01}%2C${lat-0.01}%2C${lon+0.01}%2C${lat+0.01}&marker=${lat}%2C${lon}`;

        card.innerHTML = `
            <iframe 
                src="${mapSrc}" 
                loading="lazy"
                frameborder="0"
                style="width:100%; height:200px; display:block; border:0;">
            </iframe>
        `;

        return card;
    }

    function setFile(file) {
        currentFile = file;
        const url = URL.createObjectURL(file);
        previewImg.src = url;
        preview.style.display = 'block';
        analyzeBtn.disabled = false;
        resetBtn.style.display = 'inline-block';
        resultsPanel.style.display = 'none';
        visionPanel.style.display = 'none';
        status.textContent = '';
        status.className = 'status';
        scanbar.classList.remove('locked');
    }

    function resetAll() {
        currentFile = null;
        fileInput.value = '';
        preview.style.display = 'none';
        analyzeBtn.disabled = true;
        resetBtn.style.display = 'none';
        resultsPanel.style.display = 'none';
        visionPanel.style.display = 'none';
        status.textContent = '';
        scanbar.classList.remove('locked');
        visionOutput.style.display = 'none';
        visionStatus.textContent = '';
    }

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', e => {
        e.preventDefault();
        dropzone.style.borderColor = '#557a5a';
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.style.borderColor = '#b8aa92';
    });
    dropzone.addEventListener('drop', e => {
        e.preventDefault();
        dropzone.style.borderColor = '#b8aa92';
        if (e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) setFile(fileInput.files[0]);
    });
    resetBtn.addEventListener('click', resetAll);

    analyzeBtn.addEventListener('click', async () => {
        if (!currentFile) return;
        analyzeBtn.disabled = true;
        status.className = 'status';
        status.textContent = 'Analyzing image...';
        resultsPanel.style.display = 'none';
        visionPanel.style.display = 'none';

        const formData = new FormData();
        formData.append('image', currentFile);

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            const text = await response.text();
            
            try {
                var data = JSON.parse(text);
            } catch (e) {
                console.error('Response text:', text);
                throw new Error('Server returned invalid JSON. Check server logs for errors.');
            }

            if (!response.ok) {
                throw new Error(data.error || 'Analysis failed');
            }

            scanbar.classList.add('locked');
            status.textContent = '';

            if (data.source === 'exif') {
                readoutLine.innerHTML = `<span>SOURCE</span><b>EXIF · exact coordinates</b>`;
                resultsBody.innerHTML = '';
                resultsBody.appendChild(buildResultCard(data.exif.lat, data.exif.lon, null));
                resultsPanel.style.display = 'block';
                visionPanel.style.display = 'none';
            } else if (data.source === 'geoclip') {
                readoutLine.innerHTML = `<span>SOURCE</span><b>GEOCLIP · top 5 predictions</b>`;
                resultsBody.innerHTML = '';
                data.geoclip.forEach(p => {
                    resultsBody.appendChild(buildResultCard(p.lat, p.lon, p.prob));
                });
                resultsPanel.style.display = 'block';
                visionPanel.style.display = 'block';
            } else {
                throw new Error('Unknown source in response');
            }

        } catch (error) {
            console.error('Error:', error);
            status.className = 'status err';
            status.textContent = 'Error: ' + error.message;
        } finally {
            analyzeBtn.disabled = false;
        }
    });

    function buildResultCard(lat, lon, prob) {
        const card = document.createElement('div');
        card.className = 'res-card';
        const probHtml = (prob !== null && prob !== undefined) ?
            `<span class="prob">prob ${(prob * 100).toFixed(1)}%</span>` :
            '';

        card.innerHTML = `
            <div class="row">
                <span class="coords">${lat.toFixed(5)}, ${lon.toFixed(5)}</span>
                ${probHtml}
            </div>
            <div class="links">
                <a href="#" class="sv-toggle">▶ Street View</a>
                <a href="https://www.google.com/maps?q=${lat},${lon}" target="_blank" rel="noopener">Google Maps ↗</a>
            </div>
            <div class="sv-frame"></div>
        `;

        const toggle = card.querySelector('.sv-toggle');
        const frameWrap = card.querySelector('.sv-frame');
        let loaded = false;
        toggle.addEventListener('click', e => {
            e.preventDefault();
            const open = frameWrap.style.display === 'block';
            if (!loaded) {
                const iframe = document.createElement('iframe');
                iframe.src = `https://maps.google.com/maps?layer=c&cbll=${lat},${lon}&output=svembed`;
                iframe.loading = 'lazy';
                frameWrap.appendChild(iframe);
                loaded = true;
            }
            frameWrap.style.display = open ? 'none' : 'block';
            toggle.textContent = open ? '▶ Street View' : '▼ hide';
        });

        card.appendChild(openStreetMapCard(lat, lon, prob));

        return card;
    }

    visionBtn.addEventListener('click', async () => {
        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) {
            visionStatus.className = 'status err';
            visionStatus.textContent = 'Please enter your Anthropic API key';
            return;
        }
        if (!currentFile) return;

        visionBtn.disabled = true;
        visionStatus.className = 'status';
        visionStatus.textContent = 'Claude is analyzing...';
        visionOutput.style.display = 'none';

        const formData = new FormData();
        formData.append('image', currentFile);
        formData.append('api_key', apiKey);

        try {
            const response = await fetch('/api/vision', {
                method: 'POST',
                body: formData
            });

            const text = await response.text();
            
            try {
                var data = JSON.parse(text);
            } catch (e) {
                console.error('Response text:', text);
                throw new Error('Server returned invalid JSON. Check server logs for errors.');
            }

            if (!response.ok) {
                throw new Error(data.error || 'Vision analysis failed');
            }

            visionStatus.textContent = '';
            visionOutput.textContent = data.text;
            visionOutput.style.display = 'block';

        } catch (error) {
            console.error('Vision error:', error);
            visionStatus.className = 'status err';
            visionStatus.textContent = 'Error: ' + error.message;
        } finally {
            visionBtn.disabled = false;
        }
    });

    resetAll();
})();