// ===================================
// ENABLE/DISABLE INPUT-AREA BASED ON URL ARGUMENT
// ===================================

function setInputAreaEnabled(enabled) {
    const inputArea = document.querySelector('.input-area');
    if (!inputArea) return;
    const textarea = inputArea.querySelector('textarea');
    const sendBtn = inputArea.querySelector('#send-button');
    const voiceBtn = inputArea.querySelector('#voice-button');
    if (enabled) {
        inputArea.classList.remove('disabled');
        if (textarea) textarea.disabled = false;
        if (sendBtn) sendBtn.disabled = false;
        if (voiceBtn) voiceBtn.disabled = false;
    } else {
        inputArea.classList.add('disabled');
        if (textarea) textarea.disabled = true;
        if (sendBtn) sendBtn.disabled = true;
        if (voiceBtn) voiceBtn.disabled = true;
    }
}

function checkDemo4836Argument() {
    // const urlParams = new URLSearchParams(window.location.search);
    // const demoArg = urlParams.get('code');
    // setInputAreaEnabled(demoArg === 'demo4836');
    setInputAreaEnabled(true); // Always enable input area
}

document.addEventListener('DOMContentLoaded', function() {
    checkDemo4836Argument();
});
// ===================================
// INTERNATIONALIZATION SYSTEM
// ===================================

let translations = {};
let currentLanguage = 'fr';

/**
 * Get URL parameter by name
 */
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

/**
 * Load translations from JSON file
 */
async function loadTranslations() {
    try {
        const response = await fetch('/api/get_config');
        translations = await response.json();
        
        // Language detection priority: URL parameter > browser language > stored preference
        const urlLang = getUrlParameter('lang');
        const browserLang = navigator.language || navigator.userLanguage;
        const langCode = browserLang.startsWith('en') ? 'en' : 'fr';
        const storedLang = localStorage.getItem('preferredLanguage');
        
        // Validate URL language parameter
        if (urlLang && (urlLang === 'en' || urlLang === 'fr')) {
            currentLanguage = urlLang;
            // Update stored preference when URL parameter is used
            localStorage.setItem('preferredLanguage', urlLang);
        } else {
            // Favor browser language over stored preference when no URL argument
            currentLanguage = langCode || storedLang;
            // Ensure URL parameter is set even when using browser/stored preference
            const url = new URL(window.location);
            url.searchParams.set('lang', currentLanguage);
            window.history.replaceState({}, '', url);
        }
        
        // Apply translations
        applyTranslations(currentLanguage);

    } catch (error) {
        console.error('Failed to load translations:', error);
        currentLanguage = 'fr';
    }

}

/**
 * Apply translations to all elements with data-i18n attributes
 */
function applyTranslations(lang) {
    const langData = translations[lang] || translations['fr'];
    
    // Update text content
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        const translation = getNestedValue(langData, key);
        if (translation) {
            element.textContent = translation;
        }
    });
    
    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        const translation = getNestedValue(langData, key);
        if (translation) {
            element.placeholder = translation;
        }
    });
    

    
    // Update title attributes
    document.querySelectorAll('[data-i18n-title]').forEach(element => {
        const key = element.getAttribute('data-i18n-title');
        const translation = getNestedValue(langData, key);
        if (translation) {
            element.title = translation;
        }
    });
    
    // Update alt attributes
    document.querySelectorAll('[data-i18n-alt]').forEach(element => {
        const key = element.getAttribute('data-i18n-alt');
        const translation = getNestedValue(langData, key);
        if (translation) {
            element.alt = translation;
        }
    });
    
    // Update src attributes
    document.querySelectorAll('[data-i18n-src]').forEach(element => {
        const key = element.getAttribute('data-i18n-src');
        const translation = getNestedValue(langData, key);
        if (translation) {
            element.src = translation;
        }
    });
    
    // Update document title
    const titleElement = document.querySelector('title[data-i18n]');
    if (titleElement) {
        const key = titleElement.getAttribute('data-i18n');
        const translation = getNestedValue(langData, key);
        if (translation) {
            document.title = translation;
        }
    }
}

/**
 * Get nested value from object using dot notation
 */
function getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : null;
    }, obj);
}

/**
 * Switch language
 */
function switchLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('preferredLanguage', lang);
    // Update URL parameter
    const url = new URL(window.location);
    url.searchParams.set('lang', lang);
    window.history.replaceState({}, '', url);
    applyTranslations(lang);
    updateFooterFromConfig();
}

/**
 * Get translation for a key
 */
function t(key) {
    const langData = translations[currentLanguage] || translations['fr'];
    return getNestedValue(langData, key) || key;
}

/**
 * Get current language
 */
function getCurrentLanguage() {
    return currentLanguage;
}

// ===================================
// DOM ELEMENTS & GLOBAL STATE
// ===================================

// Chat interface elements
const chatContainer = document.getElementById('chat-container');
const inputBox = document.getElementById('input-box');
const sendButton = document.getElementById('send-button');
const voiceButton = document.getElementById('voice-button');
const emptyState = document.getElementById('empty-state');

// Sidebar navigation elements
const menuToggle = document.getElementById('menu-toggle');
const sidebar = document.getElementById('sidebar');
const closeSidebar = document.getElementById('close-sidebar');
const overlay = document.getElementById('overlay');

// Cookie consent elements
const cookieBanner = document.getElementById('cookie-banner');
const cookieAccept = document.getElementById('cookie-accept');
const cookieDecline = document.getElementById('cookie-decline');

// Global state variables
let userMessageDiv = document.createElement('div'); // Reference to current user message
let isLoading = false; // Flag to prevent multiple simultaneous requests
let sessionId = null; // Session ID for conversation context

// Voice recording state
let recognition = null;
let isRecording = false;

// Whisper recording state (for STT)
let useWhisper = true; // Use Whisper API instead of Web Speech API
let mediaRecorder = null;
let audioChunks = [];
let whisperStream = null;
let audioContext = null;
let analyser = null;
let silenceTimer = null;
let maxDurationTimer = null;
let warningTimer = null;
let recordingAnimationInterval = null;

// TTS state
let ttsAudio = null;
let activeTtsButton = null; // Track which button is currently playing

// Keyboard state
let isKeyboardVisible = false;
let previousViewportHeight = window.innerHeight;

// ===================================
// MOBILE KEYBOARD DETECTION
// ===================================

/**
 * Initialize mobile keyboard detection
 * Detects when virtual keyboard appears or disappears on mobile devices
 */
function initKeyboardDetection() {
    // Method 1: Visual Viewport API (modern browsers - most reliable)
    if (window.visualViewport) {
        let lastHeight = window.visualViewport.height;
        
        window.visualViewport.addEventListener('resize', () => {
            const currentHeight = window.visualViewport.height;
            const heightDiff = lastHeight - currentHeight;
            
            // Keyboard appears when viewport height decreases significantly
            if (heightDiff > 150) {
                if (!isKeyboardVisible) {
                    isKeyboardVisible = true;
                    onKeyboardShow();
                }
            }
            // Keyboard disappears when viewport height increases significantly
            else if (heightDiff < -150) {
                if (isKeyboardVisible) {
                    isKeyboardVisible = false;
                    onKeyboardHide();
                }
            }
            
            lastHeight = currentHeight;
        });
    }
    
    // Method 2: Window resize fallback (older browsers)
    window.addEventListener('resize', () => {
        const currentHeight = window.innerHeight;
        const heightDiff = previousViewportHeight - currentHeight;
        
        // Significant height decrease (keyboard likely appeared)
        if (heightDiff > 150) {
            if (!isKeyboardVisible) {
                isKeyboardVisible = true;
                onKeyboardShow();
            }
        }
        // Significant height increase (keyboard likely disappeared)
        else if (heightDiff < -150) {
            if (isKeyboardVisible) {
                isKeyboardVisible = false;
                onKeyboardHide();
            }
        }
        
        previousViewportHeight = currentHeight;
    });
    
    // Method 3: Focus/blur detection (additional indicator)
    document.addEventListener('focusin', (e) => {
        // Only track for input elements on mobile
        if (isMobileDevice() && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
            setTimeout(() => {
                const currentHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
                const heightDiff = previousViewportHeight - currentHeight;
                
                if (heightDiff > 100 && !isKeyboardVisible) {
                    isKeyboardVisible = true;
                    onKeyboardShow();
                }
            }, 300);
        }
    });
    
    document.addEventListener('focusout', (e) => {
        // Only track for input elements on mobile
        if (isMobileDevice() && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
            setTimeout(() => {
                const currentHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
                const heightDiff = previousViewportHeight - currentHeight;
                
                if (Math.abs(heightDiff) < 100 && isKeyboardVisible) {
                    isKeyboardVisible = false;
                    onKeyboardHide();
                }
            }, 300);
        }
    });
}

/**
 * Callback when keyboard appears
 */
function onKeyboardShow() {
    console.log('Mobile keyboard shown');
    document.body.classList.add('keyboard-visible');
    
    // Scroll to show bottom of last message
    if (chatContainer && isMobileDevice()) {
        setTimeout(() => {
            // Scroll page to top
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
            window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
            
            // Scroll chat container to show latest messages
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }
}

/**
 * Callback when keyboard disappears
 */
function onKeyboardHide() {
    console.log('Mobile keyboard hidden');
    document.body.classList.remove('keyboard-visible');
    
    // Scroll to show bottom of last message
    if (isMobileDevice() && chatContainer) {
        setTimeout(() => {
            // Scroll page to top
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
            window.scrollTo({ top: 0, left: 0, behavior: 'smooth' });
            
            // Scroll chat container to show latest messages
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
    }
}

// ===================================
// MOBILE INPUT HANDLING
// ===================================

/**
 * Handle input box focus on mobile devices
 * Ensures the input remains visible above the virtual keyboard
 */
inputBox.addEventListener('focus', function() {
    setTimeout(() => {
        try {
            // Primary approach: Use scrollIntoView for input visibility
            this.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
            });
            
            // Fallback approach: Manual viewport adjustment for mobile keyboards
            const rect = this.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const estimatedKeyboardHeight = viewportHeight * 0.4; // Approximate keyboard size
            
            // Check if input will be hidden by keyboard
            if (rect.bottom > viewportHeight - estimatedKeyboardHeight) {
                const scrollAmount = rect.bottom - (viewportHeight - estimatedKeyboardHeight) + 20;
                window.scrollBy(0, scrollAmount);
            }
        } catch (error) {
            console.log('Input focus scroll failed:', error);
        }
    }, 300); // Delay to allow keyboard animation
});


// ===================================
// SCROLL INDICATOR
// ===================================

/**
 * Create and manage scroll indicator for chat container
 * Shows when user needs to scroll down to see new messages
 */
const scrollIndicator = document.createElement('div');
scrollIndicator.className = 'scroll-indicator';
scrollIndicator.style.opacity = '0.5';
scrollIndicator.innerHTML = `
    <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
    </svg>
`;

// Attach scroll indicator to main content area
const mainContainer = document.querySelector('.content');
if (mainContainer) {
    mainContainer.appendChild(scrollIndicator);
}

// Handle scroll indicator click - scroll to bottom of chat
scrollIndicator.addEventListener('click', () => {
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
});

/**
 * Update scroll indicator visibility based on chat scroll position
 * Hides indicator when user is near the bottom of the chat
 */
function updateScrollIndicator() {
    const threshold = 100; // Pixels from bottom to consider "near bottom"
    const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < threshold;
    
    if (isNearBottom) {
        scrollIndicator.classList.remove('visible');
    } else {
        scrollIndicator.classList.add('visible');
    }
}

// Set up scroll indicator event listeners
chatContainer.addEventListener('scroll', updateScrollIndicator);
// Initialize indicator state on page load
updateScrollIndicator();

// ===================================
// COOKIE CONSENT MANAGEMENT
// ===================================

/**
 * Check if user has previously given cookie consent
 * Shows banner with delay if no consent found
 */
function checkCookieConsent() {
    const consent = localStorage.getItem('cookieConsent');
    if (!consent) {
        // Show cookie banner after 1 second delay for better UX
        setTimeout(() => {
            cookieBanner.classList.add('show');
        }, 1000);
    }
}

// Handle cookie acceptance
cookieAccept.addEventListener('click', () => {
    localStorage.setItem('cookieConsent', 'accepted');
    cookieBanner.classList.remove('show');
});

// Handle cookie decline
cookieDecline.addEventListener('click', () => {
    localStorage.setItem('cookieConsent', 'declined');
    cookieBanner.classList.remove('show');
});

// Initialize cookie consent check on page load
checkCookieConsent();



// ===================================
// SIDEBAR NAVIGATION
// ===================================

/**
 * Open sidebar menu and show overlay
 */
menuToggle.addEventListener('click', () => {
    sidebar.classList.add('open');
    overlay.classList.add('active');
});

/**
 * Close sidebar menu using close button
 */
closeSidebar.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
});

/**
 * Close sidebar menu by clicking on overlay
 */
overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
});


// ===================================
// LEGAL NOTICE & PRIVACY POPUP
// ===================================

/**
 * Handle legal notice link click
 * Shows legal disclaimer popup and closes sidebar
 */
document.getElementById('legal-link').addEventListener('click', (e) => {
    e.preventDefault();
    showLegalNotice();
    // Close sidebar after opening legal notice
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
});

/**
 * Handle privacy policy link click
 * Shows privacy policy popup and closes sidebar
 */
document.getElementById('privacy-link').addEventListener('click', (e) => {
    e.preventDefault();
    showPrivacyPolicy();
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
});

/**
 * Handle about link click
 * Shows about popup and closes sidebar
 */
document.getElementById('about-link').addEventListener('click', (e) => {
    e.preventDefault();
    showAbout();
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
});


/**
 * Create and display legal notice popup with disclaimer text
 */
function showLegalNotice() {
    const langData = translations[currentLanguage] || translations['fr'];
    const legalContent = langData.legal;
    let html = `<h2 style='margin-top:0;text-align:center;'>${legalContent.title}</h2>`;
    html += legalContent.content.map(line => {
            return `<p>${line}</p>`;
    }).join('');

    Swal.fire({
        title: '',
        html: `<div style="text-align:left;">${html}</div>`,
        confirmButtonText: t('sidebar.closeButton') || 'Fermer',
        customClass: {
            popup: 'legal-popup-swal',
            title: 'legal-popup-title',
            content: 'legal-popup-content'
        },
        width: 700
    });
}

/**
 * Create and display privacy policy popup
 */
function showPrivacyPolicy() {
    const langData = translations[currentLanguage] || translations['fr'];
    const privacy = langData.privacy;
    let html = `<h2 style='margin-top:0;text-align:center;'>${privacy.title}</h2>`;
    if (privacy.lastUpdate) {
        html += `<p><em>${privacy.lastUpdate}</em></p>`;
    }
    html += privacy.content.map(line => {
         if (/^\d+\./.test(line)) {
            return `<h3>${line}</h3>`;
        } else if (line.trim() === '') {
            return '';
        } else {
            return `<p>${line}</p>`;
        }
    }).join('');
    // Regrouper les <li> dans des <ul> selon les sections
    html = html.replace(/(<h3>[^<]+<\/h3>)(<li>.*?<\/li>)+/gs, function(match) {
        const h3 = match.match(/<h3>[^<]+<\/h3>/)[0];
        const lis = match.match(/<li>.*?<\/li>/gs).join('');
        return h3 + '<ul >' + lis + '</ul>';
    });
    Swal.fire({
        title: '',
        html: `<div style="text-align:left;">${html}</div>`,
        confirmButtonText: t('sidebar.closeButton') || 'Fermer',
        customClass: {
            popup: 'legal-popup-swal',
            title: 'legal-popup-title',
            content: 'legal-popup-content'
        },
        width: 700
    });
}

function showAbout() {

        const langData = translations[currentLanguage] || translations['fr'];
        const about = langData.about || {};
        let html = `<h2 style='margin-top:0;text-align:center;'>${about.title}</h2>`;

        // Si about.content est un tableau, afficher chaque ligne comme une puce
        if (Array.isArray(about.content)) {
            html += '<ul style="text-align:left;">';
            about.content.forEach(line => {
                if (line.trim() !== '') {
                    html += `<li style="margin-bottom:8px;">${line}</li>`;
                }
            });
            html += '</ul>';
        } else if (typeof about.content === 'string') {
            // Si c'est une string, afficher tel quel
            html += `<div style="text-align:left;">${about.content}</div>`;
        }

        Swal.fire({
            title:  '',
            html: `<div style="text-align:left;">${html}</div>`,
            icon: 'info',
            confirmButtonText: about.closeButton || 'Fermer',
            customClass: {popup: 'swal2-ben-about'}
        });
    }

// ===================================
// INPUT HANDLING & UI INTERACTIONS
// ===================================

/**
 * Auto-resize textarea based on content
 * Limits maximum height to prevent UI issues
 */
inputBox.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
});

/**
 * Handle keyboard input for sending messages
 * Enter = send message, Shift+Enter = new line
 */
inputBox.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();

        sendMessage();

        // Dismiss mobile keyboard and trigger scroll restoration
        this.blur();
    }
});

/**
 * Remove previous bottom spacer if it exists
 */
function removePreviousSpacer() {
    const previousSpacer = document.getElementById('chat-bottom-spacer');
    if (previousSpacer && previousSpacer.parentNode) {
        previousSpacer.remove();
    }
}

/**
 * Create and add bottom spacer to chat container
 * @param {HTMLElement} userMsgDiv - The user message element
 * @param {HTMLElement} assistantMsgDiv - The assistant message element
 */
function createBottomSpacer(userMsgDiv, assistantMsgDiv,offset = 10) {
    const bottomSpacer = document.createElement('div');
    bottomSpacer.id = 'chat-bottom-spacer';

    bottomSpacer.style.height =  offset + 'px';
    bottomSpacer.style.flexShrink = '0';
    //set border for debugging
    // bottomSpacer.style.border = '1px solid red';
    return bottomSpacer;
}


/**
 * Update the bottom spacer height based on current message sizes
 * and scroll to keep the bottom of the assistant message visible
 * @param {HTMLElement} assistantMsgDiv - The assistant message element
 * @param {number} offset - Optional offset for scrolling
 */
function scrollToMessageBottom(assistantMsgDiv,offset = 0) {
    // Update spacer to shrink as message grows
    const spacer = document.getElementById('chat-bottom-spacer');
    // Scroll so the bottom of the assistant message is visible
    // console.log('Assistant message offsetTop:', assistantMsgDiv.offsetTop);
    // console.log('Assistant message offsetHeight:', assistantMsgDiv.offsetHeight);
    // console.log('Chat container clientHeight:', chatContainer.clientHeight);
    const targetTop = assistantMsgDiv.offsetTop + assistantMsgDiv.offsetHeight - chatContainer.clientHeight + offset;
    if (targetTop > 0) {
        chatContainer.scrollTop = targetTop;
    }
}
/**
 * Handle send button click
 */
sendButton.addEventListener('click', () => {


    // Check if keyboard is likely visible (input is focused)
    const isKeyboardVisible = document.activeElement === inputBox;

    sendMessage();


    // Only blur if keyboard is visible
    if (isKeyboardVisible) {
        inputBox.blur();
    }
});


/**
 * Detect if the device is mobile
 * @returns {boolean} True if mobile device
 */
function isMobileDevice() {
    // Check screen width (mobile typically < 768px)
    if (window.innerWidth <= 768) return true;
    
    // Check for touch capability
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0) {
        // Further verify with screen size for tablets
        if (window.innerWidth <= 1024) return true;
    }
    
    return false;
}

/**
 * Focus input box only on desktop browsers
 */
function handleFocus() {
    if (inputBox && !isMobileDevice()) {
        inputBox.focus();
    }
}

/**
 * Main function to send user message and handle AI response
 * Manages UI state, streaming response, and error handling
 */
async function sendMessage() {

    
    const question = inputBox.value.trim();
    
    // Prevent sending empty messages or multiple simultaneous requests
    if (!question || isLoading) return;
    
    // Stop voice recording if active
    stopRecording();
    
    // Hide welcome/empty state when first message is sent
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    
    // Remove previous spacer if any
    removePreviousSpacer();
    
    // Create and add user message to chat
    userMessageDiv = addMessage(question, 'user');
    
    // Create assistant message container with loading state
    const messageDiv = createAssistantMessage();
    
    // Append messages to the end
    chatContainer.appendChild(userMessageDiv);
    chatContainer.appendChild(messageDiv);
    
    // Add bottom spacer to ensure content can scroll properly
    const spacerDiv = createBottomSpacer(userMessageDiv, messageDiv);
    chatContainer.appendChild(spacerDiv);

    // Scroll to show user message and loading indicator
    // requestAnimationFrame(() => {
    //     chatContainer.scrollTo({ top: chatContainer.scrollHeight, behavior: 'smooth' });
    // });


    // Get message components for manipulation
    const contentDiv = messageDiv.querySelector('.message-text');
    const actionsDiv = messageDiv.querySelector('.message-actions');
    
    // Set up message action buttons (copy/share)
    setupMessageActions(messageDiv, contentDiv);
    
    // Prepare UI for loading state
    prepareUIForLoading();

    // Auto-scroll to keep assistant message bottom visible
    scrollToMessageBottom(contentDiv.closest('.message'));

    try {
        // Send request to backend and handle streaming response
        const result = await handleStreamingResponse(question, contentDiv, actionsDiv);

    } catch (error) {
        console.error('Message sending error:', error);
        contentDiv.textContent = t('messages.error');
    } finally {
        // Clean up and restore UI state
        cleanupAfterMessage(messageDiv);
        // Focus input only on user action
        handleFocus();
         // Auto-scroll to keep assistant message bottom visible
         scrollToMessageBottom(contentDiv.closest('.message'));
    }
}

/**
 * Create assistant message container with loading spinner
 * @returns {HTMLElement} The created message element
 */
function createAssistantMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    // Set initial minimal height to fit icon and small space (100px)
    // messageDiv.style.paddingBottom = '50px';

    
    messageDiv.innerHTML = `
        <div class="message-icon">Nutr</div>
        <div class="message-content">
            <div class="message-text">
                <div class="loading">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
            <div class="message-actions" style="display:none">
                <button class="action-btn copy-btn" title="" style="border-radius:50%;padding:8px;background:#f3f3f3;border:none;box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-right:6px;cursor:pointer;width:40px;height:40px;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-clipboard" style="font-size:1.3em;"></i>
                </button>
                <button class="action-btn share-btn" title="" style="border-radius:50%;padding:8px;background:#f3f3f3;border:none;box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-right:6px;cursor:pointer;width:40px;height:40px;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-share" style="font-size:1.3em;"></i>
                </button>
                <button class="action-btn like-btn" title="Like" style="border-radius:50%;padding:8px;background:#e6f9e6;border:none;box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-left:6px;cursor:pointer;width:40px;height:40px;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-hand-thumbs-up" style="font-size:1.3em;"></i>
                </button>
                <button class="action-btn dislike-btn" title="Dislike" style="border-radius:50%;padding:8px;background:#f9e6e6;border:none;box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-left:2px;cursor:pointer;width:40px;height:40px;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-hand-thumbs-down" style="font-size:1.3em;"></i>
                </button>
                <button class="action-btn tts-btn" title="" style="border-radius:50%;padding:8px;background:#c1ddf1;border:none;box-shadow:0 1px 4px rgba(0,0,0,0.07);margin-left:2px;cursor:pointer;width:40px;height:40px;display:inline-flex;align-items:center;justify-content:center;">
                    <i class="bi bi-volume-up" style="font-size:1.3em;"></i>
                </button>
            </div>
        </div>
    `;
    
    return messageDiv;
}

/**
 * Set up copy and share button functionality for a message
 * @param {HTMLElement} messageDiv - The message container
 * @param {HTMLElement} contentDiv - The message content element
 */
function setupMessageActions(messageDiv, contentDiv) {
    const copyBtn = messageDiv.querySelector('.copy-btn');
    const shareBtn = messageDiv.querySelector('.share-btn');
    const ttsBtn = messageDiv.querySelector('.tts-btn');
    const commentBtn = messageDiv.querySelector('.comment-btn');
    const likeBtn = messageDiv.querySelector('.like-btn');
    const dislikeBtn = messageDiv.querySelector('.dislike-btn');
    
    // TTS button - speak the message text
    if (ttsBtn) {
        ttsBtn.addEventListener('click', () => {
            const textToSpeak = contentDiv.textContent;
            if (!textToSpeak || textToSpeak.trim().length === 0) {
                return;
            }
            
            // If this button is already playing, stop it
            if (activeTtsButton === ttsBtn && ttsAudio) {
                stopTTS();
                return;
            }
            
            // Stop any currently playing TTS
            if (ttsAudio) {
                stopTTS();
            }
            
            speakText(textToSpeak, ttsBtn);
        });
    }
    
    // Like/dislike buttons
    if (likeBtn) {
        likeBtn.addEventListener('click', () => {
            const questionId = likeBtn.dataset.questionId || (commentBtn && commentBtn.dataset.questionId);
            if (!questionId) {
                console.log('Like button clicked but no question_id available');
                return;
            }
            // Immediate visual feedback (optimistic UI)
            likeBtn.style.background = '#49fc49ff';
            dislikeBtn && (dislikeBtn.style.background = '#f9e6e6');
            
            // Fire-and-forget API call (non-blocking)
            fetch('/api/like_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_id: questionId, like: true })
            }).then(res => res.json())
              .then(result => {
                  if (result.status !== 'success') {
                      console.log('Like vote failed:', result.message);
                  }
              })
              .catch(e => console.log('Like vote error:', e));
        });
    }
    if (dislikeBtn) {
        dislikeBtn.addEventListener('click', () => {
            const questionId = dislikeBtn.dataset.questionId || (commentBtn && commentBtn.dataset.questionId);
            if (!questionId) {
                console.log('Dislike button clicked but no question_id available');
                return;
            }
            // Immediate visual feedback (optimistic UI)
            dislikeBtn.style.background = '#f86868ff';
            likeBtn && (likeBtn.style.background = '#e6f9e6');
            
            // Fire-and-forget API call (non-blocking)
            fetch('/api/like_answer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_id: questionId, like: false })
            }).then(res => res.json())
              .then(result => {
                  if (result.status !== 'success') {
                      console.log('Dislike vote failed:', result.message);
                  }
              })
              .catch(e => console.log('Dislike vote error:', e));
        });
    }

    // Set translated titles
    copyBtn.title = t('messages.copy');
    shareBtn.title = t('messages.share');
    if (commentBtn) commentBtn.title = t('messages.comment');

    // Copy message text to clipboard
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(contentDiv.textContent);
    });

    // Share message using Web Share API or fallback
    shareBtn.addEventListener('click', () => {
        if (navigator.share) {
            navigator.share({
                text: contentDiv.textContent
            });
        } else {
            alert(t('messages.shareNotSupported'));
        }
    });


}

/**
 * Prepare UI for loading state during message sending
 */
function prepareUIForLoading() {
    // Disable input controls during loading
    isLoading = true;
    sendButton.disabled = true;
    inputBox.disabled = true;
    voiceButton.disabled = true;

}

/**
 * Handle streaming response from the server
 * @param {string} question - The user's question
 * @param {HTMLElement} contentDiv - Element to display response content
 * @param {HTMLElement} actionsDiv - Element containing action buttons
 */
async function handleStreamingResponse(question, contentDiv, actionsDiv) {
    // Prepare request payload with language information and session_id
    const requestData = {
        question: question,
        language: currentLanguage,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        locale: navigator.language || (currentLanguage === 'en' ? 'en-US' : 'fr-FR'),
        session_id: sessionId  // Include session_id to maintain conversation context
    };

    const response = await fetch('/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let questionId = null;
    let commentBtn = null;
    let likeBtn = null;
    let dislikeBtn = null;

    // For markdown streaming, accumulate the full text and render as HTML
    let fullText = '';
    while (true) {
        const { done, value } = await reader.read();

        if (done) {
            // Streaming complete - show action buttons
            actionsDiv.style.display = '';
            // Set questionId on comment, like, and dislike buttons if available
            if (questionId) {
                if (!commentBtn && actionsDiv) commentBtn = actionsDiv.querySelector('.comment-btn');
                if (!likeBtn && actionsDiv) likeBtn = actionsDiv.querySelector('.like-btn');
                if (!dislikeBtn && actionsDiv) dislikeBtn = actionsDiv.querySelector('.dislike-btn');
                if (commentBtn) commentBtn.dataset.questionId = questionId;
                if (likeBtn) likeBtn.dataset.questionId = questionId;
                if (dislikeBtn) dislikeBtn.dataset.questionId = questionId;
            }
            // Final markdown render
            if (typeof marked !== 'undefined') {
                contentDiv.innerHTML = marked.parse(fullText);
            } else {
                contentDiv.textContent = fullText;
            }
            // Call fetchAndDisplayPmids at the end of streaming
            await fetchAndDisplayPmids(contentDiv);
            break;
        }

        // Decode and process new data
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete message in buffer

        // Process each complete message line
        for (const message of lines) {
            if (!message.trim()) continue;

            const dataMatch = message.match(/^data: (.+)$/m);
            if (dataMatch) {
                try {
                    const data = JSON.parse(dataMatch[1]);

                    // Store session_id from first chunk
                    if (data.session_id && !sessionId) {
                        sessionId = data.session_id;
                        window.sessionId = sessionId; // Store globally for later use
                        console.log('Session ID received:', sessionId);
                    }
                    // Store question_id from first chunk
                    if (data.question_id && !questionId) {
                        questionId = data.question_id;
                        window.questionId = questionId; // Store globally for later use
                        // Find the comment, like, and dislike buttons and set data-question-id
                        if (!commentBtn && actionsDiv) commentBtn = actionsDiv.querySelector('.comment-btn');
                        if (!likeBtn && actionsDiv) likeBtn = actionsDiv.querySelector('.like-btn');
                        if (!dislikeBtn && actionsDiv) dislikeBtn = actionsDiv.querySelector('.dislike-btn');
                        if (commentBtn) commentBtn.dataset.questionId = questionId;
                        if (likeBtn) likeBtn.dataset.questionId = questionId;
                        if (dislikeBtn) dislikeBtn.dataset.questionId = questionId;
                    }

                    // Append new content chunk
                    if (data.chunk) {
                        // Remove loading spinner on first content chunk
                        const loadingDiv = contentDiv.querySelector('.loading');
                        if (loadingDiv) {
                            contentDiv.textContent = '';
                        }
                        fullText += data.chunk;
                        // Live preview (optional): render markdown as HTML if marked is available
                        if (typeof marked !== 'undefined') {
                            contentDiv.innerHTML = marked.parse(fullText);
                        } else {
                            contentDiv.textContent = fullText;
                        }
                        // Auto-scroll to keep assistant message bottom visible
                        scrollToMessageBottom(contentDiv.closest('.message'));
                    }
                  
                    updateScrollIndicator();
                } catch (parseError) {
                    console.error('JSON parsing error:', parseError);
                }
            }
        }
    }
}

// Appelle l’API pour obtenir les PMIDs pertinents à la question et les affiche sous la réponse
async function fetchAndDisplayPmids( container) {
    try {
        // Use sessionId and questionId if available for accurate retrieval
        const payload = { };
        if (window.sessionId && window.questionId) {
            payload.session_id = window.sessionId;
            payload.question_id = window.questionId;
        }
        const res = await fetch('/api/pmids', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.pmids && data.pmids.length > 0) {
            const refsDiv = document.createElement('div');
            refsDiv.className = 'pmid-refs';
            refsDiv.innerHTML = `<strong>Références PubMed :</strong> ` +
                data.pmids.map(pmid => {
                    // Extraire juste le numéro
                    const num = pmid.replace(/[^\d]/g, '');
                    const url = `https://google.com/search?q=${pmid}`;
                    return `<a href="${url}" target="_blank" rel="noopener">${pmid}</a>`;
                }).join(', ');
            container.appendChild(refsDiv);
        }
    } catch (e) {
        console.error('Erreur lors de la récupération des PMIDs', e);
    }
}

/**
 * Clean up UI state after message completion
 * @param {HTMLElement} messageDiv - The message container to clean up
 */
function cleanupAfterMessage(messageDiv) {
    // Restore normal padding
    // messageDiv.style.paddingBottom = '50px';
    
    // Re-enable input controls
    isLoading = false;
    sendButton.disabled = false;
    inputBox.disabled = false;
    voiceButton.disabled = false;
    
    // Update scroll indicator
    updateScrollIndicator();
}

// ===================================
// UTILITY FUNCTIONS
// ===================================
/**
 * Initialize suggestion card click handlers
 * When clicked, populates input with example question and sends it
 */
function initSuggestionCards() {
    document.querySelectorAll('.suggestion-card[data-category]').forEach(card => {
        card.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            const langData = translations[currentLanguage] || translations['fr'];
            const suggestionData = langData.suggestions && langData.suggestions[category];
            
            if (suggestionData && suggestionData.question) {
                // Set the question in the input box
                inputBox.value = suggestionData.question;
                
                // Resize input box to fit content
                inputBox.style.height = 'auto';
                inputBox.style.height = Math.min(inputBox.scrollHeight, 200) + 'px';
                
                // Auto-send the message
                sendMessage();
            }
        });
    });
}

/**
 * Add a new message to the chat container
 * @param {string} text - The message text content
 * @param {string} role - Message role ('user' or 'assistant')
 * @returns {HTMLElement} The created message element
 */
function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-icon">${role === 'user' ? 'U' : 'NIA'}</div>
        <div class="message-content">${escapeHtml(text)}</div>
    `;
    // Clear the text area
    inputBox.value = '';
    inputBox.style.height = 'auto';

    // Note: Scrolling is handled by the calling function for better control
    return messageDiv;
}

/**
 * Escape HTML characters to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} HTML-escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===================================
// VOICE RECOGNITION
// ===================================

/**
 * Initialize speech recognition
 */
function initSpeechRecognition() {
    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        console.warn('Speech recognition not supported in this browser');
        voiceButton.style.display = 'none';
        return;
    }
    
    recognition = new SpeechRecognition();
    recognition.continuous = false; // Disable continuous mode to prevent duplications
    recognition.interimResults = true;
    recognition.lang = currentLanguage === 'en' ? 'en-US' : 'fr-FR';
    
    let finalTranscript = '';
    
    recognition.onstart = function() {
        isRecording = true;
        voiceButton.classList.add('recording');
        finalTranscript = '';
        console.log('Voice recording onstart');
    };
    
    recognition.onresult = function(event) {
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Update input box with transcription
        inputBox.value = finalTranscript + interimTranscript;
        inputBox.style.height = 'auto';
        inputBox.style.height = Math.min(inputBox.scrollHeight, 200) + 'px';
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        stopRecording();
    };
    
    recognition.onend = function() {
        if (isRecording) {
            // Restart recognition to continue capturing speech
            try {
                recognition.start();
            } catch (error) {
                console.log('Recognition restart error:', error);
            }
        }
    };
}

/**
 * Toggle voice recording
 */
function toggleRecording() {
    if (isRecording) {
        // Stop recording (Whisper or Web Speech API)
        if (useWhisper) {
            stopWhisperRecording();
        } else {
            stopRecording();
        }
    } else {
        // Start recording (Whisper or Web Speech API)
        if (useWhisper) {
            isRecording = true;
            voiceButton.classList.add('recording');
            initWhisperRecording();
        } else {
            if (!recognition) {
                alert(currentLanguage === 'en' 
                    ? 'Speech recognition is not supported in your browser.' 
                    : 'La reconnaissance vocale n\'est pas supportée par votre navigateur.');
                return;
            }
            startRecording();
        }
    }
}

/**
 * Start voice recording
 */
function startRecording() {
    try {
        recognition.lang = currentLanguage === 'en' ? 'en-US' : 'fr-FR';
        recognition.start();
        console.log('Voice recording started');
    } catch (error) {
        console.error('Failed to start recording:', error);
    }
}

/**
 * Stop voice recording and clear text area
 */
function stopRecording() {
    if (recognition && isRecording) {
        isRecording = false;
        voiceButton.classList.remove('recording');
        recognition.stop();
        console.log('Voice recording stopped');
        

    }
}

/**
 * Initialize Whisper recording (MediaRecorder API)
 */
async function initWhisperRecording() {
    try {
        // Clear input box when starting recording
        inputBox.value = '';
        inputBox.style.height = 'auto';
        
        // Disable input controls during recording
        inputBox.disabled = true;
        sendButton.disabled = true;
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        whisperStream = stream;
        
        // Use webm format for better compatibility
        const options = { mimeType: 'audio/webm' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'audio/ogg; codecs=opus';
        }
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = ''; // Use default
        }
        
        mediaRecorder = new MediaRecorder(stream, options);
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            if (audioChunks.length === 0) {
                console.warn('No audio data recorded');
                // Re-enable input controls
                inputBox.disabled = false;
                sendButton.disabled = false;
                return;
            }
            
            // Create audio blob
            const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            audioChunks = [];
            
            // Check if audio is too small (likely no speech, just silence)
            const MIN_AUDIO_SIZE = 10000; // 10KB minimum
            if (audioBlob.size < MIN_AUDIO_SIZE) {
                console.log('Audio too small, likely no speech detected');
                // Re-enable input controls
                inputBox.disabled = false;
                sendButton.disabled = false;
                // Restore placeholder
                inputBox.placeholder = t('input.placeholder') || 'Pose-moi une question...';
                return;
            }
            
            // Stop animation and show processing indicator
            if (recordingAnimationInterval) {
                clearInterval(recordingAnimationInterval);
                recordingAnimationInterval = null;
            }
            
            inputBox.placeholder = currentLanguage === 'en' 
                ? '⏳ Processing audio...' 
                : '⏳ Traitement audio...';
            
            // Send to backend for transcription
            await transcribeWithWhisper(audioBlob);
            
            // Restore placeholder
            inputBox.placeholder = t('input.placeholder') || 'Pose-moi une question...';
        };
        
        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
            stopWhisperRecording();
        };
        
        // Start recording
        mediaRecorder.start();
        
            
        // Set maximum recording duration (30 seconds)
        const MAX_RECORDING_DURATION = 30000; // 30 seconds
        const WARNING_TIME = 25000; // Show warning at 25 seconds (5s remaining)
        
        // Show warning at 25 seconds
        warningTimer = setTimeout(() => {
            if (isRecording) {
                console.log('Recording warning: 5 seconds remaining');
                // Update placeholder to show warning
                inputBox.placeholder = currentLanguage === 'en' 
                    ? '⏱️ Recording (5s remaining...)' 
                    : '⏱️ Enregistrement (5s restantes...)';
            }
        }, WARNING_TIME);
        
        // Auto-stop at maximum duration
        maxDurationTimer = setTimeout(() => {
            if (isRecording) {
                console.log('Maximum recording duration reached (30s) - auto-stopping');
                stopWhisperRecording();
            }
        }, MAX_RECORDING_DURATION);
        
        // Animate placeholder during recording
        let dots = 0;
        const baseText = currentLanguage === 'en' 
            ? '🎤 Recording' 
            : '🎤 Enregistrement';
        
        recordingAnimationInterval = setInterval(() => {
            // Stop animation if recording stopped
            if (!isRecording) {
                if (recordingAnimationInterval) {
                    clearInterval(recordingAnimationInterval);
                    recordingAnimationInterval = null;
                }
                return;
            }
            dots = (dots + 1) % 4;
            inputBox.placeholder = baseText + '.'.repeat(dots) ;
        }, 500);
        
        console.log('Whisper recording started with', mediaRecorder.mimeType);
        
    } catch (error) {
        console.error('Failed to initialize Whisper recording:', error);
        alert(currentLanguage === 'en' 
            ? 'Could not access microphone. Please check permissions.' 
            : 'Impossible d\'accéder au microphone. Vérifiez les permissions.');
        isRecording = false;
        voiceButton.classList.remove('recording');
        
        // Clean up audio context
        if (audioContext) {
            audioContext.close();
            audioContext = null;
            analyser = null;
        }
        
        
        // Clear max duration timers
        if (maxDurationTimer) {
            clearTimeout(maxDurationTimer);
            maxDurationTimer = null;
        }
        if (warningTimer) {
            clearTimeout(warningTimer);
            warningTimer = null;
        }
        
        // Stop animation on error
        if (recordingAnimationInterval) {
            clearInterval(recordingAnimationInterval);
            recordingAnimationInterval = null;
        }
        
        // Re-enable input controls on error
        inputBox.disabled = false;
        sendButton.disabled = false;
    }
}

/**
 * Stop Whisper recording
 */
function stopWhisperRecording() {
    // Set recording flag to false immediately to stop animation interval
    isRecording = false;
    voiceButton.classList.remove('recording');
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        console.log('Whisper recording stopped');
    }
    
    if (whisperStream) {
        whisperStream.getTracks().forEach(track => track.stop());
        whisperStream = null;
    }
    
    // Clean up audio context and analyser
    if (audioContext) {
        audioContext.close();
        audioContext = null;
        analyser = null;
    }

    // Clear max duration timers
    if (maxDurationTimer) {
        clearTimeout(maxDurationTimer);
        maxDurationTimer = null;
    }
    if (warningTimer) {
        clearTimeout(warningTimer);
        warningTimer = null;
    }
    
    // Stop animation
    if (recordingAnimationInterval) {
        clearInterval(recordingAnimationInterval);
        recordingAnimationInterval = null;
    }
}

/**
 * Send audio to backend for Whisper transcription
 */
async function transcribeWithWhisper(audioBlob) {
    try {
        // Use interface language for transcription
        const sourceLang = currentLanguage || 'fr';
        
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        formData.append('language', sourceLang);
        
        const response = await fetch('/api/transcribe_audio', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.text) {
            // Filter out common Whisper hallucinations (occurs with silence/no speech)
            const hallucinations = [
                'thank you for watching',
                'thanks for watching',
                'thank you',
                'bye',
                'bye bye',
                'goodbye'
            ];
            
            const lowerText = result.text.toLowerCase().trim();
            const isHallucination = hallucinations.some(phrase => 
                lowerText === phrase || lowerText === phrase + '.'
            );
            
            if (isHallucination) {
                console.log('Whisper hallucination detected, ignoring:', result.text);
                // Re-enable input controls without sending
                inputBox.disabled = false;
                sendButton.disabled = false;
                return;
            }
            
            // Append transcribed text to input box
            const currentText = inputBox.value.trim();
            inputBox.value = currentText ? currentText + ' ' + result.text : result.text;
            
            // Resize input box to fit content
            inputBox.style.height = 'auto';
            inputBox.style.height = Math.min(inputBox.scrollHeight, 200) + 'px';
            
            console.log('Whisper transcription:', result.text);
            
            // Re-enable input controls before sending
            inputBox.disabled = false;
            sendButton.disabled = false;
            
            // Automatically send the transcribed message
            sendMessage();
        } else if (result.error) {
            console.error('Whisper transcription error:', result.error);
            // Re-enable input controls on error
            inputBox.disabled = false;
            sendButton.disabled = false;
        }
        
    } catch (error) {
        console.error('Failed to transcribe with Whisper:', error);
        alert(currentLanguage === 'en' 
            ? 'Failed to transcribe audio. Please try again.' 
            : 'Échec de la transcription. Veuillez réessayer.');
        // Re-enable input controls on error
        inputBox.disabled = false;
        sendButton.disabled = false;
    }
}

/**
 * Stop currently playing TTS audio
 */
function stopTTS() {
    if (ttsAudio) {
        ttsAudio.pause();
        ttsAudio.currentTime = 0;
        ttsAudio = null;
    }
    if (activeTtsButton) {
        activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
        activeTtsButton.disabled = false;
        activeTtsButton = null;
    }
}

/**
 * Convert text to speech and play audio
 * @param {string} text - Text to convert to speech
 * @param {HTMLElement} button - The TTS button element
 */
async function speakText(text, button = null) {
    try {
        // Stop any currently playing TTS
        if (ttsAudio) {
            stopTTS();
        }
        
        if (button) {
            activeTtsButton = button;
            // Show loading spinner
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            button.disabled = true;
        }
        
        // Request TTS from backend
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                language: currentLanguage || 'fr'
            })
        });
        
        if (!response.ok) {
            throw new Error('TTS request failed');
        }
        
        // Create audio element from response
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        ttsAudio = new Audio(audioUrl);
        
        // Update button to show stop icon when audio is ready
        if (activeTtsButton) {
            activeTtsButton.innerHTML = '<i class="bi bi-stop-fill" style="font-size:1.3em;"></i>';
            activeTtsButton.disabled = false;
        }
        
        // Play audio
        await ttsAudio.play();
        
        // Clean up when audio finishes
        ttsAudio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            if (activeTtsButton) {
                activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
                activeTtsButton = null;
            }
            ttsAudio = null;
        };
        
        // Handle errors during playback
        ttsAudio.onerror = (error) => {
            console.error('TTS playback error:', error);
            URL.revokeObjectURL(audioUrl);
            if (activeTtsButton) {
                activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
                activeTtsButton = null;
            }
            ttsAudio = null;
        };
        
    } catch (error) {
        console.error('TTS error:', error);
        if (activeTtsButton) {
            activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
            activeTtsButton.disabled = false;
            activeTtsButton = null;
        }
    }
}

// Voice button click handler
voiceButton.addEventListener('click', toggleRecording);

// ===================================
// INITIALIZATION
// ===================================

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Load translations and set up internationalization
    loadTranslations();
    
    // Check for cookie consent
    checkCookieConsent();
    
    // Initialize speech recognition
    initSpeechRecognition();
    
    // Initialize keyboard detection for mobile
    initKeyboardDetection();
    
    // Initialize suggestion card click handlers
    initSuggestionCards();
    
    // Add language switcher for testing (comment out in production)
    // addLanguageSwitcher();
});



