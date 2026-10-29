from ultralytics import YOLO
from roboflow import Roboflow
rf = Roboflow(api_key="xfdhswz9EceAycsM8fX5")
project = rf.workspace("muhammads-workspace-s0vqg").project("my-first-project-yqnzf")
version = project.version(2)
dataset = version.download("yolov8")
                

# Load the smallest model (best for real-time and Mac performance)
model = YOLO('yolov8n.pt') 

# Train the model
model.train(
    data=f"{dataset.location}/data.yaml", 
    epochs=50, 
    imgsz=640,
    device='mps',
    plots=True
)