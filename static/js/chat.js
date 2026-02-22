// static/js/chat.js — 채팅방 + PTT (Push-to-Talk)

let currentRoomId = null;
let recorder = null;
let isRecording = false;
let userProfiles = {}; // { username: profile_image_url }

// PTT 키 설정 (기본값: 'm', localStorage에서 불러오기)
let pttKey = localStorage.getItem('ptt_key') || 'm';
let isSettingPTTKey = false;

function getPTTKeyDisplay() {
    const specialKeys = {
        ' ': 'Space',
        'control': 'Ctrl',
        'alt': 'Alt',
        'shift': 'Shift',
        'capslock': 'CapsLock',
        'tab': 'Tab',
        'escape': 'Esc',
        'arrowup': '↑',
        'arrowdown': '↓',
        'arrowleft': '←',
        'arrowright': '→',
    };
    return specialKeys[pttKey.toLowerCase()] || pttKey.toUpperCase();
}

async function initChat(roomId, roomName) {
    currentRoomId = roomId;
    document.getElementById('chat-room-name').textContent = `# ${roomName}`;
    document.getElementById('chat-messages').innerHTML = `
        <div class="welcome-msg">
            <p>🎙️ <strong>${getPTTKeyDisplay()} 키</strong>를 누른 상태로 말하세요. 놓으면 텍스트로 변환됩니다.</p>
        </div>
    `;
    document.getElementById('chat-online-users').innerHTML = '';
    userProfiles = {}; // 프로필 캐시 초기화

    // 내 프로필 이미지 불러오기
    try {
        const res = await fetch('/api/users/profile', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            const profile = await res.json();
            userProfiles[getUsername()] = profile.profile_image;
        }
    } catch (e) {}

    setPTTStatus('ready');

    // 녹음기 초기화
    recorder = new AudioRecorder();
    try {
        await recorder.init();
    } catch (err) {
        console.error('녹음기 초기화 실패:', err);
    }

    // WebSocket 연결
    connectWebSocket(roomId, getToken(), handleWSMessage);

    // PTT 키 이벤트 등록
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
}

function handleWSMessage(msg) {
    switch (msg.type) {
        case 'message':
            // 프로필 이미지 캐싱
            if (msg.profile_image) {
                userProfiles[msg.username] = msg.profile_image;
            }
            addMessage(msg.username, msg.text, 'received');
            break;
        case 'system':
            addSystemMessage(msg.text);
            break;
        case 'user_list':
            // 프로필 캐시 업데이트
            if (msg.user_profiles) {
                msg.user_profiles.forEach(p => {
                    if (p.profile_image) userProfiles[p.username] = p.profile_image;
                });
            }
            updateOnlineUsers(msg.users);
            break;
        case 'recording':
            showRecordingIndicator(msg.username, msg.is_recording);
            break;
    }
}

// ─── 메시지 표시 ───
function addMessage(username, text, type) {
    const messagesDiv = document.getElementById('chat-messages');
    const now = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    const profileImg = userProfiles[username];
    const avatarHtml = profileImg
        ? `<img src="${profileImg}" class="msg-avatar" alt="${username}">`
        : `<div class="msg-avatar msg-avatar-default">${username[0].toUpperCase()}</div>`;

    const msgEl = document.createElement('div');
    msgEl.className = `message ${type}`;

    msgEl.innerHTML = `
        ${avatarHtml}
        <div class="msg-body">
            <div class="msg-username">${username}</div>
            <div class="msg-text">${escapeHtml(text)}</div>
            <div class="msg-time">${now}</div>
        </div>
    `;

    messagesDiv.appendChild(msgEl);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addSystemMessage(text) {
    const messagesDiv = document.getElementById('chat-messages');
    const msgEl = document.createElement('div');
    msgEl.className = 'message system';
    msgEl.textContent = text;
    messagesDiv.appendChild(msgEl);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ─── 접속자 목록 ───
function updateOnlineUsers(userList) {
    const container = document.getElementById('chat-online-users');
    document.getElementById('chat-member-count').textContent = `${userList.length}명`;
    container.innerHTML = userList.map(u => {
        const profileImg = userProfiles[u];
        const avatarHtml = profileImg
            ? `<img src="${profileImg}" class="online-user-avatar" alt="${u}">`
            : `<div class="online-user-avatar online-user-avatar-default">${u[0].toUpperCase()}</div>`;
        return `<div class="online-user">${avatarHtml} ${u}</div>`;
    }).join('');
}

// ─── 녹음 상태 표시 ───
function showRecordingIndicator(username, isRec) {
    const existingIndicator = document.getElementById(`rec-${username}`);

    if (isRec) {
        if (!existingIndicator) {
            const messagesDiv = document.getElementById('chat-messages');
            const indicator = document.createElement('div');
            indicator.id = `rec-${username}`;
            indicator.className = 'recording-indicator';
            indicator.innerHTML = `<span class="recording-dot"></span> ${username}님이 말하고 있습니다...`;
            messagesDiv.appendChild(indicator);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    } else {
        if (existingIndicator) {
            existingIndicator.remove();
        }
    }
}

// ─── PTT (Push-to-Talk) ───
function matchesPTTKey(key) {
    return key.toLowerCase() === pttKey.toLowerCase();
}

function handleKeyDown(e) {
    // PTT 키 설정 모드일 때
    if (isSettingPTTKey) return;
    // 입력 필드에 포커스가 있으면 무시
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    // 채팅 화면에 있을 때만
    if (!document.getElementById('chat-screen').classList.contains('active')) return;

    if (matchesPTTKey(e.key)) {
        e.preventDefault();
        if (!e.repeat && !isRecording && recorder) {
            isRecording = true;
            recorder.start();
            setPTTStatus('recording');

            // 녹음 중 상태 다른 유저에게 전송
            sendWSMessage({ type: 'recording', is_recording: true });
        }
    }
}

async function handleKeyUp(e) {
    if (isSettingPTTKey) return;
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    if (matchesPTTKey(e.key) && isRecording && recorder) {
        isRecording = false;
        setPTTStatus('processing');

        // 녹음 중 상태 해제
        sendWSMessage({ type: 'recording', is_recording: false });

        try {
            const blob = await recorder.stop();
            if (!blob || blob.size < 1000) {
                // 너무 짧은 녹음은 무시
                setPTTStatus('ready');
                return;
            }

            // Gemini STT 호출
            const text = await transcribeAudio(blob);

            if (text && text.trim()) {
                // 내 화면에 먼저 표시
                addMessage(getUsername(), text, 'sent');

                // 서버로 전송
                sendWSMessage({
                    type: 'message',
                    text: text
                });
            }
        } catch (err) {
            console.error('STT 처리 오류:', err);
            addSystemMessage('⚠️ 음성 변환에 실패했습니다.');
        }

        setPTTStatus('ready');
    }
}

function setPTTStatus(status) {
    const indicator = document.getElementById('ptt-indicator');
    const statusEl = document.getElementById('ptt-status');
    const iconEl = document.getElementById('ptt-icon');
    const textEl = document.getElementById('ptt-text');

    indicator.className = 'ptt-indicator ' + status;
    statusEl.className = 'ptt-status ' + status;

    const keyDisplay = getPTTKeyDisplay();

    switch (status) {
        case 'ready':
            iconEl.textContent = '🎤';
            textEl.textContent = `${keyDisplay} 키를 누르고 말하세요`;
            statusEl.textContent = 'Ready';
            break;
        case 'recording':
            iconEl.textContent = '🔴';
            textEl.textContent = '녹음 중...';
            statusEl.textContent = '🔴 Recording';
            break;
        case 'processing':
            iconEl.textContent = '⏳';
            textEl.textContent = '변환 중...';
            statusEl.textContent = '변환 중...';
            break;
    }
}

// ─── PTT 키 변경 ───
function openPTTKeySettings() {
    const modal = document.getElementById('ptt-key-modal');
    document.getElementById('current-ptt-key-display').textContent = getPTTKeyDisplay();
    document.getElementById('new-ptt-key-display').textContent = '아무 키나 누르세요...';
    modal.style.display = 'flex';
    isSettingPTTKey = true;

    // 키 입력 대기
    const keyHandler = (e) => {
        e.preventDefault();
        e.stopPropagation();

        // Escape는 취소
        if (e.key === 'Escape') {
            closePTTKeyModal();
            document.removeEventListener('keydown', keyHandler, true);
            return;
        }

        // Enter는 무시 (실수 방지)
        if (e.key === 'Enter') return;

        const newKey = e.key;
        document.getElementById('new-ptt-key-display').textContent =
            getPTTKeyDisplayForKey(newKey);
        document.getElementById('new-ptt-key-display').dataset.key = newKey;
    };

    document.addEventListener('keydown', keyHandler, true);
    // modal에 핸들러 저장해서 나중에 해제
    modal._keyHandler = keyHandler;
}

function getPTTKeyDisplayForKey(key) {
    const specialKeys = {
        ' ': 'Space',
        'Control': 'Ctrl',
        'Alt': 'Alt',
        'Shift': 'Shift',
        'CapsLock': 'CapsLock',
        'Tab': 'Tab',
        'Escape': 'Esc',
        'ArrowUp': '↑',
        'ArrowDown': '↓',
        'ArrowLeft': '←',
        'ArrowRight': '→',
    };
    return specialKeys[key] || key.toUpperCase();
}

function savePTTKey() {
    const newKeyEl = document.getElementById('new-ptt-key-display');
    const newKey = newKeyEl.dataset.key;
    if (newKey) {
        pttKey = newKey;
        localStorage.setItem('ptt_key', pttKey);
        setPTTStatus('ready');
        // 환영 메시지 업데이트
        const welcomeMsg = document.querySelector('.welcome-msg p');
        if (welcomeMsg) {
            welcomeMsg.innerHTML = `🎙️ <strong>${getPTTKeyDisplay()} 키</strong>를 누른 상태로 말하세요. 놓으면 텍스트로 변환됩니다.`;
        }
    }
    closePTTKeyModal();
}

function closePTTKeyModal() {
    const modal = document.getElementById('ptt-key-modal');
    if (modal._keyHandler) {
        document.removeEventListener('keydown', modal._keyHandler, true);
        modal._keyHandler = null;
    }
    modal.style.display = 'none';
    isSettingPTTKey = false;
}

// ─── 텍스트 직접 입력 ───
function handleTextInput(event) {
    if (event.key === 'Enter') {
        sendTextMessage();
    }
}

function sendTextMessage() {
    const input = document.getElementById('text-message-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(getUsername(), text, 'sent');
    sendWSMessage({ type: 'message', text });
    input.value = '';
}

// ─── 채팅방 나가기 ───
async function leaveChat() {
    // PTT 이벤트 해제
    document.removeEventListener('keydown', handleKeyDown);
    document.removeEventListener('keyup', handleKeyUp);

    // WebSocket 해제
    disconnectWebSocket();

    // 녹음기 해제
    if (recorder) {
        recorder.destroy();
        recorder = null;
    }

    // 로비로 복귀
    showScreen('lobby-screen');
    initLobby();
}

// ─── 유틸 ───
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
