import mediapipe as mp
from ultralytics import YOLO
from threading import Lock

# Initialize YOLO model for invigilator and mobile phone detection
yolo_model = YOLO('best.pt')

# --- MEDIAPIPE INITIALIZATION ---
mediapipe_lock = Lock()
mp_face_detection = mp.solutions.face_detection  # used below for FaceDetection init

# Face Detection: Finds all faces in frame (optimized for distance)
face_detection = mp_face_detection.FaceDetection(
    model_selection=1,              # 1 = full range model (better for distant faces)
    min_detection_confidence=0.3    # Low threshold for classroom environments
)

# MULTI-STUDENT FIX: static_image_mode=True treats every frame
# independently — no tracking continuity required between frames.
# min_tracking_confidence intentionally omitted: irrelevant in static image mode.
face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=10,
    refine_landmarks=False,
    min_detection_confidence=0.3
)
