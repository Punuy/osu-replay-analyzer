document.addEventListener('DOMContentLoaded', () => {
    const replayDropZone = document.getElementById('replayDropZone');
    const beatmapDropZone = document.getElementById('beatmapDropZone');
    const replayFileInput = document.getElementById('replayFile');
    const beatmapFileInput = document.getElementById('beatmapFile');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const results = document.getElementById('results');
    const analyzeButton = document.getElementById('analyzeButton');

    function setupDropZone(zone, input) {
        zone.addEventListener('click', () => input.click());
        
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        ['dragleave', 'dragend'].forEach(type => {
            zone.addEventListener(type, () => zone.classList.remove('drag-over'));
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) {
                input.files = e.dataTransfer.files;
                handleFileUpload(input);
            }
        });

        input.addEventListener('change', () => {
            if (input.files[0]) {
                handleFileUpload(input);
            }
        });
    }

    function handleFileUpload(input) {
        const zone = input === replayFileInput ? replayDropZone : beatmapDropZone;
        if (input.files[0]) {
            zone.classList.add('has-file');
            checkFilesAndEnableButton();
        } else {
            zone.classList.remove('has-file');
        }
    }

    function checkFilesAndEnableButton() {
        if (replayFileInput.files[0] && beatmapFileInput.files[0]) {
            analyzeButton.disabled = false;
        } else {
            analyzeButton.disabled = true;
        }
    }

    setupDropZone(replayDropZone, replayFileInput);
    setupDropZone(beatmapDropZone, beatmapFileInput);

    analyzeButton.addEventListener('click', async () => {
        if (!replayFileInput.files[0] || !beatmapFileInput.files[0]) {
            alert('Please upload both replay and beatmap files.');
            return;
        }

        loadingSpinner.classList.remove('hidden');
        results.classList.add('hidden');

        const formData = new FormData();
        formData.append('replay_file', replayFileInput.files[0]);
        formData.append('beatmap_file', beatmapFileInput.files[0]);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.error) {
                alert(data.error);
                return;
            }

            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while analyzing the replay');
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    });

    function displayResults(data) {
        document.getElementById('totalPresses').textContent = data.total_presses;
        document.getElementById('avgPressTime').textContent = `${data.avg_press_time.toFixed(2)}ms`;
        document.getElementById('minPressTime').textContent = `${data.min_press_time.toFixed(2)}ms`;
        document.getElementById('maxPressTime').textContent = `${data.max_press_time.toFixed(2)}ms`;
        
        const graphImg = document.getElementById('pressGraph');
        graphImg.src = `data:image/png;base64,${data.plot}`;
        
        results.classList.remove('hidden');
    }
});