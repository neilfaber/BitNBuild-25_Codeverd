// Popup script for TaxWise extension

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize UI elements
    const connectionStatus = document.getElementById('connectionStatus');
    const processedCount = document.getElementById('processedCount');
    const categorizedCount = document.getElementById('categorizedCount');
    const loginButton = document.getElementById('loginButton');
    const autoUploadCheckbox = document.getElementById('autoUpload');

    // Load saved settings
    chrome.storage.local.get(['autoUpload', 'processedCount', 'categorizedCount'], (result) => {
        autoUploadCheckbox.checked = result.autoUpload !== false;
        processedCount.textContent = result.processedCount || 0;
        categorizedCount.textContent = result.categorizedCount || 0;
    });

    // Check server connection
    try {
        const response = await fetch('http://localhost:8000/api/status/');
        if (response.ok) {
            connectionStatus.textContent = 'Connected to TaxWise';
            connectionStatus.className = 'status connected';
        } else {
            throw new Error('Server returned error');
        }
    } catch (error) {
        connectionStatus.textContent = 'Not connected to TaxWise';
        connectionStatus.className = 'status disconnected';
    }

    // Handle auto-upload setting change
    autoUploadCheckbox.addEventListener('change', (event) => {
        chrome.storage.local.set({ autoUpload: event.target.checked });
    });

    // Handle login button click
    loginButton.addEventListener('click', () => {
        chrome.tabs.create({ url: 'http://localhost:8000/auth/login' });
    });
});