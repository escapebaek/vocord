// static/js/ws.js — WebSocket 클라이언트

let ws = null;
let onMessageCallback = null;

function connectWebSocket(roomId, token, onMessage) {
    onMessageCallback = onMessage;

    // 기존 연결이 있으면 먼저 닫기
    if (ws) {
        ws.close();
        ws = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${roomId}?token=${token}`;
    console.log('🔌 WebSocket 연결 시도:', wsUrl.substring(0, 60) + '...');

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('✅ WebSocket 연결 성공!');
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            console.log('📩 수신:', msg);
            if (msg.type === 'error') {
                console.error('서버 오류:', msg.text);
                return;
            }
            if (onMessageCallback) {
                onMessageCallback(msg);
            }
        } catch (err) {
            console.error('메시지 파싱 오류:', err);
        }
    };

    ws.onclose = (event) => {
        console.log('🔌 WebSocket 연결 해제:', event.code, event.reason || '(이유 없음)');
    };

    ws.onerror = (error) => {
        console.error('❌ WebSocket 오류:', error);
    };
}

function sendWSMessage(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
        console.log('📤 전송:', message);
    } else {
        console.warn('⚠️ WebSocket이 연결되어 있지 않습니다. readyState:', ws?.readyState);
    }
}

function disconnectWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }
}
