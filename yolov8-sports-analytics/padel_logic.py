import cv2
import time
import threading
import subprocess
from ultralytics import YOLO

# --- 1. MOUSE CALIBRATION CALLBACK ---
def click_calibration_helper(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"📍 CALIBRATION CLICK -> X: {x}, Y: {y}")

# --- 2. SCOREBOARD ENGINE ---
class PadelScoreboard:
    def __init__(self):
        self.points_map = {0: "0", 1: "15", 2: "30", 3: "40"}
        self.team_near_score = 0
        self.team_far_score = 0
        self.team_near_games = 0
        self.team_far_games = 0
        self.active_ball_id = None

    def add_point(self, team):
        if team == "NEAR":
            self.team_near_score += 1
        else:
            self.team_far_score += 1
        self._check_game_status()

    def _check_game_status(self):
        if self.team_near_score >= 4 and (self.team_near_score - self.team_far_score) >= 2:
            self.team_near_games += 1
            self._reset_points()
        elif self.team_far_score >= 4 and (self.team_far_score - self.team_near_score) >= 2:
            self.team_far_games += 1
            self._reset_points()

    def _reset_points(self):
        self.team_near_score, self.team_far_score = 0, 0

    def draw(self, frame):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h-120), (w, h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        score_near = "AD" if self.team_near_score >= 4 and self.team_near_score > self.team_far_score else self.points_map.get(self.team_near_score, "40")
        score_far = "AD" if self.team_far_score >= 4 and self.team_far_score > self.team_near_score else self.points_map.get(self.team_far_score, "40")
        
        display_text = f"NEAR TEAM (Bottom): {self.team_near_games} [{score_near}]  |  FAR TEAM (Top): {self.team_far_games} [{score_far}]"
        cv2.putText(frame, display_text, (50, h-45), cv2.FONT_HERSHEY_DUPLEX, 1.2, (255, 255, 255), 2)

# --- 3. CONFIGURATION & PRIVACY GATE ---
MODEL_PATH = '/Users/shahrukhkhan/runs/detect/train-2/weights/best.mlpackage'
CAMERA_INDEX = 0  
ball_id, racket_id = 0, 1

YOUTUBE_BASE_URL = "rtmp://a.rtmp.youtube.com/live2/"
STREAM_KEY = "xxxx-xxxx-xxxx-xxxx-xxxx" 
RTMP_URL = YOUTUBE_BASE_URL + STREAM_KEY

print("\n" + "="*50)
privacy_choice = input("🎥 Do the players want to LIVE STREAM this match? (y/n): ").strip().lower()
print("="*50 + "\n")

if privacy_choice == 'y':
    SHOULD_STREAM = True
    print("📡 LIVE STREAM MODE ACTIVE.")
    youtube_id = input("🔗 Paste the YouTube Video ID for Firebase mapping: ").strip()
    print(f"👉 Link this ID in your Firebase document: {youtube_id}")
    print("Connecting stream pipeline upon engine start...\n")
else:
    SHOULD_STREAM = False
    print("🔒 PRIVATE MODE ACTIVE. Video will only be saved locally on this Mac Mini.\n")

# --- 4. HIGH-SPEED THREAD ---
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

cam = HighSpeedCamera(CAMERA_INDEX)
time.sleep(1.0) 

model = YOLO(MODEL_PATH)
scoreboard = PadelScoreboard()

# --- 5. TACTICAL GEOMETRY VARIABLES ---
prev_x, prev_y = 0, 0
prev_vel_x, prev_vel_y = 0, 0

video_saver = None
stream_pipe = None
output_filename = "tactical_match_test.mp4"
RECORD_FPS = 60.0  

# Match State Machine
rally_active = False
ball_owner = None       
bounce_count = 0
frame_count = 0
slow_frame_count = 0  

# Dynamic Filters
last_bounce_frame = 0
last_hit_frame = 0
BOUNCE_COOLDOWN = 12    
HIT_COOLDOWN = 15       

cv2.namedWindow("Padel Analytics - Court Tracker", cv2.WND_PROP_FULLSCREEN)
cv2.setMouseCallback("Padel Analytics - Court Tracker", click_calibration_helper)

print("🚀 Tactical Back-Wall Tracking Engine Initialized.")

# --- 6. MAIN LOOP ---
while True:
    ret, frame = cam.read()
    if not ret or frame is None:
        continue

    frame_count += 1
    h, w = frame.shape[:2]

    # Initialize Local File Recorder
    if video_saver is None:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_saver = cv2.VideoWriter(output_filename, fourcc, RECORD_FPS, (w, h))

    # Initialize RTMP App Streamer Pipe (ONLY IF PUBLIC MODE IS ENABLED)
    if stream_pipe is None and SHOULD_STREAM:
        stream_command = [
            'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24', '-s', f'{w}x{h}', '-r', '60',                   
            '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast', '-tune', 'zerolatency',       
            '-b:v', '2500k', '-f', 'flv', RTMP_URL
        ]
        print("📡 Connecting to YouTube Live Server Matrix...")
        stream_pipe = subprocess.Popen(stream_command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    results = model.track(source=frame, stream=True, imgsz=1280, conf=0.15, persist=True, verbose=False)

    ball_coords = None
    racket_coords = []

    # 📏 BACK-WALL HIGH HORIZON LINES (Default start values)
    # Use the mouse clicks in the window to find your exact numbers and update these!
    NET_Y = int(154)           
    NEAR_WALL_Y = int(h * 0.96)     
    FAR_WALL_Y = int(h * 0.15)      
    LEFT_FENCE_X = int(w * 0.05)    
    RIGHT_FENCE_X = int(w * 0.95)   

    for r in results:
        if r.boxes is not None:
            sorted_boxes = sorted(r.boxes, key=lambda x: x.conf, reverse=True)
            
            # Diagnostic heartbeat
            if len(sorted_boxes) > 0 and frame_count % 30 == 0:
                 print(f"\n--- Frame {frame_count} ---")
            
            for box in sorted_boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                box_id = int(box.id.item()) if box.id is not None else None
                
                if cls_id == racket_id:
                    racket_coords.append((int(box.xywh[0][0]), int(box.xywh[0][1])))
                    if frame_count % 30 == 0:
                        print(f"🏸 RACKET spotted! Conf: {conf:.2f}")

                elif cls_id == ball_id and conf > 0.15 and ball_coords is None:
                    if scoreboard.active_ball_id is None or box_id == scoreboard.active_ball_id or box_id is None:
                        if box_id is not None:
                            scoreboard.active_ball_id = box_id 
                        ball_coords = (int(box.xywh[0][0]), int(box.xywh[0][1]))
                        if frame_count % 30 == 0:
                            print(f"⚽ BALL spotted! Conf: {conf:.2f}")

    # --- TACTICAL PHYSICS MATRIX ---
    if ball_coords:
        curr_x, curr_y = ball_coords
        
        if prev_x != 0:
            vel_x = curr_x - prev_x
            vel_y = curr_y - prev_y
            ball_speed = (vel_x**2 + vel_y**2)**0.5  

            if ball_speed < 3.5:
                slow_frame_count += 1
            else:
                slow_frame_count = 0

            if slow_frame_count > 25:
                rally_active = False
                ball_owner = None
                bounce_count = 0

            dynamic_racket_radius = 90 
            near_racket = any(((curr_x - rx)**2 + (curr_y - ry)**2)**0.5 < dynamic_racket_radius for rx, ry in racket_coords)

            # 1. Stroke Ignition (Near vs Far side)
            if near_racket:
                current_striker = "NEAR" if curr_y > NET_Y else "FAR"
                
                if not rally_active and ball_speed > 6.0:
                    ball_owner = current_striker
                    bounce_count = 0
                    rally_active = True
                    last_hit_frame = frame_count
                    print(f"Frame {frame_count}: 💥 Rally Started! Clean Shot by Team {ball_owner}")
                
                elif rally_active and ball_owner != current_striker:
                    ball_owner = current_striker
                    bounce_count = 0
                    last_hit_frame = frame_count
                    print(f"Frame {frame_count}: 💥 Shot Returned by Team {ball_owner}")

            # 2. 2D Vector Acceleration Bounce Check
            accel_x = vel_x - prev_vel_x
            accel_y = vel_y - prev_vel_y
            accel_mag = (accel_x**2 + accel_y**2)**0.5
            
            frames_since_hit = frame_count - last_hit_frame
            frames_since_bounce = frame_count - last_bounce_frame
            
            if accel_mag > 4.0 and frames_since_bounce > BOUNCE_COOLDOWN and frames_since_hit > HIT_COOLDOWN and not near_racket:
                bounce_side = "NEAR" if curr_y > NET_Y else "FAR"
                last_bounce_frame = frame_count
                
                if rally_active and ball_owner is not None:
                    if bounce_side == ball_owner and bounce_count == 0:
                        print(f"Frame {frame_count}: 🔴 Fault! Team {ball_owner} bounced on their own court side.")
                        scoreboard.add_point("FAR" if ball_owner == "NEAR" else "NEAR")
                        rally_active, ball_owner = False, None
                    else:
                        bounce_count += 1
                        print(f"Frame {frame_count}: 🎾 Bounce #{bounce_count} on Team {bounce_side}'s side")
                        
                        if bounce_count >= 2:
                            print(f"Frame {frame_count}: 🏆 Double Bounce! Point awarded to Team {ball_owner}")
                            scoreboard.add_point(ball_owner) 
                            rally_active, ball_owner = False, None

            # 3. DIRECTIONAL OUT OF BOUNDS VALIDATION
            if rally_active and ball_owner is not None and frames_since_hit > 10:
                if ball_owner == "NEAR" and curr_y < FAR_WALL_Y and bounce_count == 0:
                    print(f"Frame {frame_count}: 🔴 Out! Hitting Far Glass directly. Point to Near Team.")
                    scoreboard.add_point("FAR") 
                    rally_active, ball_owner = False, None
                    
                elif ball_owner == "FAR" and curr_y > NEAR_WALL_Y and bounce_count == 0:
                    print(f"Frame {frame_count}: 🔴 Out! Hitting Near Glass directly. Point to Far Team.")
                    scoreboard.add_point("NEAR")
                    rally_active, ball_owner = False, None
                    
                elif (curr_x < LEFT_FENCE_X or curr_x > RIGHT_FENCE_X) and bounce_count == 0:
                    winner = "FAR" if ball_owner == "NEAR" else "NEAR"
                    print(f"Frame {frame_count}: 🔴 Out over side fence! Point awarded.")
                    scoreboard.add_point(winner)
                    rally_active, ball_owner = False, None

            prev_vel_x = vel_x
            prev_vel_y = vel_y
        prev_x, prev_y = curr_x, curr_y
    else:
        prev_vel_x, prev_vel_y = 0, 0

    # --- GEOMETRIC RENDERING ---
    cv2.line(frame, (0, NET_Y), (w, NET_Y), (0, 255, 255), 2)             
    cv2.line(frame, (0, FAR_WALL_Y), (w, FAR_WALL_Y), (255, 0, 0), 1)     
    cv2.line(frame, (0, NEAR_WALL_Y), (w, NEAR_WALL_Y), (255, 0, 0), 1)   
    cv2.line(frame, (LEFT_FENCE_X, 0), (LEFT_FENCE_X, h), (0, 0, 255), 1)  
    cv2.line(frame, (RIGHT_FENCE_X, 0), (RIGHT_FENCE_X, h), (0, 0, 255), 1)
    
    scoreboard.draw(frame)
    
    if video_saver is not None:
        video_saver.write(frame)
        
    if stream_pipe is not None and SHOULD_STREAM:
        try:
            stream_pipe.stdin.write(frame.tobytes())
        except Exception:
            pass
        
    cv2.imshow("Padel Analytics - Court Tracker", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

# --- 7. CLEAN DISCONNECT ---
if video_saver is not None:
    video_saver.release()
if stream_pipe is not None:
    stream_pipe.stdin.close()
    stream_pipe.wait()
cam.stop()
cv2.destroyAllWindows()
print("👋 Tactical tracking process ended cleanly.")