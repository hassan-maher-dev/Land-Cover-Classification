// Form and API interaction script

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const mtlInput = document.getElementById('mtlInput');
    const mtlFileName = document.getElementById('mtlFileName');
    const submitBtn = document.getElementById('submitBtn');

    // MTL file name display
    mtlInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            mtlFileName.textContent = `✓ ${e.target.files[0].name}`;
            mtlFileName.classList.add('show');
        }
    });

    // Form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get all band files
        const bandInputs = document.querySelectorAll('input[name="bands"]');
        const bandFiles = [];
        let allFilesSelected = true;

        for (let input of bandInputs) {
            if (input.files.length === 0) {
                allFilesSelected = false;
                break;
            }
            bandFiles.push(input.files[0]);
        }

        if (!allFilesSelected) {
            showError('Please select all 7 band files.');
            return;
        }

        if (!mtlInput.files[0]) {
            showError('Please select the MTL metadata file.');
            return;
        }

        const rowStart = document.querySelector('input[name="row_start"]').value;
        const rowEnd = document.querySelector('input[name="row_end"]').value;
        const colStart = document.querySelector('input[name="col_start"]').value;
        const colEnd = document.querySelector('input[name="col_end"]').value;

        if (!rowStart || !rowEnd || !colStart || !colEnd) {
            showError('Crop window values are required. Please enter all four values (row/column start and end).');
            return;
        }

        const rowStartNum = parseInt(rowStart, 10);
        const rowEndNum = parseInt(rowEnd, 10);
        const colStartNum = parseInt(colStart, 10);
        const colEndNum = parseInt(colEnd, 10);

        if ((rowEndNum - rowStartNum) !== 2000 || (colEndNum - colStartNum) !== 2000) {
            showError('Crop window must be exactly 2000×2000 pixels. You selected ' + 
                      (rowEndNum - rowStartNum) + '×' + (colEndNum - colStartNum) + '. ' +
                      'Try rows 1000-3000 and columns 1000-3000.');
            return;
        }

        // Prepare FormData
        const formData = new FormData();

        // Add band files
        bandFiles.forEach((file, index) => {
            formData.append('bands', file);
        });

        formData.append('row_start', rowStart);
        formData.append('row_end', rowEnd);
        formData.append('col_start', colStart);
        formData.append('col_end', colEnd);

        // Add MTL file
        formData.append('mtl', mtlInput.files[0]);

        // Hide upload section, show progress
        document.querySelector('.upload-section').style.display = 'none';
        showProgress();

        // Send request
        try {
            submitBtn.disabled = true;

            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Unknown error occurred');
            }

            // Show results
            displayResults(data);

            if (data.warning) {
                showWarning(data.warning);
            }

        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
        } finally {
            submitBtn.disabled = false;
        }
    });

    /**
     * Show progress section
     */
    function showProgress() {
        const progressSection = document.getElementById('progressSection');
        progressSection.style.display = 'block';

        // Animate progress bar
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress > 90) progress = 90;
            updateProgress(progress);
        }, 800);

        // Store interval ID in window for later cleanup
        window.progressInterval = interval;
    }

    /**
     * Update progress bar
     */
    function updateProgress(percentage) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');

        percentage = Math.min(percentage, 100);
        progressBar.style.width = percentage + '%';

        // Update status text based on progress
        let statusMessages = [
            'Initializing...',
            'Parsing MTL metadata...',
            'Loading Landsat bands...',
            'Applying radiometric calibration...',
            'Computing spectral indices (NDVI, NDWI, NDBI)...',
            'Stacking features (B1-B7 + 3 indices)...',
            'Loading trained model...',
            'Running classification...',
            'Computing area statistics...',
            'Generating visualization...',
            'Finalizing results...'
        ];

        const messageIndex = Math.floor((percentage / 100) * (statusMessages.length - 1));
        progressText.textContent = statusMessages[messageIndex];
    }

    /**
     * Display results
     */
    function displayResults(data) {
        // Clear progress interval
        clearInterval(window.progressInterval);
        updateProgress(100);

        // Hide progress section after delay
        setTimeout(() => {
            document.getElementById('progressSection').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'block';

            // Display classification map
            const classificationMap = document.getElementById('classificationMap');
            classificationMap.src = data.map_image;

            // Display statistics table
            const statsBody = document.getElementById('statsBody');
            statsBody.innerHTML = '';

            let totalPixels = 0;
            const statsArray = [];

            // Collect stats
            Object.entries(data.statistics).forEach(([className, stats]) => {
                totalPixels += stats.pixel_count;
                statsArray.push({
                    name: className,
                    pixels: stats.pixel_count,
                    area: stats.area_km2
                });
            });

            // Add rows to table
            statsArray.forEach(stat => {
                const percentage = ((stat.pixels / totalPixels) * 100).toFixed(2);
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${stat.name}</strong></td>
                    <td>${stat.pixels.toLocaleString()}</td>
                    <td>${stat.area.toLocaleString()}</td>
                    <td>${percentage}%</td>
                `;
                statsBody.appendChild(row);
            });

            // Add total row
            const totalRow = document.createElement('tr');
            totalRow.style.fontWeight = 'bold';
            totalRow.style.background = '#f0f7ff';
            totalRow.innerHTML = `
                <td>TOTAL</td>
                <td>${totalPixels.toLocaleString()}</td>
                <td>${(totalPixels * 900 / 1e6).toFixed(2)}</td>
                <td>100%</td>
            `;
            statsBody.appendChild(totalRow);

            // Set download link
            const downloadCSV = document.getElementById('downloadCSV');
            downloadCSV.href = data.csv_download;

            // Scroll to results
            document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });

        }, 1000);
    }

    /**
     * Show error message
     */
    function showError(message) {
        document.getElementById('progressSection').style.display = 'none';
        document.querySelector('.upload-section').style.display = 'block';
        document.getElementById('errorSection').style.display = 'block';
        document.getElementById('errorMessage').textContent = message;

        document.getElementById('errorSection').scrollIntoView({ behavior: 'smooth' });
    }
});
