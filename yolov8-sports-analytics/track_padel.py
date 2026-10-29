from ultralytics import YOLO
import cv2

# 1. Configuration & Constants
# Load the model directly using the path string
model = YOLO('/Users/shahrukhkhan/runs/detect/train-2/weights/best.mlpackage')

VIDEO_PATH = '0514.mp4'
NET_X_RATIO = 0.5  
TURF_Y_RATIO = 0.65  # Lowered slightly to capture more of the far court

# 2. State Variables
prev_y = 0
is_falling = True
ball_id = 0 

# Run tracking at 1280 resolution
results = model.track(source=VIDEO_PATH, save=True, stream=True, imgsz=1280, conf=0.15)

print("--- Padel Play AI: Logic Engine Started ---")

for r in results:
    h, w = r.orig_shape
    net_line = w * NET_X_RATIO
    turf_line = h * TURF_Y_RATIO

    if r.boxes:
        for box in r.boxes:
            if int(box.cls) == ball_id:
                curr_x, curr_y = int(box.xywh[0][0].item()), int(box.xywh[0][1].item())
        
                # --- THE SKY MASK ---
                if curr_y < (h * 0.35): 
                    continue # If the ball is in the lights, skip the rest of this loop!
                
                # --- THE BOUNCE LOGIC ---
                # This only runs if the ball is BELOW the 35% mark (because of the continue above)
                if curr_y < prev_y and is_falling and prev_y > turf_line:
                    side = "TEAM A (Left)" if curr_x < net_line else "TEAM B (Right)"
                    print(f"🏆 BOUNCE DETECTED on {side}!")

                # Update states for the next frame
                is_falling = curr_y > prev_y
                prev_y = curr_y