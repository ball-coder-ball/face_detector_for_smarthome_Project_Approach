// Smart Home Face Registration System - Main JavaScript
// (MODIFIED VERSION - Connects to REAL FastAPI Backend)

class FaceRegistrationSystem {
    constructor() {
        this.videoStream = null;
        // เราจะไม่เก็บ mockUsers ที่นี่อีกต่อไป Backend จะเป็นคนจัดการ
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    async requestCameraPermission() {
        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 },
                    facingMode: 'user'
                }
            });
            return { success: true, stream: this.videoStream };
        } catch (error) {
            console.error('Camera permission denied:', error);
            return { success: false, error: error.message };
        }
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    startVideoStream(videoElement) {
        if (this.videoStream) {
            videoElement.srcObject = this.videoStream;
            videoElement.play();
        }
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    stopVideoStream() {
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    captureFrame(videoElement) {
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0);
        return canvas.toDataURL('image/jpeg', 0.8);
    }

    // ---------------------------------------------------
    // START: ส่วนที่เปลี่ยนแปลง (เปลี่ยนจาก Simulation เป็น API จริง)
    // ---------------------------------------------------

    // หน้า 2: ตรวจจับ Spoof
    async simulateSpoofDetection(frames) {
        // เราจะส่ง 'frames' (array ของรูปภาพ base64) ไปให้ Backend
        console.log('Sending 5 frames to backend for spoof check...');
        const response = await fetch('http://127.0.0.1:8000/api/v1/spoof-check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ frames: frames })
        });
        return await response.json(); // คืนค่า { is_real: true/false, confidence: 0.xx }
    }

    // หน้า 2: กดปุ่ม "ขออนุมัติ"
    async simulateLineNotification(userName, frame) {
        // ส่งชื่อและรูปภาพ (เฟรมที่ดีที่สุด) ไปให้ Backend เพื่อส่ง LINE
        console.log(`Sending registration request for ${userName}`);
        const response = await fetch('http://127.0.0.1:8000/api/v1/request-permission', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: userName, image_data: frame })
        });
        return await response.json(); // คืนค่า { success: true, user_id: '...' }
    }


    // หน้า 3: บันทึกใบหน้า 20 ภาพ
    async simulateFaceRegistration(userId, userName, faceImages) {
        // ส่ง userId (ที่ได้จาก LINE) และ "ชื่อ" และ "รูปภาพ 20 รูป" ไปให้ Backend
        console.log(`Sending 20 images for ${userName} (ID: ${userId})`);
        const response = await fetch('http://127.0.0.1:8000/api/v1/register-faces', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: userId, 
                name: userName, // ส่งชื่อไปด้วย
                images: faceImages 
            })
        });
        return await response.json(); // คืนค่า { success: true, faces_registered: 20 }
    }

    // หน้า 4: สแกนใบหน้า
    async simulateFaceScan(imageData) {
        // ส่งภาพที่สแกนได้ไปให้ Backend
        console.log('Sending 1 frame to backend for recognition...');
        const response = await fetch('http://127.0.0.1:8000/api/v1/scan-face', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: imageData })
        });
        const result = await response.json();
        
        // Backend จะคืนค่าเป็น { is_match: true, user: { name: 'น้องบอล' }, confidence: 0.9 }
        // หรือ { is_match: false, reason: 'unknown_face' }
        console.log("Backend response:", result);
        return result; 
    }

    // ---------------------------------------------------
    // END: ส่วนที่เปลี่ยนแปลง
    // ---------------------------------------------------

    // ฟังก์ชันนี้ยังเหมือนเดิม
    generateJWT(userId) {
        // ในระบบจริง JWT ควรสร้างจาก Backend
        // แต่ใน Prototype นี้ เรายังจำลองที่ Frontend ได้
        return btoa(JSON.stringify({
            userId: userId,
            exp: Date.now() + (24 * 60 * 60 * 1000), // 24 hours
            iat: Date.now()
        }));
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    verifyJWT(token) {
        try {
            const payload = JSON.parse(atob(token));
            return payload.exp > Date.now();
        } catch {
            return false;
        }
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    animateElement(element, properties, duration = 500) {
        if (typeof anime !== 'undefined') {
            anime({
                targets: element,
                ...properties,
                duration: duration,
                easing: 'easeInOutQuad'
            });
        }
    }

    // ฟังก์ชันนี้ยังเหมือนเดิม
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        
        switch (type) {
            case 'success':
                notification.style.background = '#00ff88';
                break;
            case 'error':
                notification.style.background = '#ff4444';
                break;
            case 'warning':
                notification.style.background = '#ffaa00';
                break;
            default:
                notification.style.background = '#0066ff';
        }
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
}

// Initialize the system
const faceSystem = new FaceRegistrationSystem();

// *** โค้ดแก้จอดำ (ยังมีอยู่) ***
window.addEventListener('beforeunload', () => {
    console.log("Releasing camera before page unload...");
    faceSystem.stopVideoStream();
});

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FaceRegistrationSystem;
}
