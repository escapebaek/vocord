// static/js/auth.js — 로그인/회원가입 로직

let currentMode = 'login'; // 'login' or 'register'

function switchTab(mode) {
    currentMode = mode;
    document.getElementById('login-tab').classList.toggle('active', mode === 'login');
    document.getElementById('register-tab').classList.toggle('active', mode === 'register');
    document.getElementById('auth-submit-btn').textContent = mode === 'login' ? '로그인' : '회원가입';
    document.getElementById('auth-error').textContent = '';
}

async function handleAuth(event) {
    event.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('auth-error');
    errorEl.textContent = '';

    if (!username || !password) {
        errorEl.textContent = '사용자 이름과 비밀번호를 입력해주세요.';
        return;
    }

    const endpoint = currentMode === 'login' ? '/api/auth/login' : '/api/auth/register';

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            errorEl.textContent = data.detail || '오류가 발생했습니다.';
            return;
        }

        if (currentMode === 'register') {
            // 회원가입 성공 → 로그인 탭으로 전환
            errorEl.style.color = 'var(--success)';
            errorEl.textContent = '✅ 회원가입 성공! 로그인해주세요.';
            switchTab('login');
            return;
        }

        // 로그인 성공
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('username', username);

        // 로비로 이동
        showScreen('lobby-screen');
        initLobby();

        // API Key 확인
        if (!localStorage.getItem('gemini_api_key')) {
            document.getElementById('api-key-modal').style.display = 'flex';
        }

    } catch (err) {
        errorEl.textContent = '서버 연결에 실패했습니다.';
        console.error(err);
    }
}

function getToken() {
    return localStorage.getItem('access_token');
}

function getUsername() {
    return localStorage.getItem('username');
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    showScreen('auth-screen');
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function saveApiKey() {
    const key = document.getElementById('gemini-api-key-input').value.trim();
    if (key) {
        localStorage.setItem('gemini_api_key', key);
        alert('✅ API Key가 저장되었습니다.');
    }
    closeApiKeyModal();
}

function openApiKeyModal() {
    const existingKey = localStorage.getItem('gemini_api_key') || '';
    document.getElementById('gemini-api-key-input').value = existingKey;
    document.getElementById('api-key-modal').style.display = 'flex';
}

function closeApiKeyModal() {
    document.getElementById('api-key-modal').style.display = 'none';
}

// 페이지 로드 시 저장된 토큰 확인
window.addEventListener('DOMContentLoaded', () => {
    const token = getToken();
    if (token) {
        // 토큰이 유효한지 확인
        fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        }).then(res => {
            if (res.ok) {
                showScreen('lobby-screen');
                initLobby();
            } else {
                localStorage.removeItem('access_token');
            }
        }).catch(() => {});
    }
});

// ─── 마이페이지 ───
let myPageStatus = 'online';

async function openMyPage() {
    document.getElementById('mypage-username').textContent = getUsername();
    document.getElementById('current-pw').value = '';
    document.getElementById('new-pw').value = '';
    document.getElementById('new-pw-confirm').value = '';
    document.getElementById('pw-change-msg').textContent = '';
    document.getElementById('pw-change-msg').style.color = '';
    document.getElementById('profile-img-msg').textContent = '';
    document.getElementById('mypage-modal').style.display = 'flex';

    // 프로필 정보 불러오기
    try {
        const res = await fetch('/api/users/profile', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            const profile = await res.json();
            myPageStatus = profile.user_status || 'online';
            updateStatusBtn(myPageStatus);

            const imgEl = document.getElementById('mypage-avatar-img');
            const defaultEl = document.getElementById('mypage-avatar-default');
            if (profile.profile_image) {
                imgEl.src = profile.profile_image + '?t=' + Date.now();
                imgEl.style.display = 'block';
                defaultEl.style.display = 'none';
            } else {
                imgEl.style.display = 'none';
                defaultEl.style.display = 'flex';
                defaultEl.textContent = getUsername()[0].toUpperCase();
            }
        }
    } catch (e) {
        console.error('프로필 불러오기 실패:', e);
    }
}

function updateStatusBtn(status) {
    const btn = document.getElementById('status-toggle-btn');
    if (status === 'away') {
        btn.textContent = '🟡 자리 비움';
        btn.style.background = 'var(--warning, #f59e0b)';
    } else {
        btn.textContent = '🟢 온라인';
        btn.style.background = 'var(--success, #22c55e)';
    }
}

async function toggleStatus() {
    try {
        const res = await fetch('/api/users/status', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            const data = await res.json();
            myPageStatus = data.status;
            updateStatusBtn(myPageStatus);
        }
    } catch (e) {
        console.error('상태 변경 실패:', e);
    }
}

async function uploadProfileImage(input) {
    const file = input.files[0];
    if (!file) return;

    const msgEl = document.getElementById('profile-img-msg');
    msgEl.style.color = 'var(--text-muted)';
    msgEl.textContent = '업로드 중...';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/users/profile-image', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` },
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            msgEl.style.color = 'var(--success, #22c55e)';
            msgEl.textContent = '✅ ' + data.message;

            // 미리보기 업데이트
            const imgEl = document.getElementById('mypage-avatar-img');
            const defaultEl = document.getElementById('mypage-avatar-default');
            imgEl.src = data.profile_image + '?t=' + Date.now();
            imgEl.style.display = 'block';
            defaultEl.style.display = 'none';
        } else {
            msgEl.style.color = 'var(--danger)';
            msgEl.textContent = data.detail || '업로드 실패';
        }
    } catch (e) {
        msgEl.style.color = 'var(--danger)';
        msgEl.textContent = '서버 연결 실패';
    }

    // 파일 입력 초기화 (같은 파일 재업로드 가능하게)
    input.value = '';
}

function closeMyPage() {
    document.getElementById('mypage-modal').style.display = 'none';
}

async function changePassword() {
    const currentPw = document.getElementById('current-pw').value;
    const newPw = document.getElementById('new-pw').value;
    const confirmPw = document.getElementById('new-pw-confirm').value;
    const msgEl = document.getElementById('pw-change-msg');

    msgEl.style.color = 'var(--danger)';

    if (!currentPw || !newPw || !confirmPw) {
        msgEl.textContent = '모든 필드를 입력해주세요.';
        return;
    }

    if (newPw.length < 4) {
        msgEl.textContent = '새 비밀번호는 4자 이상이어야 합니다.';
        return;
    }

    if (newPw !== confirmPw) {
        msgEl.textContent = '새 비밀번호가 일치하지 않습니다.';
        return;
    }

    try {
        const res = await fetch('/api/auth/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({
                current_password: currentPw,
                new_password: newPw
            })
        });

        const data = await res.json();

        if (res.ok) {
            msgEl.style.color = 'var(--success)';
            msgEl.textContent = '✅ ' + data.message;
            document.getElementById('current-pw').value = '';
            document.getElementById('new-pw').value = '';
            document.getElementById('new-pw-confirm').value = '';
        } else {
            msgEl.textContent = data.detail || '오류가 발생했습니다.';
        }
    } catch (err) {
        msgEl.textContent = '서버 연결에 실패했습니다.';
        console.error(err);
    }
}
