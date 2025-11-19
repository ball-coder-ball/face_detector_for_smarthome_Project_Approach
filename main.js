// Smart Home Face Registration System - Real API Connection
// เชื่อมต่อกับ backend_main.py (FastAPI + DeepFace)

class FaceRegistrationSystem {
    constructor() {
        this.videoStream = null;
        // เปลี่ยน URL นี้เป็นของ ngrok เมื่อคุณจะรันผ่านเน็ต (เช่น 'https://xxxx.ngrok-free.app')
        // แต่ถ้ารันในเครื่องเดียวกันใช้ localhost ได้
        this.apiBaseUrl = 'https://alma-unvirulent-lanita.ngrok-free.dev'; 
    }

    // 1. เปิดกล้อง
    async requestCameraPermission() {
        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({
                video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
            });
            return { success: true, stream: this.videoStream };
        } catch (error) {
            console.error('Camera error:', error);
            return { success: false, error: error.message };
        }
    }

    startVideoStream(videoElement) {
        if (this.videoStream) {
            videoElement.srcObject = this.videoStream;
            videoElement.play();
        }
    }

    stopVideoStream() {
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }
    }

    captureFrame(videoElement) {
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0);
        return canvas.toDataURL('image/jpeg', 0.8);
    }

    // --- ส่วนเชื่อมต่อ API ของจริง ---

    // 2. ตรวจจับ Spoof (ส่ง 5 เฟรมไปให้ Python)
    async simulateSpoofDetection(frames) {
        console.log('📡 Sending frames to check spoof...');
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/spoof-check`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frames: frames })
            });
            return await response.json();
        } catch (e) {
            console.error(e);
            return { is_real: false, message: "Server connection failed" };
        }
    }

    // 3. ส่ง LINE หาเจ้าของบ้าน (Request Permission)
    async simulateLineNotification(userName, frame) {
        console.log(`📡 Requesting permission for ${userName}...`);
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/request-permission`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: userName, image_data: frame })
            });
            return await response.json();
        } catch (e) {
            return { success: false, message: "Connection error" };
        }
    }

    // 4. บันทึกหน้าลง Database (Register)
    async simulateFaceRegistration(userId, images) {
        // ดึงชื่อจาก URL หรือ form ถ้ามี
        const urlParams = new URLSearchParams(window.location.search);
        const userName = urlParams.get('name') || 'Unknown User';

        console.log(`📡 Registering faces for ${userName}...`);
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/register-faces`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    user_id: userId, 
                    name: userName, 
                    images: images 
                })
            });
            return await response.json();
        } catch (e) {
            return { success: false };
        }
    }

    // 5. สแกนหน้าเข้าบ้าน (Scan)
    async simulateFaceScan(imageData) {
        console.log('📡 Scanning face...');
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/scan-face`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_data: imageData })
            });
            return await response.json(); // คืนค่า { is_match: true/false, user: ... }
        } catch (e) {
            console.error(e);
            return { is_match: false, reason: "server_error" };
        }
    }

    // --- Utilities ---
    generateJWT(userId) { return btoa(JSON.stringify({ userId, exp: Date.now() + 86400000 })); }
    verifyJWT(token) { try { return JSON.parse(atob(token)).exp > Date.now(); } catch { return false; } }
    delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
    
    animateElement(element, properties, duration = 500) {
        if (typeof anime !== 'undefined') anime({ targets: element, ...properties, duration, easing: 'easeInOutQuad' });
    }

    showNotification(message, type = 'info') {
        const div = document.createElement('div');
        div.className = 'notification';
        div.style.cssText = `position:fixed;top:20px;right:20px;padding:16px 24px;border-radius:8px;color:white;z-index:1000;background:${type==='success'?'#00ff88':type==='error'?'#ff4444':'#0066ff'}`;
        div.textContent = message;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 3000);
    }
}

const faceSystem = new FaceRegistrationSystem();
window.addEventListener('beforeunload', () => faceSystem.stopVideoStream());