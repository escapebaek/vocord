// static/js/lobby.js — 로비 화면 (친구, 방 관리, 초대)

let refreshInterval = null;
let inviteCheckInterval = null;

async function initLobby() {
    document.getElementById('current-username').textContent = '🟢 ' + getUsername();
    await Promise.all([
        loadFriends(),
        loadPendingRequests(),
        loadRooms()
    ]);

    // 10초마다 자동 새로고침
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(async () => {
        await Promise.all([
            loadFriends(),
            loadPendingRequests(),
            loadRooms()
        ]);
    }, 10000);

    // 3초마다 초대 확인
    if (inviteCheckInterval) clearInterval(inviteCheckInterval);
    inviteCheckInterval = setInterval(checkInvitations, 3000);
    checkInvitations(); // 즉시 1회 실행
}

// ─── 유저 검색 ───
let searchTimeout = null;
async function searchUsers() {
    const query = document.getElementById('user-search').value.trim();
    const resultsDiv = document.getElementById('search-results');

    if (!query) {
        resultsDiv.classList.remove('visible');
        return;
    }

    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        try {
            const res = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            const users = await res.json();

            if (users.length === 0) {
                resultsDiv.innerHTML = '<div class="search-result-item"><span style="color:var(--text-muted)">검색 결과 없음</span></div>';
            } else {
                resultsDiv.innerHTML = users.map(u => `
                    <div class="search-result-item">
                        <span>${u.username} ${u.is_online ? '🟢' : '⚫'}</span>
                        <button class="btn-accept" onclick="sendFriendRequest(${u.id})">친구 추가</button>
                    </div>
                `).join('');
            }
            resultsDiv.classList.add('visible');
        } catch (err) {
            console.error('검색 오류:', err);
        }
    }, 300);
}

// 검색창 바깥 클릭 시 닫기
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-box')) {
        document.getElementById('search-results')?.classList.remove('visible');
    }
});

// ─── 친구 요청 보내기 ───
async function sendFriendRequest(userId) {
    try {
        const res = await fetch(`/api/friends/request/${userId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            document.getElementById('user-search').value = '';
            document.getElementById('search-results').classList.remove('visible');
        } else {
            alert(data.detail);
        }
    } catch (err) {
        console.error('친구 요청 오류:', err);
    }
}

// ─── 친구 요청 수락 ───
async function acceptFriendRequest(requestId) {
    try {
        const res = await fetch(`/api/friends/accept/${requestId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.ok) {
            await loadFriends();
            await loadPendingRequests();
        }
    } catch (err) {
        console.error('수락 오류:', err);
    }
}

// ─── 친구 목록 로드 ───
async function loadFriends() {
    try {
        const res = await fetch('/api/friends', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const friends = await res.json();
        const listDiv = document.getElementById('friends-list');

        if (friends.length === 0) {
            listDiv.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;padding:8px;">친구가 없습니다</p>';
            return;
        }

        listDiv.innerHTML = friends.map(f => {
            const friendUserId = f.other_user_id;
            const friendName = f.friend_username || '알 수 없음';
            return `
                <div class="friend-item" onclick="inviteFriend(${friendUserId}, '${friendName}')" title="클릭하여 ${friendName}님과 대화하기">
                    <div>
                        <div class="friend-name">${friendName}</div>
                        <div class="friend-status-hint">💬 클릭하여 대화</div>
                    </div>
                    <span class="invite-icon">📩</span>
                </div>
            `;
        }).join('');
    } catch (err) {
        console.error('친구 목록 오류:', err);
    }
}

// ─── 받은 친구 요청 로드 ───
async function loadPendingRequests() {
    try {
        const res = await fetch('/api/friends/pending', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const pending = await res.json();

        document.getElementById('pending-count').textContent = pending.length;
        const listDiv = document.getElementById('pending-list');

        if (pending.length === 0) {
            listDiv.innerHTML = '';
            return;
        }

        listDiv.innerHTML = pending.map(p => `
            <div class="pending-item">
                <span class="friend-name">${p.friend_username || '유저 #' + p.user_id}</span>
                <div class="pending-actions">
                    <button class="btn-accept" onclick="acceptFriendRequest(${p.id})">수락</button>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('요청 목록 오류:', err);
    }
}

// ─── 방 목록 로드 ───
async function loadRooms() {
    try {
        const res = await fetch('/api/rooms', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const rooms = await res.json();
        const listDiv = document.getElementById('rooms-list');

        if (rooms.length === 0) {
            listDiv.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;padding:16px;">아직 만들어진 방이 없습니다</p>';
            return;
        }

        listDiv.innerHTML = rooms.map(r => `
            <div class="room-item" onclick="enterRoom(${r.id}, '${r.name.replace(/'/g, "\\'")}')">
                <div class="room-info">
                    <h4># ${r.name}</h4>
                    <span>${r.member_count}명 참가 중</span>
                </div>
                <button class="btn-join" onclick="event.stopPropagation(); enterRoom(${r.id}, '${r.name.replace(/'/g, "\\'")}')">입장</button>
            </div>
        `).join('');
    } catch (err) {
        console.error('방 목록 오류:', err);
    }
}

// ─── 방 생성 ───
async function createRoom() {
    const nameInput = document.getElementById('room-name-input');
    const name = nameInput.value.trim();
    if (!name) return;

    try {
        const res = await fetch('/api/rooms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}`
            },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (res.ok) {
            nameInput.value = '';
            await loadRooms();
        } else {
            alert(data.detail);
        }
    } catch (err) {
        console.error('방 생성 오류:', err);
    }
}

// ─── 친구 초대 (클릭 → 방 생성 + 초대) ───
async function inviteFriend(friendId, friendName) {
    try {
        const res = await fetch(`/api/rooms/invite/${friendId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const data = await res.json();

        if (res.ok) {
            // 초대자는 바로 채팅방으로 이동
            alert(`✅ ${friendName}님에게 초대를 보냈습니다!\n방으로 입장합니다.`);
            enterRoom(data.room_id, data.room_name);
        } else {
            alert(data.detail);
        }
    } catch (err) {
        console.error('초대 오류:', err);
    }
}

// ─── 초대 폴링 & 팝업 ───
let shownInviteIds = new Set(); // 이미 표시한 초대 ID 추적

async function checkInvitations() {
    // 로비 화면이 아니면 건너뛰기
    if (!document.getElementById('lobby-screen').classList.contains('active')) return;

    try {
        const res = await fetch('/api/rooms/invitations', {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const invites = await res.json();

        for (const invite of invites) {
            if (!shownInviteIds.has(invite.id)) {
                shownInviteIds.add(invite.id);
                showInvitePopup(invite);
            }
        }
    } catch (err) {
        // 조용히 무시 (폴링 에러)
    }
}

function showInvitePopup(invite) {
    const popup = document.getElementById('invite-popup');
    document.getElementById('invite-from-user').textContent = invite.from_username;
    document.getElementById('invite-room-name').textContent = invite.room_name;

    // 버튼에 invite id 저장
    document.getElementById('btn-accept-invite').onclick = () => respondToInvite(invite.id, true);
    document.getElementById('btn-decline-invite').onclick = () => respondToInvite(invite.id, false);

    popup.style.display = 'flex';

    // 30초 후 자동 숨기기
    setTimeout(() => {
        if (popup.style.display === 'flex') {
            popup.style.display = 'none';
        }
    }, 30000);
}

async function respondToInvite(inviteId, accept) {
    const popup = document.getElementById('invite-popup');
    popup.style.display = 'none';

    const endpoint = accept
        ? `/api/rooms/invitations/${inviteId}/accept`
        : `/api/rooms/invitations/${inviteId}/decline`;

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        const data = await res.json();

        if (accept && res.ok) {
            // 수락 → 채팅방으로 바로 이동
            enterRoom(data.room_id, data.room_name);
        }
    } catch (err) {
        console.error('초대 응답 오류:', err);
    }
}

// ─── 방 입장 ───
async function enterRoom(roomId, roomName) {
    // 먼저 REST API로 방 입장 (이미 입장한 경우에도 채팅 화면으로 이동)
    try {
        await fetch(`/api/rooms/${roomId}/join`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
    } catch (err) {
        // 이미 참가 중이어도 OK
    }

    // 자동 갱신 중지
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    if (inviteCheckInterval) {
        clearInterval(inviteCheckInterval);
        inviteCheckInterval = null;
    }

    // 채팅 화면으로 전환
    showScreen('chat-screen');
    initChat(roomId, roomName);
}
