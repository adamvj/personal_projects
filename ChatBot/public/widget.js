document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const toggleBtn = document.getElementById('md-chat-toggle-btn');
    const chatWindow = document.getElementById('md-chat-window');
    const closeBtn = document.getElementById('md-chat-close-btn');
    const chatForm = document.getElementById('md-chat-form');
    const chatInput = document.getElementById('md-chat-input');
    const messagesContainer = document.getElementById('md-chat-messages');
    const sendBtn = document.getElementById('md-chat-send-btn');
    const micBtn = document.getElementById('md-mic-btn');

    // Floyd Overlay Elements
    const floydOverlay = document.getElementById('floyd-voice-overlay');
    const floydCloseBtn = document.getElementById('floyd-close-btn');
    const floydOrbBtn = document.getElementById('floyd-orb-btn');
    const floydTranscriptText = document.getElementById('floyd-transcript-text');
    const floydStatusText = document.getElementById('floyd-status-text');

    // State
    let conversationHistory = [];
    const API_URL = 'http://localhost:3000/chat'; // Change this when deploying

    // Speech Configuration
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isRecording = false;
    let continuousChatEnabled = false; // Add state for continuous chat
    let voiceModeActive = false; // Indicates if the last input was via voice, triggering a spoken response
    let audioContext = null; // AudioContext for TTS playback

    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('md-mic-recording');
            chatInput.placeholder = "Listening...";

            // Floyd UI updates
            floydOrbBtn.classList.add('is-listening');
            floydStatusText.textContent = "Listening...";
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            floydTranscriptText.textContent = `"${transcript}"`;
            voiceModeActive = true;

            floydOrbBtn.classList.remove('is-listening');
            floydStatusText.textContent = "Thinking...";

            // Auto submit the form once speech is recognized
            chatForm.dispatchEvent(new Event('submit'));
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            // Don't stop continuous mode on no-speech errors, just restart
            if (event.error !== 'no-speech') {
                stopRecording(false);
            }
        };

        recognition.onend = () => {
            isRecording = false;
            micBtn.classList.remove('md-mic-recording');
            chatInput.placeholder = "Type your question...";
            floydOrbBtn.classList.remove('is-listening');

            if (continuousChatEnabled && !window.speechSynthesis.speaking && document.getElementById('md-chat-send-btn').disabled === false) {
                try { recognition.start(); } catch (e) { }
            }
        };
    } else {
        micBtn.style.display = 'none'; // Hide if browser doesn't support it
        floydOrbBtn.style.display = 'none';
        console.warn("Speech Recognition API not supported in this browser.");
    }

    // Modal Toggle Logic
    function openFloydOverlay() {
        // Hide standard chat window but keep the container widget around
        chatWindow.classList.add('md-hidden');
        toggleBtn.classList.remove('is-open');

        // Show Floyd Overlay
        floydOverlay.classList.remove('md-hidden');
    }

    function closeFloydOverlay() {
        floydOverlay.classList.add('md-hidden');
        stopRecording(true);
        if (audioContext && audioContext.state === 'running') {
            audioContext.suspend();
            audioContext = null;
        }
        floydOrbBtn.classList.remove('is-speaking');
        floydOrbBtn.classList.remove('is-listening');
    }

    floydCloseBtn.addEventListener('click', closeFloydOverlay);

    function stopRecording(disableContinuous = true) {
        if (disableContinuous) {
            continuousChatEnabled = false;
        }
        if (isRecording && recognition) {
            try { recognition.stop(); } catch (e) { }
        }
        isRecording = false;
        micBtn.classList.remove('md-mic-recording');
        chatInput.placeholder = "Type your question...";
        floydOrbBtn.classList.remove('is-listening');
    }

    // Connect standard mic button to open the overlay AND start listening
    micBtn.addEventListener('click', () => {
        if (!recognition) return;

        // Ensure AudioContext is initialized/resumed on user click!
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } else if (audioContext.state === 'suspended') {
            audioContext.resume();
        }

        openFloydOverlay();

        continuousChatEnabled = true;
        try {
            recognition.start();
        } catch (e) {
            console.error(e);
        }
    });

    // Also let the big Orb act as a start/stop toggle
    floydOrbBtn.addEventListener('click', () => {
        if (!recognition) return;

        // Ensure AudioContext is initialized/resumed on user click!
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } else if (audioContext.state === 'suspended') {
            audioContext.resume();
        }

        if (continuousChatEnabled) {
            stopRecording(true);
            if (audioContext && audioContext.state === 'running') {
                audioContext.suspend();
            }
            floydOrbBtn.classList.remove('is-speaking');
            floydStatusText.textContent = "Paused";
        } else {
            continuousChatEnabled = true;
            try {
                recognition.start();
            } catch (e) {
                console.error(e);
            }
        }
    });

    // ---- Voice Selection Logic ----
    let currentAudio = null; // Track playing audio object

    async function speakText(text) {
        if (!voiceModeActive) return;

        // Stop any currently playing audio
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }

        // Remove markdown syntax for cleaner speech
        const cleanText = text.replace(/[*_~`#\[\]]/g, '').replace(/https?:\/\/[^\s]+/g, 'a link');

        floydOrbBtn.classList.add('is-speaking');
        floydStatusText.textContent = "Speaking...";

        let isPlayingAudio = false;

        try {
            // Fetch audio from local Python TTS server 
            const response = await fetch('http://localhost:5001/synthesize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: cleanText,
                    voice: 'am_adam',
                    speed: 1.05
                })
            });

            if (!response.body) {
                console.error('ReadableStream not yet supported in this browser.');
                floydOrbBtn.classList.remove('is-speaking');
                return;
            }

            isPlayingAudio = true;
            const reader = response.body.getReader();

            // Re-sync nextStartTime to audioContext.currentTime + slight buffer
            let nextStartTime = audioContext.currentTime + 0.05;
            let leftover = new Uint8Array(0);

            // Stream chunks
            while (isPlayingAudio) {
                const { value, done } = await reader.read();
                if (done) break;

                // Accumulate previous leftover byte(s) with new chunk
                const currentChunk = new Uint8Array(leftover.length + value.length);
                currentChunk.set(leftover);
                currentChunk.set(value, leftover.length);

                // Ensure we only process even amounts of bytes for Int16Array
                const evenLength = currentChunk.length - (currentChunk.length % 2);
                leftover = currentChunk.slice(evenLength);

                const processableBytes = currentChunk.slice(0, evenLength);
                if (processableBytes.length === 0) continue;

                // Kokoro outputs raw 16-bit PCM at 24000Hz.
                const int16Array = new Int16Array(processableBytes.buffer, processableBytes.byteOffset, processableBytes.length / 2);

                // Convert Int16 to Float32 for Web Audio API
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {
                    float32Array[i] = int16Array[i] / 32768.0;
                }

                // Create AudioBuffer
                const audioBuffer = audioContext.createBuffer(1, float32Array.length, 24000);
                audioBuffer.copyToChannel(float32Array, 0);

                // Play Chunk
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);

                // Prevent nextStartTime from falling behind currentTime (prevents stuttering)
                if (nextStartTime < audioContext.currentTime) {
                    nextStartTime = audioContext.currentTime + 0.05;
                }

                // Queue it up right after the last chunk finishes
                source.start(nextStartTime);
                nextStartTime += audioBuffer.duration;
            }

            // Wait for the final audio chunk to finish playing
            const timeToWaitMs = Math.max(0, (nextStartTime - audioContext.currentTime) * 1000);
            setTimeout(() => {
                isPlayingAudio = false;
                floydOrbBtn.classList.remove('is-speaking');
                // If continuous chat was enabled, restart mic
                if (wasContinuous && !isRecording && continuousChatEnabled) {
                    try { recognition.start(); } catch (e) { }
                }
            }, timeToWaitMs);

        } catch (error) {
            console.error('Error contacting TTS server:', error);
            floydOrbBtn.classList.remove('is-speaking');
        }
    }

    // Turn off voice mode if user manually types
    chatInput.addEventListener('input', () => {
        voiceModeActive = false;
        stopRecording(true);
        if (audioContext && audioContext.state === 'running') {
            audioContext.suspend(); // Stop playing immediately
        }
        floydOrbBtn.classList.remove('is-speaking');
        floydOrbBtn.classList.remove('is-listening');
    });

    // Toggle Chat Window
    function toggleChat() {
        const isHidden = chatWindow.classList.contains('md-hidden');
        if (isHidden) {
            chatWindow.classList.remove('md-hidden');
            toggleBtn.classList.add('is-open');
            // Remove pulse after first interaction
            toggleBtn.classList.remove('md-btn-pulse');
            setTimeout(() => chatInput.focus(), 300);
        } else {
            chatWindow.classList.add('md-hidden');
            toggleBtn.classList.remove('is-open');
        }
    }

    toggleBtn.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Escape key closes chat
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !chatWindow.classList.contains('md-hidden')) {
            toggleChat();
        }
    });

    // Formatting simple markdown-like syntax (bold, links)
    function formatMessage(text) {
        // Convert URLs to clickable links
        let formattedText = text.replace(
            /(https?:\/\/[^\s]+)/g,
            '<a href="$1" target="_blank">$1</a>'
        );
        // Convert **bold** to <strong>
        formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Convert *italic* to <em>
        formattedText = formattedText.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Convert newlines to <br>
        formattedText = formattedText.replace(/\n/g, '<br>');

        return formattedText;
    }

    // Add Message to UI
    function appendMessage(content, sender = 'user') {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('md-message', `md-message-${sender}`);

        const contentDiv = document.createElement('div');
        contentDiv.classList.add('md-message-content');

        if (sender === 'user') {
            contentDiv.textContent = content;
        } else {
            contentDiv.innerHTML = formatMessage(content);
        }

        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    // Show/Hide Typing Indicator
    function showTypingIndicator() {
        const indicatorId = 'md-typing-' + Date.now();
        const indicatorHTML = `
            <div id="${indicatorId}" class="md-typing-indicator md-message">
                <div class="md-typing-dot"></div>
                <div class="md-typing-dot"></div>
                <div class="md-typing-dot"></div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', indicatorHTML);
        scrollToBottom();
        return indicatorId;
    }

    function removeTypingIndicator(indicatorId) {
        const indicator = document.getElementById(indicatorId);
        if (indicator) {
            indicator.remove();
        }
    }

    function scrollToBottom() {
        // Add a tiny delay to ensure DOM is updated first
        setTimeout(() => {
            messagesContainer.scrollTo({
                top: messagesContainer.scrollHeight,
                behavior: 'smooth'
            });
        }, 10);
    }

    // Handle Form Submit
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const message = chatInput.value.trim();
        if (!message) return;

        // 1. Add User Message
        appendMessage(message, 'user');
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        // 2. Add to history
        conversationHistory.push({ role: 'user', content: message });

        // 3. Show loading
        const indicatorId = showTypingIndicator();

        try {
            // 4. Call Backend API
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    history: conversationHistory.slice(-10) // Only send last 10 msgs
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            // 5. Remove loading & Add Bot Message
            removeTypingIndicator(indicatorId);
            appendMessage(data.reply, 'bot');

            // Optional: If answering in voice mode, display bot response
            // in the center of the screen
            if (voiceModeActive) {
                floydTranscriptText.innerHTML = `<span class="floyd-transcript-ai">"${formatMessage(data.reply)}"</span>`;
            }

            // 6. Speak the bot message if voice mode is active
            if (voiceModeActive) {
                speakText(data.reply);
            }

            // 7. Update history
            conversationHistory.push({ role: 'model', content: data.reply });

        } catch (error) {
            console.error('Chat error:', error);
            removeTypingIndicator(indicatorId);
            appendMessage('Sorry, I am having trouble connecting to the server right now. Please try again later or reach out directly!', 'bot');
        } finally {
            // Re-enable input
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    // Optional: Auto-open chat after a delay
    // setTimeout(() => {
    //     if (chatWindow.classList.contains('md-hidden')) {
    //         toggleChat();
    //     }
    // }, 5000);
});
