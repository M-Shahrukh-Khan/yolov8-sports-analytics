from ultralytics import YOLO
import cv2

model = YOLO('/Users/shahrukhkhan/runs/detect/train/weights/best.pt')

# Run prediction and get the results object
results = model.predict(source='0504.mp4', save=True, stream=True)

for r in results:
    for box in r.boxes:
        # Get coordinates: x, y, width, height
        x, y, w, h = box.xywh[0]
        
        # Class 0 is likely your 'Ball'
        if int(box.cls) == 0:
            print(f"Ball detected at: X={x.item():.2f}, Y={y.item():.2f}")

    prev_y = 0
is_falling = True

for r in results:
    for box in r.boxes:
        if int(box.cls) == 0: # Ball
            current_y = box.xywh[0][1].item()
            
            # If Y was increasing (falling) and now it's decreasing (rising)
            if current_y < prev_y and is_falling and prev_y > 450: 
                print("BOUNCE DETECTED!")
                # Determine side
                current_x = box.xywh[0][0].item()
                side = "Team A" if current_x < 320 else "Team B"
                print(f"Bounce on {side} side")
                
            is_falling = current_y > prev_y
            prev_y = current_y