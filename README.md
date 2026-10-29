# YOLOv8 Sports Analytics & Tracking Pipeline

A computer vision pipeline built with Python and YOLOv8 designed to track sports objects, detect ball impacts, and analyze court interactions.

---

## 🚀 Key Features
* **Object Detection & Tracking:** Utilizes custom-trained YOLOv8 models to track fast-moving sports objects and player movements.
* **Impact Detection:** Identifies precise contact points and interactions (such as ball-racket impacts) using spatial-temporal frame analysis.
* **Court Mapping & Perspective Correction:** Implements computer vision algorithms (`court_listener.py`, `padel_logic.py`) to map camera feeds to actual court coordinates.

---

## 🛠️ Tech Stack & Tools
* **Language:** Python
* **Computer Vision:** YOLOv8, OpenCV, Roboflow (Dataset Labeling)
* **Architecture:** Modular processing pipelines for real-time video inference and telemetry extraction.

---

## 📂 Project Structure
* `yolo.py`: Core YOLOv8 model initialization and inference engine.
* `track_padel.py`: Main tracking loop for object localization across video frames.
* `court_listener.py`: Extracts court lines and maps spatial boundaries.
* `padel_logic.py`: Handles rule-based game events and interaction analytics.
* `match_router.py`: Coordinates data flow between multiple video streams and tracking modules.
* `camera_recorder.py` & `camera_test.py`: Utilities for multi-camera feed validation and recording triggers.

---

## ⚙️ Getting Started
1. Clone the repository:
   ```bash
   git clone [https://github.com/M-Shahrukh-Khan/yolov8-sports-analytics.git](https://github.com/M-Shahrukh-Khan/yolov8-sports-analytics.git)
