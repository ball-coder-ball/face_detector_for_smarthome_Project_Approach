// Smart Home Face Registration System - Main JavaScript
// Core functionality for camera, face detection, and API simulation

class FaceRegistrationSystem {
    constructor() {
        this.videoStream = null;
        this.isDetecting = false;
        this.registeredFaces = [];
        this.accessLogs = [];
        this.mockUsers = [];
        this.initializeMockData();
    }

    initializeMockData() {
        // Mock registered users for demonstration
        this.mockUsers = [
            {
                id: 'user001',
                name: 'สมชาย ใจดี',
                faceEmbeddings: this.generateMockEmbeddings(),
                status: 'approved'
            },
            {
                id: 'user002',
                name: 'สมหญิง รักษ์บ้าน',
                faceEmbeddings: this.generateMockEmbeddings(),
                status: 'approved'
            }
        ];
    }

    generateMockEmbeddings() {
        // Generate mock face embeddings for demonstration
        const embeddings = [];
        for (let i = 0; i < 20; i++) {
            const embedding = [];
            for (let j = 0; j < 512; j++) {
                embedding.push(Math.random() * 2 - 1);
            }
            embeddings.push(embedding);
        }
        return embeddings;
    }

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

    async simulateSpoofDetection(frames) {
        // Simulate spoof detection with realistic timing
        await this.delay(1000 + Math.random() * 500);
        
        // Simulate detection results
        const isReal = Math.random() > 0.3; // 70% success rate for demo
        const confidence = isReal ? 0.95 + Math.random() * 0.05 : 0.1 + Math.random() * 0.3;
        
        return {
            is_real: isReal,
            confidence: confidence,
            message: isReal ? 'Real face detected' : 'Spoof detected'
        };
    }

    async simulateFaceRegistration(userId, faceImages) {
        // Simulate face registration process
        await this.delay(2000 + Math.random() * 1000);
        
        const newUser = {
            id: userId,
            name: `User ${userId}`,
            faceEmbeddings: this.generateMockEmbeddings(),
            status: 'approved',
            registeredAt: new Date().toISOString()
        };
        
        this.mockUsers.push(newUser);
        
        return {
            success: true,
            faces_registered: faceImages.length,
            user_id: userId
        };
    }

    async simulateFaceScan(imageData) {
        // Simulate spoof detection first
        const spoofResult = await this.simulateSpoofDetection([imageData]);
        if (!spoofResult.is_real) {
            return {
                is_match: false,
                reason: 'spoof_detected',
                message: 'Spoofing attempt detected'
            };
        }

        // Simulate face matching
        await this.delay(500 + Math.random() * 300);
        
        // Random match with existing users
        if (Math.random() > 0.4 && this.mockUsers.length > 0) {
            const matchedUser = this.mockUsers[Math.floor(Math.random() * this.mockUsers.length)];
            
            // Log access attempt
            this.accessLogs.push({
                userId: matchedUser.id,
                timestamp: new Date().toISOString(),
                success: true,
                confidence: 0.75 + Math.random() * 0.25
            });
            
            return {
                is_match: true,
                user: matchedUser,
                confidence: 0.75 + Math.random() * 0.25
            };
        }
        
        return {
            is_match: false,
            reason: 'unknown_face',
            message: 'Face not recognized'
        };
    }

    async simulateLineNotification(message, userId = null) {
        // Simulate LINE notification sending
        await this.delay(500);
        
        console.log('LINE Notification:', message);
        
        return {
            success: true,
            message_id: `msg_${Date.now()}`,
            timestamp: new Date().toISOString()
        };
    }

    generateJWT(userId) {
        // Simulate JWT token generation
        return btoa(JSON.stringify({
            userId: userId,
            exp: Date.now() + (24 * 60 * 60 * 1000), // 24 hours
            iat: Date.now()
        }));
    }

    verifyJWT(token) {
        // Simulate JWT verification
        try {
            const payload = JSON.parse(atob(token));
            return payload.exp > Date.now();
        } catch {
            return false;
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Animation helpers
    animateProgress(element, targetValue, duration = 1000) {
        if (typeof anime !== 'undefined') {
            anime({
                targets: element,
                value: targetValue,
                duration: duration,
                easing: 'easeInOutQuad'
            });
        } else {
            element.value = targetValue;
        }
    }

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

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FaceRegistrationSystem;
}