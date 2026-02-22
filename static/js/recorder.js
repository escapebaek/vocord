// static/js/recorder.js — Web Audio 마이크 녹음

class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.chunks = [];
        this.stream = null;
    }

    async init() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            });
            console.log('🎤 마이크 초기화 완료');
        } catch (err) {
            console.error('마이크 접근 실패:', err);
            alert('마이크 접근 권한이 필요합니다. 브라우저 설정에서 마이크를 허용해주세요.');
            throw err;
        }
    }

    start() {
        if (!this.stream) {
            console.error('마이크가 초기화되지 않았습니다.');
            return;
        }
        this.chunks = [];
        this.mediaRecorder = new MediaRecorder(this.stream, {
            mimeType: this.getSupportedMimeType()
        });
        this.mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) {
                this.chunks.push(e.data);
            }
        };
        this.mediaRecorder.start();
        console.log('🔴 녹음 시작');
    }

    stop() {
        return new Promise((resolve) => {
            if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
                resolve(null);
                return;
            }

            this.mediaRecorder.onstop = () => {
                const mimeType = this.mediaRecorder.mimeType;
                const blob = new Blob(this.chunks, { type: mimeType });
                console.log(`⏹️ 녹음 완료 (${(blob.size / 1024).toFixed(1)}KB)`);
                resolve(blob);
            };
            this.mediaRecorder.stop();
        });
    }

    getSupportedMimeType() {
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/mp4',
        ];
        for (const type of types) {
            if (MediaRecorder.isTypeSupported(type)) {
                return type;
            }
        }
        return '';
    }

    destroy() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }
}
