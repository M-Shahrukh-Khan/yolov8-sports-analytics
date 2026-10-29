import cv2
import os
from datetime import datetime

# --- CONFIGURATION ---
CAMERA_INDEX = 0  # 0 is usually the built-in webcam, 1 or 2 will be your external USB camera
RECORD_FPS = 60.0
RESOLUTION = (1280, 720)
OUTPUT_DIR = "elite_courts_raw_matches"

def initialize_camera():
    # cv2.CAP_AVFOUNDATION is critical for macOS hardware acceleration
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])
    cap.set(cv2.CAP_PROP_FPS, RECORD_FPS)
    
    if not cap.isOpened():
        print(f"❌ Error: Could not open camera at index {CAMERA_INDEX}")
        exit()
        
    return cap

def start_match_recording():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    cap = initialize_camera()
    
    # Generate a unique filename based on the exact date and time
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    match_filename = f"match_{timestamp}.mp4"
    filepath = os.path.join(OUTPUT_DIR, match_filename)

    # 'avc1' is the H.264 codec, which provides excellent compression and quality on Macs
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(filepath, fourcc, RECORD_FPS, RESOLUTION)

    print("\n" + "="*50)
    print(f"🔴 RECORDING LIVE: {match_filename}")
    print("Press 'q' in the video window to END THE MATCH.")
    print("="*50 + "\n")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Camera feed lost.")
                break

            out.write(frame)
            
            # Show the live feed so you can ensure the camera hasn't shifted
            cv2.imshow("ELITE COURTS - Live Capture", frame)

            # Wait for the 'q' key to be pressed to simulate the end of a match
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n🛑 Match ended by admin. Stopping recording...")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Force quit detected. Saving video safely...")

    finally:
        # Clean up and save the file properly
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        print(f"✅ Video saved successfully to: {filepath}")
        
        # --- THE HANDOFF ---
        # In the final version, this is where we tell Firebase: 
        # "Update Firestore: status = 'awaiting_admin', video_path = filepath"
        print("⏳ Ready to notify Firebase and trigger the Router module.\n")

if __name__ == "__main__":
    print("🚀 Camera Module Initialized.")
    start_match_recording()