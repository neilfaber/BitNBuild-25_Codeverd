/* TaxWise Frontend JavaScript */

// API Configuration
const API_BASE_URL = '/tax-ai/api/';
const API_ENDPOINTS = {
    calculate: 'calculate/',
    classify: 'classify/',
    recommendations: 'recommendations/'
};

// Global State Management
const TaxWiseApp = {
    data: {
        userProfile: {},
        calculations: {},
        recommendations: []
    },
    
    // Initialize the application
    init() {
        this.setupEventListeners();
        this.loadStoredData();
        this.initializeCharts();
    },
    
    // Setup global event listeners
    setupEventListeners() {
        // Form validation - only intercept forms without data-no-intercept attribute
        document.querySelectorAll('form:not([data-no-intercept])').forEach(form => {
            form.addEventListener('submit', this.handleFormSubmission.bind(this));
        });
        
        // Real-time input validation
        document.querySelectorAll('input[type="number"]').forEach(input => {
            input.addEventListener('input', this.validateNumericInput);
            input.addEventListener('blur', this.formatCurrencyInput);
        });
        
        // Theme switcher (if needed in future)
        this.setupThemeSwitcher();
    },
    
    // Handle form submissions with validation
    handleFormSubmission(event) {
        event.preventDefault();
        const form = event.target;
        
        if (!this.validateForm(form)) {
            this.showError('Please correct the highlighted errors before submitting.');
            return;
        }
        
        this.processForm(form);
    },
    
    // Validate form inputs
    validateForm(form) {
        let isValid = true;
        const inputs = form.querySelectorAll('input[required], select[required]');
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.highlightError(input);
                isValid = false;
            } else {
                this.clearError(input);
            }
        });
        
        return isValid;
    },
    
    // Validate numeric inputs
    validateNumericInput(event) {
        const input = event.target;
        const value = parseFloat(input.value);
        const min = parseFloat(input.getAttribute('min')) || 0;
        const max = parseFloat(input.getAttribute('max')) || Number.MAX_VALUE;
        
        if (isNaN(value) || value < min || value > max) {
            TaxWiseApp.highlightError(input);
        } else {
            TaxWiseApp.clearError(input);
        }
    },
    
    // Format currency inputs
    formatCurrencyInput(event) {
        const input = event.target;
        const value = parseFloat(input.value);
        
        if (!isNaN(value)) {
            input.value = Math.round(value);
        }
    },
    
    // Highlight input errors
    highlightError(input) {
        input.classList.add('is-invalid');
        
        // Add error message if not exists
        if (!input.parentElement.querySelector('.invalid-feedback')) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = this.getErrorMessage(input);
            input.parentElement.appendChild(errorDiv);
        }
    },
    
    // Clear input errors
    clearError(input) {
        input.classList.remove('is-invalid');
        const errorDiv = input.parentElement.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    },
    
    // Get appropriate error message for input
    getErrorMessage(input) {
        const type = input.type;
        const name = input.name || input.id;
        
        if (type === 'number') {
            const min = input.getAttribute('min');
            const max = input.getAttribute('max');
            
            if (min && max) {
                return `Please enter a value between ${min} and ${max}`;
            } else if (min) {
                return `Please enter a value greater than ${min}`;
            } else if (max) {
                return `Please enter a value less than ${max}`;
            }
            return 'Please enter a valid number';
        }
        
        return 'This field is required';
    },
    
    // Process form data
    async processForm(form) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
        submitBtn.disabled = true;
        
        try {
            // Determine API endpoint based on form
            let endpoint = API_ENDPOINTS.calculate;
            if (form.id === 'profileForm') {
                endpoint = API_ENDPOINTS.recommendations;
            }
            
            const result = await this.callAPI(endpoint, data);
            this.handleAPIResponse(result, form);
            
        } catch (error) {
            this.showError('An error occurred while processing your request. Please try again.');
            console.error('Form processing error:', error);
        } finally {
            // Restore button state
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    },
    
    // API call wrapper
    async callAPI(endpoint, data, method = 'POST') {
        const url = API_BASE_URL + endpoint;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        // Add CSRF token if available (for non-exempt endpoints)
        const csrfToken = this.getCSRFToken();
        if (csrfToken) {
            options.headers['X-CSRFToken'] = csrfToken;
        }
        
        if (method !== 'GET' && data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`API call failed: ${response.status}`);
        }
        
        return await response.json();
    },
    
    // Get CSRF token
    getCSRFToken() {
        // Try meta tag first
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }
        
        // Fallback to cookies
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    },
    
    // Handle API responses
    handleAPIResponse(response, form) {
        if (response.status === 'success') {
            this.showSuccess('Data processed successfully!');
            
            // Store data
            if (form.id === 'taxCalculatorForm') {
                this.data.calculations = response.data;
                this.displayTaxResults(response.data);
            } else if (form.id === 'profileForm') {
                this.data.recommendations = response.data.recommendations || [];
                this.displayRecommendations(response.data);
            }
            
            // Save to localStorage
            this.saveData();
        } else {
            this.showError(response.message || 'An error occurred');
        }
    },
    
    // Display tax calculation results
    displayTaxResults(data) {
        // This would integrate with the calculator.html template
        // Implementation would depend on specific result structure
        console.log('Tax results:', data);
    },
    
    // Display recommendations
    displayRecommendations(data) {
        // This would integrate with the recommendations.html template
        console.log('Recommendations:', data);
    },
    
    // Local storage management
    saveData() {
        localStorage.setItem('taxwise_data', JSON.stringify(this.data));
    },
    
    loadStoredData() {
        const stored = localStorage.getItem('taxwise_data');
        if (stored) {
            try {
                this.data = { ...this.data, ...JSON.parse(stored) };
            } catch (error) {
                console.error('Error loading stored data:', error);
            }
        }
    },
    
    // Initialize charts (placeholder for Chart.js integration)
    initializeCharts() {
        // Chart initialization would go here
        // This is handled in individual template files for now
    },
    
    // Theme switcher setup
    setupThemeSwitcher() {
        const theme = localStorage.getItem('taxwise_theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    },
    
    // Notification system
    showSuccess(message) {
        this.showNotification(message, 'success');
    },
    
    showError(message) {
        this.showNotification(message, 'error');
    },
    
    showNotification(message, type = 'info') {
        // Remove existing notifications
        document.querySelectorAll('.notification').forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show notification`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    },
    
    // Utility functions
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        }).format(amount);
    },
    
    formatNumber(num) {
        return new Intl.NumberFormat('en-IN').format(num);
    },
    
    // Animation utilities
    animateValue(element, start, end, duration = 2000) {
        const range = end - start;
        const minTimer = 50;
        let stepTime = Math.abs(Math.floor(duration / range));
        
        stepTime = Math.max(stepTime, minTimer);
        
        const startTime = new Date().getTime();
        const endTime = startTime + duration;
        let timer;
        
        function run() {
            const now = new Date().getTime();
            const remaining = Math.max((endTime - now) / duration, 0);
            const value = Math.round(end - (remaining * range));
            
            element.textContent = TaxWiseApp.formatCurrency(value);
            
            if (value === end) {
                clearInterval(timer);
            }
        }
        
        timer = setInterval(run, stepTime);
        run();
    },
    
    // Scroll to element with smooth animation
    scrollToElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    },
    
    // Progressive enhancement for older browsers
    supportsES6() {
        try {
            new Function('(a = 0) => a');
            return true;
        } catch (err) {
            return false;
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (TaxWiseApp.supportsES6()) {
        TaxWiseApp.init();
    } else {
        console.warn('TaxWise requires a modern browser with ES6 support');
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TaxWiseApp;
}

// Global helper functions for templates
window.TaxWiseApp = TaxWiseApp;
window.formatCurrency = TaxWiseApp.formatCurrency.bind(TaxWiseApp);
window.formatNumber = TaxWiseApp.formatNumber.bind(TaxWiseApp);
window.showSuccess = TaxWiseApp.showSuccess.bind(TaxWiseApp);
window.showError = TaxWiseApp.showError.bind(TaxWiseApp);