// Background script for TaxWise extension

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('TaxWise Extension installed');
    // Initialize extension state
    chrome.storage.local.set({
        autoUpload: true,
        processedCount: 0,
        categorizedCount: 0
    });
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'UPLOAD_SUCCESS') {
        // Update statistics
        chrome.storage.local.get(['processedCount', 'categorizedCount'], (result) => {
            chrome.storage.local.set({
                processedCount: (result.processedCount || 0) + 1,
                categorizedCount: message.categorized ? (result.categorizedCount || 0) + 1 : (result.categorizedCount || 0)
            });
        });
    }
    
    // Return true to indicate we'll respond asynchronously
    return true;
});

// Handle browser action click
chrome.action.onClicked.addListener((tab) => {
    // Open popup if not already open
    chrome.action.openPopup();
});

// Check TaxWise server status
async function checkServerStatus() {
    try {
        const response = await fetch('http://localhost:8000/api/status/');
        return response.ok;
    } catch (error) {
        console.error('Server check failed:', error);
        return false;
    }
}

// Update extension icon based on server status
async function updateExtensionStatus() {
    const isServerActive = await checkServerStatus();
    
    chrome.action.setIcon({
        path: isServerActive ? {
            16: "icons/icon16.svg",
            48: "icons/icon48.svg",
            128: "icons/icon128.svg"
        } : {
            16: "icons/icon16_disabled.svg",
            48: "icons/icon48_disabled.svg",
            128: "icons/icon128_disabled.svg"
        }
    });
}

// Check server status periodically
setInterval(updateExtensionStatus, 30000); // Every 30 seconds
updateExtensionStatus(); // Initial check