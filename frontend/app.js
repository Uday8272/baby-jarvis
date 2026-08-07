// ── Pre-load voices for TTS ─────────────────────
if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

// ── State ───────────────────────────────────────
const sessionId = Math.random().toString(36).substring(2, 15);
let isProcessing = false;
let voiceEnabled = false;
let recognition = null;
let isListening = false;

// ── Auth State ──────────────────────────────────
const TOKEN_KEY = 'jarvis_token';

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function saveToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

// ── Show/Hide overlay ───────────────────────────
function showLoginOverlay() {
    const overlay = document.getElementById('loginOverlay');
    overlay.style.display = 'flex';
    overlay.classList.remove('hidden');
}

function hideLoginOverlay() {
    const overlay = document.getElementById('loginOverlay');
    overlay.classList.add('hidden');
    setTimeout(() => { overlay.style.display = 'none'; }, 400);
}

// ── Login form submit ───────────────────────────
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const errorBox = document.getElementById('loginError');
    const btn = document.getElementById('loginBtn');
    const btnText = document.getElementById('loginBtnText');

    errorBox.style.display = 'none';
    btn.disabled = true;
    btnText.textContent = 'Authenticating...';

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch('/auth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        if (res.ok) {
            const data = await res.json();
            saveToken(data.access_token);
            hideLoginOverlay();
        } else {
            errorBox.textContent = '❌ Invalid username or password.';
            errorBox.style.display = 'block';
        }
    } catch (err) {
        errorBox.textContent = '❌ Could not reach the server.';
        errorBox.style.display = 'block';
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Access System';
    }
});

// ── On page load: check if already logged in ────
(function checkAuth() {
    if (getToken()) {
        hideLoginOverlay();
    } else {
        showLoginOverlay();
    }
})();

// ── Logout ──────────────────────────────────────
function logout() {
    clearToken();
    showLoginOverlay();
}

// ── Voice & Speech Setup ────────────────────────
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        isListening = true;
        const micBtn = document.getElementById('micBtn');
        micBtn.classList.add('listening');
        document.getElementById('queryInput').placeholder = "Listening...";
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('queryInput').value = transcript;
        sendMessage();
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error", event.error);
        stopMic();
    };

    recognition.onend = () => {
        stopMic();
    };
} else {
    setTimeout(() => {
        const micBtn = document.getElementById('micBtn');
        if (micBtn) micBtn.style.display = 'none';
    }, 0);
}

function toggleMic() {
    if (!recognition) return;
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function stopMic() {
    isListening = false;
    const micBtn = document.getElementById('micBtn');
    if (micBtn) micBtn.classList.remove('listening');
    document.getElementById('queryInput').placeholder = "Ask Jarvis anything... (system commands, file ops, web search, etc.)";
}

function toggleVoice() {
    voiceEnabled = !voiceEnabled;
    const btn = document.getElementById('voiceToggle');
    if (voiceEnabled) {
        btn.classList.add('active');
        btn.textContent = '🔊 Voice: ON';
    } else {
        btn.classList.remove('active');
        btn.textContent = '🔊 Voice: OFF';
        window.speechSynthesis.cancel();
    }
}

function stripMarkdown(text) {
    return text
        .replace(/(\*\*|__)(.*?)\1/g, '$2')
        .replace(/(\*|_)(.*?)\1/g, '$2')
        .replace(/~~(.*?)~~/g, '$1')
        .replace(/`{1,3}(.*?)`{1,3}/g, '$1')
        .replace(/\[(.*?)\]\(.*?\)/g, '$1')
        .replace(/#+\s+(.*)/g, '$1')
        .replace(/>\s+(.*)/g, '$1')
        .replace(/[-*+]\s+/g, '')
        .replace(/\n+/g, ' ');
}

function speakText(text) {
    if (!voiceEnabled || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const cleanText = stripMarkdown(text);
    const utterance = new SpeechSynthesisUtterance(cleanText);
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(v => v.name.includes('Google UK English Male') || v.name.includes('Microsoft Mark') || v.name.includes('English'));
    if (preferredVoice) utterance.voice = preferredVoice;
    utterance.rate = 1.05;
    window.speechSynthesis.speak(utterance);
}

// ── Enter to send ───────────────────────────────
document.getElementById('queryInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ── Quick action buttons ────────────────────────
function sendQuick(text) {
    document.getElementById('queryInput').value = text;
    sendMessage();
}

// ── Send message ────────────────────────────────
async function sendMessage() {
    const input = document.getElementById('queryInput');
    const query = input.value.trim();
    if (!query || isProcessing) return;

    isProcessing = true;
    input.value = '';
    document.getElementById('sendBtn').disabled = true;

    const welcome = document.getElementById('welcomeScreen');
    if (welcome) welcome.remove();

    addMessage('user', query);
    const thinkingId = showThinking();

    try {
        const token = getToken();
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ query: query, session_id: sessionId })
        });

        if (response.status === 401) {
            clearToken();
            removeThinking(thinkingId);
            addMessage('jarvis', '🔒 Session expired. Please log in again.');
            showLoginOverlay();
            return;
        }

        const data = await response.json();
        removeThinking(thinkingId);
        addMessage('jarvis', data.result);
        speakText(data.result);

    } catch (error) {
        removeThinking(thinkingId);
        addMessage('jarvis', '❌ Connection error — is the server running?');
    } finally {
        isProcessing = false;
        document.getElementById('sendBtn').disabled = false;
        input.focus();
    }
}

// ── Add message to chat ─────────────────────────
function addMessage(role, content) {
    const container = document.getElementById('chatContainer');
    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'jarvis' ? 'J' : '🧑';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (role === 'jarvis') {
        bubble.innerHTML = '<div class="prose">' + marked.parse(content || '') + '</div>';
    } else {
        bubble.textContent = content;
    }

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

// ── Thinking indicator ──────────────────────────
function showThinking() {
    const container = document.getElementById('chatContainer');
    const id = 'thinking-' + Date.now();

    const thinking = document.createElement('div');
    thinking.className = 'thinking';
    thinking.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.style.background = 'linear-gradient(135deg, var(--accent-blue), var(--accent-purple))';
    avatar.style.boxShadow = '0 0 12px var(--glow-blue)';
    avatar.textContent = 'J';

    const dots = document.createElement('div');
    dots.className = 'thinking-dots';
    dots.innerHTML = '<span></span><span></span><span></span>';

    thinking.appendChild(avatar);
    thinking.appendChild(dots);
    container.appendChild(thinking);
    container.scrollTop = container.scrollHeight;

    return id;
}

function removeThinking(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
