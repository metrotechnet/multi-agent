// Backend configuration
// This file is auto-generated during Firebase deployment
// For local development, detect if we're on localhost:3000 and point to backend on 8080
if (window.location.hostname === 'localhost' && window.location.port === '3000') {
    window.BACKEND_URL = 'http://localhost:8080';
} else {
    // For production or same-origin requests
    window.BACKEND_URL = window.BACKEND_URL || '';
}
