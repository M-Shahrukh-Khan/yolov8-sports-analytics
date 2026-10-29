import cv2
import time
import threading

# Verified index from your system
CAMERA_INDEX = 0 

class HighSpeedCamera:
    def __init__(self, index):
        self.cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 120)
        
        self.ret, self.frame = False, None
        self.running = True
        
        if not self.cap.isOpened():
            print(f"❌ Could not open camera at index {index}")
            exit()
            
        # Start background hardware reading thread
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while self.running:
            self.ret, self.frame = self.cap.read()

    def read(self):
        return self.ret, self.frame

    def stop(self):
        self.running = False
        self.cap.release()

# Initialize camera thread
cam = HighSpeedCamera(CAMERA_INDEX)
print("🚀 Background Thread Running. Calibrating real-time FPS window...")

# Give the hardware thread a moment to wake up
time.sleep(1.0)

prev_time = time.time()
frame_count = 0
fps = 0

while True:
    ret, frame = cam.read()
    if not ret or frame is None:
        continue

    frame_count += 1

    # Calculate precise FPS over short intervals
    if frame_count % 30 == 0:
        curr_time = time.time()
        time_elapsed = curr_time - prev_time
        fps = 30 / time_elapsed if time_elapsed > 0 else 0
        prev_time = curr_time

    h, w = frame.shape[:2]
    
    # Render frame statistics
    cv2.putText(frame, f"FPS: {int(fps)} | Res: {w}x{h} (High-Speed)", (30, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Threaded High-Speed Window", frame)

    # Clean keyboard polling break
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.stop()
cv2.destroyAllWindows()
print("👋 High-speed camera safely disconnected.")