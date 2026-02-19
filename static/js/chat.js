// ===================================
// CHAT MESSAGING FUNCTIONALITY
// ===================================

/**
 * Chat module
 * Handles message sending, streaming responses, and message UI
 */

// Global state
let isLoading = false;
let sessionId = null;
let userMessageDiv = document.createElement('div');

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Add message to chat
 */
function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `
        <div class="message-icon">${role === 'user' ? 'U' : 'D2U'}</div>
        <div class="message-content">${escapeHtml(text)}</div>
    `;
    
    const inputBox = document.getElementById('input-box');
    if (inputBox) {
        inputBox.value = '';
        inputBox.style.height = 'auto';
    }
    
    return messageDiv;
}

/**
 * Create assistant message with loading state
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
 * Setup message action buttons
 */
function setupMessageActions(messageDiv, contentDiv) {
    const { t, BACKEND_URL } = window.ConfigModule;
    const { speakText, stopTTS, getActiveTtsButton } = window.TTSModule || {};
    
    const copyBtn = messageDiv.querySelector('.copy-btn');
    const shareBtn = messageDiv.querySelector('.share-btn');
    const likeBtn = messageDiv.querySelector('.like-btn');
    const dislikeBtn = messageDiv.querySelector('.dislike-btn');
    const ttsBtn = messageDiv.querySelector('.tts-btn');

    // Set translated titles
    if (ttsBtn) ttsBtn.title = t('messages.listen') || 'Listen';
    if (copyBtn) copyBtn.title = t('messages.copy');
    if (shareBtn) shareBtn.title = t('messages.share');

    // TTS button
    if (ttsBtn && speakText && stopTTS && getActiveTtsButton) {
        ttsBtn.addEventListener('click', () => {
            if (getActiveTtsButton() === ttsBtn) {
                stopTTS();
                return;
            }
            
            let textToSpeak;
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
            const questionId = likeBtn.dataset.questionId;
            if (!questionId) {
                console.log('Like button clicked but no question_id available');
                return;
            }
            likeBtn.style.background = '#49fc49ff';
            if (dislikeBtn) dislikeBtn.style.background = '#f9e6e6';
            
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
            const questionId = dislikeBtn.dataset.questionId;
            if (!questionId) {
                console.log('Dislike button clicked but no question_id available');
                return;
            }
            dislikeBtn.style.background = '#ff8686';
            if (likeBtn) likeBtn.style.background = '#e6f9e6';
            
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

    // Copy button
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(contentDiv.textContent);
        });
    }

    // Share button
    if (shareBtn) {
        shareBtn.addEventListener('click', () => {
            if (navigator.share) {
                navigator.share({ text: contentDiv.textContent });
            } else {
                alert(t('messages.shareNotSupported'));
            }
        });
    }
}

/**
 * Remove previous bottom spacer
 */
function removePreviousSpacer() {
    const previousSpacer = document.getElementById('chat-bottom-spacer');
    if (previousSpacer && previousSpacer.parentNode) {
        previousSpacer.remove();
    }
}

/**
 * Create bottom spacer
 */
function createBottomSpacer(userMsgDiv, assistantMsgDiv, offset = 10) {
    const bottomSpacer = document.createElement('div');
    bottomSpacer.id = 'chat-bottom-spacer';
    bottomSpacer.style.height = offset + 'px';
    bottomSpacer.style.flexShrink = '0';
    return bottomSpacer;
}

/**
 * Scroll to message bottom
 */
function scrollToMessageBottom(assistantMsgDiv, offset = 0) {
    const chatContainer = document.getElementById('chat-container');
    if (!chatContainer) return;
    
    const targetTop = assistantMsgDiv.offsetTop + assistantMsgDiv.offsetHeight - chatContainer.clientHeight + offset;
    if (targetTop > 0) {
        chatContainer.scrollTop = targetTop;
    }
}

/**
 * Prepare UI for loading
 */
function prepareUIForLoading() {
    isLoading = true;
    const sendButton = document.getElementById('send-button');
    const inputBox = document.getElementById('input-box');
    const voiceButton = document.getElementById('voice-button');
    
    if (sendButton) sendButton.disabled = true;
    if (inputBox) inputBox.disabled = true;
    if (voiceButton) voiceButton.disabled = true;
}

/**
 * Cleanup after message
 */
function cleanupAfterMessage(messageDiv) {
    isLoading = false;
    const sendButton = document.getElementById('send-button');
    const inputBox = document.getElementById('input-box');
    const voiceButton = document.getElementById('voice-button');
    
    if (sendButton) sendButton.disabled = false;
    if (inputBox) inputBox.disabled = false;
    if (voiceButton) voiceButton.disabled = false;
    
    const { updateScrollIndicator } = window.UIUtilsModule || {};
    if (updateScrollIndicator) updateScrollIndicator();
}

/**
 * Display links/PMIDs
 */
function displayLinks(container, links) {
    if (!links || links.length === 0) return;
    
    const refsDiv = document.createElement('div');
    refsDiv.className = 'link-refs';
    refsDiv.innerHTML = `<strong>Références :</strong> ` +
        links.map(link => {
            const url = `https://google.com/search?q=${link}`;
            return `<a href="${url}" target="_blank" rel="noopener">${link}</a>`;
        }).join(', ');
    container.appendChild(refsDiv);
}

/**
 * Handle streaming response
 */
async function handleStreamingResponse(question, contentDiv, actionsDiv) {
    const { BACKEND_URL, getCurrentLanguage } = window.ConfigModule;
    const { updateScrollIndicator } = window.UIUtilsModule || {};
    
    const requestData = {
        question: question,
        language: getCurrentLanguage(),
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
        locale: navigator.language || (getCurrentLanguage() === 'en' ? 'en-US' : 'fr-FR'),
        session_id: sessionId
    };

    const response = await fetch(`${BACKEND_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let questionId = null;
    let fullText = '';
    let linksReceived = null;

    while (true) {
        const { done, value } = await reader.read();

        if (done) {
            actionsDiv.style.display = '';
            if (questionId) {
                const likeBtn = actionsDiv.querySelector('.like-btn');
                const dislikeBtn = actionsDiv.querySelector('.dislike-btn');
                if (likeBtn) likeBtn.dataset.questionId = questionId;
                if (dislikeBtn) dislikeBtn.dataset.questionId = questionId;
            }
            if (typeof marked !== 'undefined') {
                contentDiv.innerHTML = marked.parse(fullText);
            } else {
                contentDiv.textContent = fullText;
            }
            if (linksReceived !== null) {
                displayLinks(contentDiv, linksReceived);
            }
            return { fullText };
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

                    if (data.session_id && !sessionId) {
                        sessionId = data.session_id;
                        window.sessionId = sessionId;
                        console.log('Session ID received:', sessionId);
                    }
                    
                    if (data.question_id && !questionId) {
                        questionId = data.question_id;
                        window.questionId = questionId;
                    }

                    if (data.links !== undefined) {
                        linksReceived = data.links;
                        console.log('Links received via stream:', linksReceived);
                    }

                    if (data.chunk) {
                        fullText += data.chunk;
                        if (typeof marked !== 'undefined') {
                            contentDiv.innerHTML = marked.parse(fullText);
                        } else {
                            contentDiv.textContent = fullText;
                        }
                        scrollToMessageBottom(contentDiv.closest('.message'));
                    }
                  
                    if (updateScrollIndicator) updateScrollIndicator();
                } catch (parseError) {
                    console.error('JSON parsing error:', parseError);
                }
            }
        }
    }
}

/**
 * Main send message function
 */
async function sendMessage() {
    const inputBox = document.getElementById('input-box');
    const emptyState = document.getElementById('empty-state');
    const chatContainer = document.getElementById('chat-container');
    
    // Check if we're in translator mode
    if (window.AgentsModule && window.AgentsModule.getCurrentAgent() === 'translator') {
        if (window.AgentsModule.sendTranslation) {
            return window.AgentsModule.sendTranslation();
        }
    }
    
    const question = inputBox ? inputBox.value.trim() : '';
    if (!question || isLoading) return;
    
    // Stop voice recording
    if (window.VoiceRecognitionModule && window.VoiceRecognitionModule.stopRecording) {
        window.VoiceRecognitionModule.stopRecording();
    }
    
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    
    removePreviousSpacer();
    
    userMessageDiv = addMessage(question, 'user');
    const messageDiv = createAssistantMessage();
    
    if (chatContainer) {
        chatContainer.appendChild(userMessageDiv);
        chatContainer.appendChild(messageDiv);
    }
    
    const spacerDiv = createBottomSpacer(userMessageDiv, messageDiv);
    if (chatContainer) {
        chatContainer.appendChild(spacerDiv);
    }

    const contentDiv = messageDiv.querySelector('.message-text');
    const actionsDiv = messageDiv.querySelector('.message-actions');
    
    setupMessageActions(messageDiv, contentDiv);
    prepareUIForLoading();
    scrollToMessageBottom(contentDiv.closest('.message'));

    try {
        await handleStreamingResponse(question, contentDiv, actionsDiv);
    } catch (error) {
        console.error('Message sending error:', error);
        const { t } = window.ConfigModule;
        contentDiv.textContent = t('messages.error');
    } finally {
        cleanupAfterMessage(messageDiv);
        const { handleFocus } = window.UIUtilsModule || {};
        if (handleFocus) handleFocus();
        scrollToMessageBottom(contentDiv.closest('.message'));
    }
}

/**
 * Get loading state
 */
function isMessageLoading() {
    return isLoading;
}

// Export for use in other modules
window.ChatModule = {
    sendMessage,
    createAssistantMessage,
    setupMessageActions,
    addMessage,
    removePreviousSpacer,
    createBottomSpacer,
    scrollToMessageBottom,
    prepareUIForLoading,
    cleanupAfterMessage,
    handleStreamingResponse,
    isMessageLoading
};
