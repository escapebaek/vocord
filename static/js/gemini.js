// static/js/gemini.js — Gemini Flash STT

async function transcribeAudio(audioBlob) {
    const apiKey = localStorage.getItem('gemini_api_key');
    if (!apiKey) {
        document.getElementById('api-key-modal').style.display = 'flex';
        throw new Error('Gemini API Key가 설정되지 않았습니다.');
    }

    // Blob을 Base64로 변환
    const base64Data = await blobToBase64(audioBlob);

    // MIME 타입 결정
    const mimeType = audioBlob.type || 'audio/webm';

    const requestBody = {
        contents: [
            {
                parts: [
                    {
                        inline_data: {
                            mime_type: mimeType,
                            data: base64Data
                        }
                    },
                    {
                        text: "이 오디오를 텍스트로 정확히 변환해주세요. 변환된 텍스트만 반환하고, 다른 설명은 하지 마세요. 오디오가 없거나 인식할 수 없으면 빈 문자열을 반환하세요."
                    }
                ]
            }
        ],
        generationConfig: {
            temperature: 0.1,
            maxOutputTokens: 1024
        }
    };

    try {
        const response = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=${apiKey}`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            }
        );

        if (!response.ok) {
            const errData = await response.json();
            console.error('Gemini API 오류:', errData);
            throw new Error(errData.error?.message || 'API 호출 실패');
        }

        const data = await response.json();
        const text = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '';
        return text;
    } catch (err) {
        console.error('STT 오류:', err);
        throw err;
    }
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            // data:audio/webm;base64,XXXX → XXXX 부분만 추출
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}
