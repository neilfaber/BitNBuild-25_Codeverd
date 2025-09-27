// Statement detection patterns
const STATEMENT_PATTERNS = {
    pdf: /statement|invoice|bill/i,
    links: /download|statement|pdf|csv/i
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    detectStatements();
    observePageChanges();
});

// Detect statements in the page
function detectStatements() {
    // Find PDF links
    const links = Array.from(document.getElementsByTagName('a'));
    
    links.forEach(link => {
        if (isStatementLink(link)) {
            addUploadButton(link);
        }
    });
}

// Check if a link is likely a statement
function isStatementLink(link) {
    const href = link.href.toLowerCase();
    const text = link.textContent.toLowerCase();
    
    return (STATEMENT_PATTERNS.pdf.test(text) || 
            href.endsWith('.pdf') ||
            href.endsWith('.csv')) &&
           STATEMENT_PATTERNS.links.test(text);
}

// Add upload button next to statement links
function addUploadButton(link) {
    const button = document.createElement('button');
    button.className = 'taxwise-upload-btn';
    button.textContent = 'Upload to TaxWise';
    
    button.addEventListener('click', async (e) => {
        e.preventDefault();
        await handleUpload(link.href);
    });
    
    link.parentNode.insertBefore(button, link.nextSibling);
}

// Handle file upload
async function handleUpload(url) {
    try {
        // Get the file
        const response = await fetch(url);
        const blob = await response.blob();
        
        // Create form data
        const formData = new FormData();
        formData.append('file', blob, 'statement.pdf');
        
        // Upload to TaxWise
        const uploadResponse = await fetch('http://localhost:8000/api/upload-statement/', {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });
        
        if (uploadResponse.ok) {
            // Update counts
            chrome.storage.local.get(['processedCount'], (result) => {
                const newCount = (result.processedCount || 0) + 1;
                chrome.storage.local.set({ processedCount: newCount });
            });
            
            showNotification('Success', 'Statement uploaded successfully!');
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        showNotification('Error', 'Failed to upload statement');
        console.error('Upload error:', error);
    }
}

// Show notification
function showNotification(title, message) {
    const notification = document.createElement('div');
    notification.className = 'taxwise-notification';
    notification.textContent = `${title}: ${message}`;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 3000);
}

// Observe page changes for dynamic content
function observePageChanges() {
    const observer = new MutationObserver(() => detectStatements());
    observer.observe(document.body, { 
        childList: true, 
        subtree: true 
    });
}