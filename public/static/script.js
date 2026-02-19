// ===================================
// CONFIGURATION
// ===================================

// Backend URL - can be overridden by window.BACKEND_URL from config.js
// Empty string defaults to same-origin (relative URLs)
const BACKEND_URL = window.BACKEND_URL || '';
console.log('Using BACKEND_URL:', BACKEND_URL);
// ===================================
// INTERNATIONALIZATION SYSTEM
// ===================================

let translations = {};
let mainConfig = {};
let translatorConfig = {};
let nutriaConfig = {};
let currentLanguage = 'fr';

/**
 * Get URL parameter by name
 */
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

/**
 * Load all configurations separately (main, translator, nutria)
 */
async function loadTranslations() {
    try {
        // Load main config
        const mainResponse = await fetch(`${BACKEND_URL}/api/get_config?agent=main`);
        mainConfig = await mainResponse.json();
        console.log('Main config loaded:', mainConfig);

        // Load translator config
        const translatorResponse = await fetch(`${BACKEND_URL}/api/get_config?agent=translator`);
        translatorConfig = await translatorResponse.json();
        console.log('Translator config loaded:', translatorConfig);

        // Load nutria config
        const nutriaResponse = await fetch(`${BACKEND_URL}/api/get_config?agent=nutria`);
        nutriaConfig = await nutriaResponse.json();
        console.log('Nutria config loaded:', nutriaConfig);
        
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
    const langData = translatorConfig[lang] || translatorConfig['fr'];
    
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
    
    // Update agent selector labels
    if (typeof updateAgentSelectorLabels === 'function') {
        updateAgentSelectorLabels();
    }
    
    // Populate language dropdown from config
    populateLanguageDropdown(lang);
    
    // Populate suggestion cards from config
    populateSuggestionCards(lang);
    
    // Refresh agent-specific placeholders
    if (typeof switchAgent === 'function' && typeof currentAgent !== 'undefined') {
        switchAgent(currentAgent);
    }
    
    // Update language selector value
    const langSelector = document.getElementById('language-selector');
    if (langSelector) {
        langSelector.value = lang;
    }
}

/**
 * Populate the target language dropdown from config languages
 */
function populateLanguageDropdown(lang) {
    const select = document.getElementById('target-language');
    if (!select) return;
    
    const langData = translatorConfig[lang] || translatorConfig['fr'];
    const languages = langData && langData.languages;
    if (!languages) return;
    
    const currentValue = select.value;
    select.innerHTML = '';
    
    for (const [code, label] of Object.entries(languages)) {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = label;
        select.appendChild(option);
    }
    
    // Restore previous selection if still available
    if (languages[currentValue]) {
        select.value = currentValue;
    }
}

/**
 * Populate suggestion cards dynamically from config
 */
function populateSuggestionCards(lang) {
    const suggestionsContainer = document.querySelector('.suggestions');
    if (!suggestionsContainer) return;
    
    const langData = mainConfig[lang] || mainConfig['fr'];
    const agents = langData && langData.agents;
    
    // Clear existing cards
    suggestionsContainer.innerHTML = '';
    
    // If agents array exists, create agent selection cards
    if (agents && Array.isArray(agents)) {
        agents.forEach(agent => {
            const card = document.createElement('div');
            card.className = 'suggestion-card agent-card';
            card.setAttribute('data-agent', agent.id);
            
            // Set background color if color attribute exists
            if (agent.color) {
                card.style.backgroundColor = agent.color;
            }
            
            const title = document.createElement('h3');
            title.textContent = `${agent.icon} ${agent.title}`;
            
            const description = document.createElement('p');
            description.textContent = agent.description;
            
            card.appendChild(title);
            card.appendChild(description);
            
            // Add click event listener
            card.addEventListener('click', async function() {
                const agentId = this.getAttribute('data-agent');
                if (agentSelector) {
                    agentSelector.value = agentId;
                }
                await switchAgent(agentId, true);
            });
            
            suggestionsContainer.appendChild(card);
        });
    }
    // Otherwise, if suggestions object exists, create topic suggestion cards
    else if (langData && langData.suggestions) {
        const suggestions = langData.suggestions;
        
        // Handle both array and object formats
        const suggestionsList = Array.isArray(suggestions) 
            ? suggestions 
            : Object.entries(suggestions).map(([key, value]) => ({ id: key, ...value }));
        
        suggestionsList.forEach((suggestion) => {
            const card = document.createElement('div');
            card.className = 'suggestion-card';
            
            // Set background color if color attribute exists
            if (suggestion.color) {
                card.style.backgroundColor = suggestion.color;
            }
            
            const title = document.createElement('h3');
            // Add icon if it exists as a separate attribute
            title.textContent = suggestion.icon ? `${suggestion.icon} ${suggestion.title}` : suggestion.title;
            
            const description = document.createElement('p');
            description.textContent = suggestion.description;
            
            card.appendChild(title);
            card.appendChild(description);
            
            // Add click event listener
            card.addEventListener('click', async function() {
                if (suggestion.event && suggestion.event.startsWith('display:')) {
                    // Extract text from event (e.g., "display:Some text" -> "Some text")
                    const displayText = suggestion.event.split(':')[1] || suggestion.event.replace('display:', '').trim();
                    if (inputBox && displayText) {
                        inputBox.value = displayText;
                        console.log(`Displaying text: ${displayText}`);
                        inputBox.focus();
                    }
                } else if (suggestion.event && suggestion.event.startsWith('switch:')) {
                    // Extract agent name from event (e.g., "switch:nutria" -> "nutria")
                    const agentName = suggestion.event.split(':')[1] || suggestion.event.replace('switch:', '').trim();
                    if (agentName && typeof switchAgent === 'function') {
                        if (agentSelector) {
                            agentSelector.value = agentName;
                        }
                        console.log(`Switching agent to: ${agentName}`);
                        await switchAgent(agentName, true);
                    }
                } else {
                    // No action for other events
                    console.log('No action for suggestion event:', suggestion.event);
                }
            });
            
            suggestionsContainer.appendChild(card);
        });
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
    
    // Update language selector value
    const langSelector = document.getElementById('language-selector');
    if (langSelector) {
        langSelector.value = lang;
    }
    
    // Update source language display in translator
    updateSourceLanguageDisplay();
}

/**
 * Update the source language display in translator options
 */
function updateSourceLanguageDisplay() {
    if (!sourceLanguageText) return;
    
    const langData = translatorConfig[currentLanguage] || translatorConfig['fr'];
    const languages = langData.languages || {};
    
    // Always display interface language (doesn't change with arrow direction)
    const displayLang = currentLanguage || 'fr';
    
    sourceLanguageText.textContent = languages[displayLang] || displayLang.toUpperCase();
}

/**
 * Get translation for a key
 */
function t(key) {
    const langData = translatorConfig[currentLanguage] || translatorConfig['fr'];
    return getNestedValue(langData, key) || key;
}

/**
 * Get current language
 */
function getCurrentLanguage() {
    return currentLanguage;
}

/**
 * Switch active configuration based on agent
 * @param {string} agent - Agent name ('translator' or 'dok2u')
 */
function switchActiveConfig(agent) {
    currentAgent = agent;
    applyTranslations(currentLanguage);
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

// TTS (Text-to-Speech) state
let ttsAudio = null; // Current Audio object for playback
let activeTtsButton = null; // Track which button is currently playing

// Agent state
let currentAgent = 'dok2u'; // 'dok2u' or 'translator'
const agentSelector = document.getElementById('agent-selector');
const translateOptions = document.getElementById('translate-options');
const targetLanguageSelect = document.getElementById('target-language');
const translationDirectionBtn = document.getElementById('translation-direction-btn');
const sourceLanguageText = document.getElementById('source-language-text');

// Translation state
let translationReversed = false; // Track if translation direction is reversed

// Voice recording state
let recognition = null;
let isRecording = false;

// Keyboard state
let isKeyboardVisible = false;
let previousViewportHeight = window.innerHeight;

// ===================================
// COMPONENT REGISTRY SYSTEM
// ===================================

/**
 * Component Registry - manages UI components for different agents
 */
const componentRegistry = {
    /**
     * Language Selector Component
     * Supports single, pair (source/target), or multi-select modes
     */
    languageSelector: {
        render(config) {
            const container = document.getElementById('translate-options');
            if (!container) return;
            
            const type = config.type || 'pair';
            
            if (type === 'pair') {
                // Show the translate options bar
                container.style.display = 'flex';
                
                // Update labels
                const sourceLabel = document.getElementById('source-language-text');
                const targetSelect = document.getElementById('target-language');
                
                if (sourceLabel && config.source) {
                    sourceLabel.textContent = config.source.label || 'Auto';
                }
                
                // Populate target language options
                if (targetSelect && config.languages) {
                    this.populateLanguages(targetSelect, config.languages, config.target?.default);
                }
            } else {
                // Hide for other types (single/multi not implemented yet)
                container.style.display = 'none';
            }
        },
        
        hide() {
            const container = document.getElementById('translate-options');
            if (container) {
                container.style.display = 'none';
            }
        },
        
        populateLanguages(select, languages, defaultValue) {
            if (!select || !languages) return;
            
            select.innerHTML = '';
            for (const [code, label] of Object.entries(languages)) {
                const option = document.createElement('option');
                option.value = code;
                option.textContent = label;
                select.appendChild(option);
            }
            
            if (defaultValue && languages[defaultValue]) {
                select.value = defaultValue;
            }
        },
        
        getValue() {
            const targetSelect = document.getElementById('target-language');
            return {
                source: 'auto', // Could be extended to read from a source selector
                target: targetSelect ? targetSelect.value : 'fr',
                reversed: translationReversed
            };
        },
        
        reset() {
            translationReversed = false;
            const directionBtn = document.getElementById('translation-direction-btn');
            if (directionBtn) {
                directionBtn.classList.remove('reversed');
            }
        }
    },
    
    /**
     * Input Component
     * Manages input area visibility and configuration
     */
    inputArea: {
        render(config) {
            const inputArea = document.querySelector('.input-area');
            const inputBox = document.getElementById('input-box');
            const disclaimerEl = document.querySelector('.input-disclaimer');
            
            if (inputArea && config.showInputOnLoad !== undefined) {
                inputArea.style.display = config.showInputOnLoad ? '' : 'none';
            }
            
            if (inputBox && config.placeholder) {
                inputBox.placeholder = config.placeholder;
            }
            
            if (disclaimerEl && config.disclaimer) {
                disclaimerEl.textContent = config.disclaimer;
            }
        },
        
        show() {
            const inputArea = document.querySelector('.input-area');
            if (inputArea) {
                inputArea.style.display = '';
            }
        },
        
        hide() {
            const inputArea = document.querySelector('.input-area');
            if (inputArea) {
                inputArea.style.display = 'none';
            }
        }
    }
};

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

// Language selector event listener
const languageSelector = document.getElementById('language-selector');
if (languageSelector) {
    languageSelector.addEventListener('change', function() {
        switchLanguage(this.value);
    });
}


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
    const langData = translatorConfig[currentLanguage] || translatorConfig['fr'];
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
    const langData = translatorConfig[currentLanguage] || translatorConfig['fr'];
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

        const langData = translatorConfig[currentLanguage] || translatorConfig['fr'];
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
            customClass: {popup: 'swal2-dok2u-about'}
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

    // const spacerHeight = chatContainer.clientHeight - userMsgDiv.offsetHeight - assistantMsgDiv.offsetHeight - translateOptionsHeight - 20;
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
    // Route to translation if translator agent is active
    if (currentAgent === 'translator') {
        return sendTranslation();
    }
    
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
    
    messageDiv.innerHTML = `
        <div class="message-icon">D2U</div>
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
    const commentBtn = messageDiv.querySelector('.comment-btn');
    const likeBtn = messageDiv.querySelector('.like-btn');
    const dislikeBtn = messageDiv.querySelector('.dislike-btn');
    const ttsBtn = messageDiv.querySelector('.tts-btn');

    // Set translated titles
    if (ttsBtn) ttsBtn.title = t('messages.listen') || 'Listen';
    copyBtn.title = t('messages.copy');
    shareBtn.title = t('messages.share');
    if (commentBtn) commentBtn.title = t('messages.comment');

    // TTS button to read message aloud
    if (ttsBtn) {
        ttsBtn.addEventListener('click', () => {
            // If this button is currently playing, stop it
            if (activeTtsButton === ttsBtn && ttsAudio) {
                stopTTS();
                return;
            }
            
            let textToSpeak;
            
            // For translation messages, skip the language header
            const translationResult = contentDiv.querySelector('.translation-result > div:last-child');
            if (translationResult) {
                textToSpeak = translationResult.textContent || translationResult.innerText;
            } else {
                textToSpeak = contentDiv.textContent || contentDiv.innerText;
            }
            
            if (textToSpeak && textToSpeak.trim()) {
                speakText(textToSpeak, ttsBtn);
            }
        });
    }

    // Like/dislike buttons
    if (likeBtn) {
        likeBtn.addEventListener('click', async () => {
            const questionId = likeBtn.dataset.questionId || (commentBtn && commentBtn.dataset.questionId);
            if (!questionId) {
                console.log('Like button clicked but no question_id available');
                return;
            }
            // Immediate visual feedback (optimistic UI)
            likeBtn.style.background = '#49fc49ff';
            dislikeBtn && (dislikeBtn.style.background = '#f9e6e6');
            
            // Fire-and-forget API call (non-blocking)
            fetch(`${BACKEND_URL}/api/like_answer`, {
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
            dislikeBtn.style.background = '#ff8686';
            likeBtn && (likeBtn.style.background = '#e6f9e6');
            
            // Fire-and-forget API call (non-blocking)
            fetch(`${BACKEND_URL}/api/like_answer`, {
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

    const response = await fetch(`${BACKEND_URL}/query`, {
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
    let ttsReceivedViaStream = false;
    let ttsPendingQuestionId = null;

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
            // Fetch PMIDs in background 
            await fetchAndDisplayPmids(contentDiv);
            return { fullText, ttsReceivedViaStream };
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

                    // Handle TTS pending notification from stream
                    if (data.tts_pending) {
                        ttsPendingQuestionId = data.tts_pending;
                        console.log('TTS: generation started on server for', ttsPendingQuestionId);
                    }

                    // Append new content chunk
                    if (data.chunk) {

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

/**
 * Clean up UI state after message completion
 * @param {HTMLElement} messageDiv - The message container to clean up
 */
function cleanupAfterMessage(messageDiv) {
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
 * Add a new message to the chat container
 * @param {string} text - The message text content
 * @param {string} role - Message role ('user' or 'assistant')
 * @returns {HTMLElement} The created message element
 */
function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-icon">${role === 'user' ? 'U' : 'D2U'}</div>
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
function initSpeechRecognition() {
    // Check for browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        console.warn('Speech recognition not supported in this browser');
        voiceButton.style.display = 'none';
        return;
    }
    
    recognition = new SpeechRecognition();
    recognition.continuous = true; // Enable continuous mode - won't stop after brief pauses
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
        
        // Update input box with transcription only if still recording
        if (isRecording) {
            inputBox.value = finalTranscript + interimTranscript;
            inputBox.style.height = 'auto';
            inputBox.style.height = Math.min(inputBox.scrollHeight, 200) + 'px';
        }
    };
    
    recognition.onerror = function(event) {
        if (event.error === "no-speech") {
            console.log("Restarting...");
            setTimeout(() => recognition.start(), 1000);
        } else {
            console.error('Speech recognition error:', event.error);
            stopRecording();
        }
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
 * Routes to either Web Speech API or Whisper based on useWhisper flag
 */
function toggleRecording() {
    // Use Whisper if enabled
    if (useWhisper) {
        if (isRecording) {
            stopWhisperRecording();
        } else {
            isRecording = true;
            voiceButton.classList.add('recording');
            initWhisperRecording();
        }
        return;
    }
    
    // Fallback to Web Speech API
    if (!recognition) {
        alert(currentLanguage === 'en' 
            ? 'Speech recognition is not supported in your browser.' 
            : 'La reconnaissance vocale n\'est pas supportée par votre navigateur.');
        return;
    }
    
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

/**
 * Convert language code to speech recognition locale
 */
function getRecognitionLocale(langCode) {
    const localeMap = {
        'fr': 'fr-FR',
        'en': 'en-US',
        'es': 'es-ES',
        'de': 'de-DE',
        'it': 'it-IT',
        'pt': 'pt-PT',
        'nl': 'nl-NL',
        'ru': 'ru-RU',
        'zh': 'zh-CN',
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'ar': 'ar-SA',
        'hi': 'hi-IN',
        'pl': 'pl-PL',
        'tr': 'tr-TR',
        'sv': 'sv-SE',
        'da': 'da-DK',
        'no': 'no-NO',
        'fi': 'fi-FI',
        'uk': 'uk-UA',
        'cs': 'cs-CZ',
        'ro': 'ro-RO',
        'el': 'el-GR',
        'he': 'he-IL',
        'th': 'th-TH',
        'vi': 'vi-VN',
        'id': 'id-ID'
    };
    return localeMap[langCode] || 'en-US';
}

/**
 * Start voice recording
 */
function startRecording() {
    try {
        // Determine source language based on translation direction
        if (currentAgent === 'translator') {
            let sourceLang;
            if (translationReversed) {
                // Reversed: target becomes source
                sourceLang = targetLanguageSelect ? targetLanguageSelect.value : 'en';
            } else {
                // Normal: interface language is source
                sourceLang = currentLanguage || 'fr';
            }
            recognition.lang = getRecognitionLocale(sourceLang);
            console.log(`Voice recording in translator mode: ${sourceLang} (${recognition.lang})`);
        } else {
            recognition.lang = currentLanguage === 'en' ? 'en-US' : 'fr-FR';
            console.log(`Voice recording in interface language: ${currentLanguage} (${recognition.lang})`);
        }
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

// Voice button click handler
voiceButton.addEventListener('click', toggleRecording);

// ===================================
// WHISPER SPEECH RECOGNITION (Alternative to Web Speech API)
// ===================================

// Whisper recording state
let useWhisper = true; // Toggle between Web Speech API (false) and Whisper (true)
let mediaRecorder = null;
let audioChunks = [];
let whisperStream = null;
let recordingAnimationInterval = null;
let silenceTimer = null;
let audioContext = null;
let analyser = null;
let maxDurationTimer = null;
let warningTimer = null;

/**
 * Initialize Whisper-based speech recognition
 * Uses MediaRecorder to capture audio and sends to backend for transcription
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
                if (currentAgent === 'translator') {
                    inputBox.placeholder = t('translator.placeholder') || 'Entrez le texte à traduire...';
                } else {
                    inputBox.placeholder = t('input.placeholder') || 'Pose-moi une question...';
                }
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
            if (currentAgent === 'translator') {
                inputBox.placeholder = t('translator.placeholder') || 'Entrez le texte à traduire...';
            } else {
                inputBox.placeholder = t('input.placeholder') || 'Pose-moi une question...';
            }
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
        // Determine source language based on agent and translation direction
        let sourceLang;
        if (currentAgent === 'translator') {
            if (translationReversed) {
                // Reversed: target becomes source
                sourceLang = targetLanguageSelect ? targetLanguageSelect.value : 'en';
            } else {
                // Normal: interface language is source
                sourceLang = currentLanguage || 'fr';
            }
        } else {
            // Dok2u mode: use interface language
            sourceLang = currentLanguage || 'en';
        }
        
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');
        formData.append('language', sourceLang);
        
        const response = await fetch(`${BACKEND_URL}/api/transcribe_audio`, {
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
 * Toggle between Web Speech API and Whisper
 * Call this function to switch recognition methods
 */
function toggleRecognitionMethod() {
    useWhisper = !useWhisper;
    console.log('Recognition method switched to:', useWhisper ? 'Whisper' : 'Web Speech API');
    // You can add UI feedback here to show which method is active
}

// ===================================
// AGENT SWITCHING
// ===================================

/**
 * Display agent-specific intro in the empty state
 * @param {string} agent - Agent name ('nutria' or 'translator')
 */
function displayAgentIntro(agent) {
    if (!emptyState) return;
    
    // Get the appropriate config based on agent
    const agentConfig = agent === 'translator' ? translatorConfig : nutriaConfig;
    const langData = agentConfig[currentLanguage] || agentConfig['fr'];
    const intro = langData.intro || {};
    
    // Update profile image
    const profileImg = emptyState.querySelector('.profile-photo');
    if (profileImg && intro.profileImage) {
        profileImg.src = intro.profileImage;
    }
    
    // Update title
    const titleEl = emptyState.querySelector('h2[data-i18n="intro.title"]');
    if (titleEl && intro.title) {
        titleEl.textContent = intro.title;
    }
    
    // Update description
    const descEl = emptyState.querySelector('p[data-i18n="intro.description"]');
    if (descEl && intro.description) {
        descEl.textContent = intro.description;
    }
    
    // Update disclaimer
    const disclaimerEl = emptyState.querySelector('strong[data-i18n="intro.disclaimer"]');
    if (disclaimerEl && intro.disclaimer) {
        disclaimerEl.textContent = intro.disclaimer;
    }
    
    // Show the intro
    emptyState.style.display = '';
}

/**
 * Switch between agents using component-driven architecture
 */
async function switchAgent(agent, userInitiated) {
    currentAgent = agent;
    
    // Load agent-specific config when user switches agents
    if (userInitiated) {
        const configAgent = agent === 'dok2u' ? 'nutria' : agent;
        
        // Reload the specific agent config
        try {
            const response = await fetch(`${BACKEND_URL}/api/get_config?agent=${configAgent}`);
            const config = await response.json();
            
            // Update the appropriate config variable
            if (configAgent === 'translator') {
                translatorConfig = config;
            } else {
                nutriaConfig = config;
            }
            
            console.log(`${configAgent} config reloaded:`, config);
        } catch (error) {
            console.error('Failed to reload agent config:', error);
        }
        
        // Display agent-specific intro
        displayAgentIntro(configAgent);
        
        // Get language-specific config
        const agentConfig = configAgent === 'translator' ? translatorConfig : nutriaConfig;
        const langData = agentConfig[currentLanguage] || agentConfig['fr'];
        
        // Render components based on configuration
        renderAgentComponents(langData);
        
        // Clear chat messages when switching agents
        if (chatContainer) {
            chatContainer.querySelectorAll('.message, #chat-bottom-spacer').forEach(el => el.remove());
        }
    }

    // Focus input only on user action
    if (userInitiated) {
        handleFocus();
    }
}

/**
 * Render agent-specific UI components from configuration
 * @param {Object} langData - Language-specific agent configuration
 */
function renderAgentComponents(langData) {
    // Check if agent has components configuration
    if (langData.components) {
        // Render language selector if configured
        if (langData.components.languageSelector) {
            componentRegistry.languageSelector.render(langData.components.languageSelector);
        } else {
            componentRegistry.languageSelector.hide();
        }
        
        // Render input area if configured in components
        if (langData.components.inputArea) {
            componentRegistry.inputArea.render(langData.components.inputArea);
        } else if (langData.input) {
            // Backward compatibility: check old location
            componentRegistry.inputArea.render(langData.input);
        }
    } else {
        // No components config = hide language selector (backward compatibility)
        componentRegistry.languageSelector.hide();
        
        // Still render input area from old location if available
        if (langData.input) {
            componentRegistry.inputArea.render(langData.input);
        }
    }
    
    // Populate suggestion cards
    populateSuggestionCards(currentLanguage);
}

// Agent selector event listener
if (agentSelector) {
    agentSelector.addEventListener('change', async function() {
        await switchAgent(this.value, true);
    });
}

// Translation direction button for translator
if (translationDirectionBtn) {
    translationDirectionBtn.addEventListener('click', function() {
        // Toggle the reversed state
        translationReversed = !translationReversed;
        
        // Update button visual state
        if (translationReversed) {
            translationDirectionBtn.classList.add('reversed');
        } else {
            translationDirectionBtn.classList.remove('reversed');
        }
        
        // Update source language display
        updateSourceLanguageDisplay();
        
        console.log(`Translation direction ${translationReversed ? 'reversed' : 'normal'}`);
    });
}



// Update source language display when target language changes (if reversed)
if (targetLanguageSelect) {
    targetLanguageSelect.addEventListener('change', function() {
        // Reset translation direction to normal (interface -> target)
        translationReversed = false;
        
        // Reset button visual state
        if (translationDirectionBtn) {
            translationDirectionBtn.classList.remove('reversed');
        }
        
        // Update source language display
        updateSourceLanguageDisplay();
    });
}

/**
 * Update agent selector option texts with translations
 */
function updateAgentSelectorLabels() {
    if (!agentSelector) return;
    const options = agentSelector.querySelectorAll('option');
    options.forEach(opt => {
        const key = opt.getAttribute('data-i18n-option');
        if (key) {
            const label = t(key);
            if (label && label !== key) {
                opt.textContent = label;
            }
        }
    });
}

// ===================================
// TRANSLATION FUNCTIONS
// ===================================

/**
 * Send a translation request (text) with streaming response
 * Uses manually selected source language from toggle button
 */
async function sendTranslation() {
    const text = inputBox.value.trim();
    if (!text || isLoading) return;
    
    // Stop voice recording if active
    stopRecording();
    
    // Hide welcome state
    if (emptyState) emptyState.style.display = 'none';
    
    removePreviousSpacer();
    
    // Add user message
    userMessageDiv = addMessage(text, 'user');
    chatContainer.appendChild(userMessageDiv);
    
    // Create assistant message with loading state
    const messageDiv = createAssistantMessage();
    
    // Change icon to globe for translator
    const iconDiv = messageDiv.querySelector('.message-icon');
    if (iconDiv) iconDiv.textContent = 'D2U';
    
    chatContainer.appendChild(messageDiv);

    const spacerDiv = createBottomSpacer(userMessageDiv, messageDiv);
    chatContainer.appendChild(spacerDiv);
    
    const contentDiv = messageDiv.querySelector('.message-text');
    const actionsDiv = messageDiv.querySelector('.message-actions');
    
    // Set up message action buttons (copy/share/like/dislike/TTS)
    setupMessageActions(messageDiv, contentDiv);
    
    prepareUIForLoading();
    
    // Auto-scroll to keep assistant message bottom visible
    scrollToMessageBottom(contentDiv.closest('.message'));

    // Determine source and target languages based on translation direction
    let actualSourceLang, actualTargetLang;
    
    if (translationReversed) {
        // Reversed: target language -> interface language
        actualSourceLang = targetLanguageSelect.value || 'en';
        actualTargetLang = currentLanguage || 'fr';
    } else {
        // Normal: interface language -> target language
        actualSourceLang = currentLanguage || 'fr';
        actualTargetLang = targetLanguageSelect.value || 'en';
    }
    
    console.log(`Translating from ${actualSourceLang} to ${actualTargetLang}`);
    
    // Get language names for display
    const langData = translatorConfig[currentLanguage] || translatorConfig['fr'];
    const languages = langData.languages || {};
    const sourceLangName = languages[actualSourceLang] || actualSourceLang.toUpperCase();
    const targetLangName = languages[actualTargetLang] || actualTargetLang.toUpperCase();
    
    let questionId = null;
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                target_language: targetLangName,
                source_language: sourceLangName
            })
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullText = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                // Final render with detected languages
                contentDiv.innerHTML = `
                    <div class="translation-result">
                        <div class="translation-label">
                            <span style="color: #718096; font-size: 0.85em;">${sourceLangName} → ${targetLangName}</span>
                        </div>
                        <div>${fullText}</div>
                    </div>
                `;
                // Show action buttons
                actionsDiv.style.display = '';
                
                // Set questionId on like/dislike buttons if available
                if (questionId) {
                    const likeBtn = actionsDiv.querySelector('.like-btn');
                    const dislikeBtn = actionsDiv.querySelector('.dislike-btn');
                    if (likeBtn) likeBtn.dataset.questionId = questionId;
                    if (dislikeBtn) dislikeBtn.dataset.questionId = questionId;
                }
                break;
            }
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';
            
            for (const message of lines) {
                if (!message.trim()) continue;
                const dataMatch = message.match(/^data: (.+)$/m);
                if (dataMatch) {
                    try {
                        const data = JSON.parse(dataMatch[1]);
                        
                        // Capture question_id from first chunk
                        if (data.question_id && !questionId) {
                            questionId = data.question_id;
                            console.log('Translation question_id received:', questionId);
                        }
                        
                        if (data.chunk) {
                            const loadingDiv = contentDiv.querySelector('.loading');
                            if (loadingDiv) contentDiv.textContent = '';
                            fullText += data.chunk;
                            contentDiv.textContent = fullText;

                            // Auto-scroll to keep assistant message bottom visible
                            scrollToMessageBottom(contentDiv.closest('.message'));
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
            updateScrollIndicator();
        }
    } catch (error) {
        console.error('Translation error:', error);
        contentDiv.textContent = t('messages.error');
    } finally {
        cleanupAfterMessage(messageDiv);
        
        // Focus input box after translation completes
        handleFocus();
        
        // Auto-scroll to keep assistant message bottom visible
        scrollToMessageBottom(contentDiv.closest('.message'));

        
        // Automatically reverse translation direction for next input
        translationReversed = !translationReversed;
        
        // Update button visual state
        if (translationDirectionBtn) {
            if (translationReversed) {
                translationDirectionBtn.classList.add('reversed');
            } else {
                translationDirectionBtn.classList.remove('reversed');
            }
        }
        
        // Update source language display
        updateSourceLanguageDisplay();
    }
}

// ===================================
// TEXT-TO-SPEECH (TTS)
// ===================================

/**
 * Stop current TTS audio playback
 */
function stopTTS() {
    if (ttsAudio) {
        ttsAudio.pause();
        ttsAudio.currentTime = 0;
        ttsAudio = null;
    }
    
    // Restore button icon
    if (activeTtsButton) {
        activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
        activeTtsButton.disabled = false;
        activeTtsButton = null;
    }
}

/**
 * Read text aloud using OpenAI TTS via backend API
 * @param {string} text - The text to read aloud
 * @param {HTMLElement} button - Optional TTS button to show spinner
 */
async function speakText(text, button = null) {
    if (!text || text.trim().length === 0) {
        console.log('TTS skipped: empty text');
        return;
    }
    
    // Stop any previous playback
    stopTTS();
    
    // Save button reference and show spinner
    if (button) {
        activeTtsButton = button;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" style="color: #1976d2; border-right-color: transparent;"></span>';
        button.disabled = true;
    }
    
    // Strip markdown/HTML for cleaner speech
    const cleanText = text
        .replace(/<[^>]*>/g, '')        // Remove HTML tags
        .replace(/\*\*(.+?)\*\*/g, '$1') // Bold
        .replace(/\*(.+?)\*/g, '$1')     // Italic
        .replace(/#{1,6}\s/g, '')        // Headers
        .replace(/```[\s\S]*?```/g, '')  // Code blocks
        .replace(/`([^`]+)`/g, '$1')     // Inline code
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Links
        .replace(/PMID:\s*\d+/gi, '')    // PMID references
        .replace(/\[\d+\]/g, '')         // Numbered citations [1], [2]
        .replace(/Références?\s*PubMed\s*:.*$/gim, '') // "Références PubMed:" lines
        .replace(/References?\s*:.*$/gim, '')           // "References:" lines
        .replace(/Sources?\s*:.*$/gim, '')              // "Sources:" lines
        .replace(/\n{2,}/g, '. ')        // Multiple newlines to pause
        .replace(/\n/g, ' ')             // Newlines to space
        .replace(/\s{2,}/g, ' ')         // Collapse extra spaces
        .trim();
    
    if (!cleanText) return;
    
    console.log('TTS: speaking', cleanText.length, 'chars, language:', currentLanguage);

    try {
        const response = await fetch(`${BACKEND_URL}/api/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: cleanText,
                language: currentLanguage
            })
        });
        
        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`TTS error: ${response.status} - ${errText}`);
        }
        
        const audioBlob = await response.blob();
        console.log('TTS audio blob size:', audioBlob.size, 'type:', audioBlob.type);
        const audioUrl = URL.createObjectURL(audioBlob);
        ttsAudio = new Audio(audioUrl);
        
        // Change button to stop icon after audio is loaded
        if (button) {
            button.innerHTML = '<i class="bi bi-stop-fill" style="font-size:1.3em;"></i>';
            button.disabled = false;
        }
        
        ttsAudio.addEventListener('ended', () => {
            URL.revokeObjectURL(audioUrl);
            ttsAudio = null;
            // Restore button icon when playback ends
            if (activeTtsButton) {
                activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
                activeTtsButton = null;
            }
        });
        
        ttsAudio.addEventListener('error', () => {
            console.error('TTS audio playback error');
            URL.revokeObjectURL(audioUrl);
            ttsAudio = null;
            // Restore button icon on error
            if (activeTtsButton) {
                activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
                activeTtsButton = null;
            }
        });
        
        await ttsAudio.play();
    } catch (error) {
        console.error('TTS error:', error);
        // Restore button on error
        if (activeTtsButton) {
            activeTtsButton.innerHTML = '<i class="bi bi-volume-up" style="font-size:1.3em;"></i>';
            activeTtsButton.disabled = false;
            activeTtsButton = null;
        }
        if (ttsAudio) {
            ttsAudio = null;
        }
    }
}

// ===================================
// INITIALIZATION
// ===================================

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Load translations and set up internationalization
    loadTranslations().then(() => {
        updateAgentSelectorLabels();
        updateSourceLanguageDisplay();
        
        // Render components based on initial config
        const langData = mainConfig[currentLanguage] || mainConfig['fr'];
        renderAgentComponents(langData);
    });
    
    // Check for cookie consent
    checkCookieConsent();
    
    // Initialize speech recognition
    initSpeechRecognition();
    
    // Initialize speech method indicator and toggle
    const speechMethodIndicator = document.getElementById('speech-method-indicator');
    if (speechMethodIndicator) {
        // Update indicator text based on current method
        function updateIndicator() {
            if (useWhisper) {
                speechMethodIndicator.textContent = '🎤 Whisper';
                speechMethodIndicator.style.background = '#4CAF50';
            } else {
                speechMethodIndicator.textContent = '🎤 Web Speech';
                speechMethodIndicator.style.background = '#2196F3';
            }
        }
        
        // Click to toggle between methods
        speechMethodIndicator.addEventListener('click', () => {
            toggleRecognitionMethod();
            updateIndicator();
        });
        
        // Initialize display
        updateIndicator();
    }
    
    // Initialize mobile keyboard detection
    if (isMobileDevice()) {
        initKeyboardDetection();
    }
});


