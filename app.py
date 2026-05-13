import atexit
import cv2
import os
import time
try:
    import winsound
    _WINSOUND_AVAILABLE = True
except ImportError:
    # winsound is Windows-only; on Linux/macOS alerts are handled by the browser
    _WINSOUND_AVAILABLE = False
import json
from functools import wraps
from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, send_file, session, flash
from ultralytics import YOLO
from datetime import datetime
from threading import Thread, Lock
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from fpdf import FPDF
import mediapipe as mp
import numpy as np


app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random key

# --- Configurations ---
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed_outputs'  # ITERATION 3
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)  # ITERATION 3
os.makedirs('Reports', exist_ok=True)

# Model Load karein
model = YOLO('best.pt')
current_source = None
violations_log = []
violations_lock = Lock()  # Thread-safe access to violations_log
active_violations = {}

# Camera management (ITERATION 1)
active_camera = None
camera_lock = Lock()
camera_error = None
selected_camera_index = 0  # Default camera index for proctoring

# --- FRAME BUFFER (Evidence Quality Fix) ---
# Stores last 5 valid frames from generate() loop for use in evidence saving.
# Prevents black screenshots when async detection thread runs on empty buffer.
frame_buffer = []
frame_buffer_lock = Lock()
FRAME_BUFFER_SIZE = 5

# Per-face peeking cooldown tracker — maps cooldown_key -> {'last_capture': float}
_peek_cooldowns = {}

# Settings
invigilator_threshold = 0.80  # High Accuracy Class
# Mobile phone detection confidence threshold
# Separate from invigilator_threshold for independent tuning
confidence_threshold = 0.60  # 60% minimum confidence for phone detection

# --- PHONE TRACKER STATE MACHINE (Multi-Phone Spatial Tracking) ---
# Tracks individual phones using IoU to ensure each distinct phone has
# its own debounce and cooldown logic.
phone_tracks = {}         # {phone_id (int): {'box': list, 'frames_lost': int, 'consecutive_frames': int, 'alarm_fired_at': float, 'incident_active': bool}}
phone_id_counter = 0
phone_tracker_lock = Lock()
# Depth difference threshold (Lower = More Sensitive)
peeking_sensitivity = 0.2
current_session_id = None  # Global session ID for report isolation
session_active = False  # Track if monitoring session is active

# --- SESSION METADATA (Enhanced Report) ---
session_start_time = None     # datetime object — set when session starts
session_end_time = None       # datetime object — set when session ends
unique_face_ids_seen = set()  # tracks unique student face_ids flagged as critical

# --- INVIGILATOR GHOST BOX SYSTEM (MODEL A: Phase 1 - Sensor Fusion) ---
# When YOLO detects an invigilator, their bounding box is stored as a "ghost".
# The ghost persists for 20 frames (TTL) even after YOLO stops detecting them.
# This prevents false peeking alarms when the invigilator briefly leaves YOLO's view.
invigilator_ghost_boxes = []   # List of [x1, y1, x2, y2] numpy arrays (last known positions)
invigilator_ghost_ttl = {}     # Dict: {list_index (int) -> remaining_frames (int)}
invigilator_ghost_lock = Lock()  # Thread-safe access since detection runs in background thread

# --- MUTUAL GAZE DETECTION (MODEL A: Phase 3) ---
MUTUAL_GAZE_MAX_DISTANCE = 600
MUTUAL_GAZE_MAX_VERTICAL = 150
mutual_gaze_sessions = {} # pair_key (str) -> {'start_time': float, 'duration': float, 'last_seen': float, 'alert_fired': bool}

# --- FACE TRACKER + SUSPICION STATE MACHINE (MODEL A: Phase 2) ---
# face_tracks: Lightweight IoU-based tracker for peeking faces only.
# Allows us to re-identify the same face across frames even if it briefly
# looks forward (no bounding box from MediaPipe) and then peeks again.
face_tracks = {}         # {face_id (int): {'box': list, 'last_seen_frame': int, 'frames_lost': int}}
face_id_counter = 0      # Monotonically increasing ID for new face tracks
current_frame_number = 0 # Incremented each time run_async_detection() runs

# student_suspicion: Cumulative suspicion state per tracked face.
# Key insight: we accumulate sideways time ACROSS multiple looks within a
# 30-second session window, so smart cheaters cannot fool the system by
# breaking their glances into short bursts.
student_suspicion = {}   # {face_id (int): suspicion state dict (see update_suspicion_state)}

# --- MEDIAPIPE INITIALIZATION ---
mediapipe_lock = Lock()
mp_face_mesh = mp.solutions.face_mesh
mp_face_detection = mp.solutions.face_detection

# Face Detection: Finds all faces in frame (optimized for distance)
face_detection = mp_face_detection.FaceDetection(
    model_selection=1,  # 1 = full range model (better for distant faces)
    min_detection_confidence=0.3  # Low threshold for classroom environments
)

# MULTI-STUDENT FIX: static_image_mode=True treats every frame
# independently — no tracking continuity required between frames.
# This is essential because our async thread skips frames, which
# breaks MediaPipe's internal face tracker causing it to drop
# all faces except the most prominent one.
# min_detection_confidence=0.3 catches second/third faces that
# are slightly less frontal. Combined with 1280px input resolution,
# this does NOT increase false positives.
face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=10,
    refine_landmarks=False,
    min_detection_confidence=0.3,
    min_tracking_confidence=0.3
)


def trigger_alert():
    """Beep sound in a separate thread to prevent lag (Windows only)"""
    if _WINSOUND_AVAILABLE:
        Thread(target=lambda: winsound.Beep(1000, 500)).start()


def get_available_cameras():
    """
    Scans indices 0-5 to find all connected cameras.
    Returns: List of dicts [{'id': index, 'name': room_name}]
    """
    available = []
    # Use DSHOW on Windows for fast detection
    for i in range(5):
        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    room_name = f"Room {i+1} (Built-in)" if i == 0 else f"Room {i+1} (External)"
                    available.append({'id': i, 'name': room_name})
                cap.release()
        except:
            continue
    return available


def initialize_camera(index=None):
    """
    Try multiple backends to open camera reliably on Windows
    Args:
        index: If provided, opens this index. Otherwise uses selected_camera_index.
    Returns: VideoCapture object or None
    """
    global camera_error, selected_camera_index
    
    target_index = index if index is not None else selected_camera_index
    camera_error = None
    
    backends = [
        (cv2.CAP_DSHOW, "DirectShow (Windows)"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_ANY, "Default Backend")
    ]

    print(f"🎥 Attempting to initialize camera {target_index}...")

    for backend, name in backends:
        try:
            print(f"   Trying {name}...")
            cap = cv2.VideoCapture(target_index, backend)

            # Test if camera actually opened
            if cap.isOpened():
                # Try to read a test frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"   ✅ Camera {target_index} opened successfully with {name}")
                    return cap
                else:
                    cap.release()
            else:
                cap.release()
        except Exception as e:
            print(f"   ❌ {name} failed: {str(e)}")
            continue

    # All backends failed
    camera_error = f"Camera {target_index} not accessible. Please check connection and permissions."
    print(f"   ❌ {camera_error}")
    return None


def release_camera():
    """Safely release the active camera"""
    global active_camera
    with camera_lock:
        if active_camera is not None:
            try:
                active_camera.release()
                print("📷 Camera released successfully")
            except Exception as e:
                print(f"⚠️ Error releasing camera: {str(e)}")
            finally:
                active_camera = None


def get_report_dir():
    """Returns folder specific to current session"""
    global current_session_id
    if not current_session_id:
        # Fallback or default
        current_session_id = f"Session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    path = os.path.join('Reports', current_session_id)
    os.makedirs(path, exist_ok=True)
    return path

def detect_peeking_mediapipe(frame):
    """
    Head Pose Estimation using Upper-Face Rigid Model (6-Point PnP).
    Uses only eyes, nose bridge, and forehead - stable even with face coverings.
    ITERATION 13: Upper-Face Rigid Model for proctoring.
    - Only Yaw detection (left/right head turn)
    - 30° threshold to reduce false positives
    - No chin/mouth points (unstable, often covered)
    """
    h, w, _ = frame.shape

    # --- STEP 1: Define 3D Upper-Face Rigid Model ---
    # Anatomically correct coordinates in millimeters
    # Origin at nose bridge (between eyes)
    # X: left(-) / right(+)
    # Y: down(-) / up(+)  
    # Z: back(-) / forward(+)
    model_points = np.array([
        (0.0, 0.0, 0.0),         # Nose bridge (MediaPipe #6) - ORIGIN
        (-33.0, -3.0, -25.0),    # Left eye outer corner (MediaPipe #33)
        (33.0, -3.0, -25.0),     # Right eye outer corner (MediaPipe #263)
        (-13.0, -3.0, -12.0),    # Left eye inner corner (MediaPipe #133)
        (13.0, -3.0, -12.0),     # Right eye inner corner (MediaPipe #362)
        (0.0, 25.0, -15.0)       # Forehead/Glabella (MediaPipe #10)
    ], dtype=np.float64)

    # --- STEP 2: Camera Matrix Estimation ---
    focal_length = w  # Approximate focal length as frame width
    center = (w / 2.0, h / 2.0)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    
    dist_coeffs = np.zeros((4, 1))  # Assume no lens distortion

    # Resize for processing if frame is very large
    proc_frame = frame
    scale_factor = 1.0
    if w > 2560:
        scale_factor = 2560 / w
        proc_frame = cv2.resize(frame, (2560, int(h * scale_factor)))

    rgb_frame = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)

    with mediapipe_lock:
        results = face_mesh.process(rgb_frame)

    peeking_detections = []

    # Log total faces detected — critical for verifying multi-face fix
    total_detected = len(results.multi_face_landmarks) \
        if results.multi_face_landmarks else 0
    print(f"[MEDIAPIPE] Total faces detected: {total_detected} "
          f"(frame: {frame.shape[1]}x{frame.shape[0]}px)")

    if results.multi_face_landmarks:
        proc_h, proc_w, _ = proc_frame.shape
        
        for face_landmarks in results.multi_face_landmarks:
            # --- STEP 3: Extract 2D Image Points (Upper Face Only) ---
            image_points = np.array([
                (face_landmarks.landmark[6].x * proc_w, 
                 face_landmarks.landmark[6].y * proc_h),      # Nose bridge
                (face_landmarks.landmark[33].x * proc_w, 
                 face_landmarks.landmark[33].y * proc_h),     # Left eye outer
                (face_landmarks.landmark[263].x * proc_w, 
                 face_landmarks.landmark[263].y * proc_h),    # Right eye outer
                (face_landmarks.landmark[133].x * proc_w, 
                 face_landmarks.landmark[133].y * proc_h),    # Left eye inner
                (face_landmarks.landmark[362].x * proc_w, 
                 face_landmarks.landmark[362].y * proc_h),    # Right eye inner
                (face_landmarks.landmark[10].x * proc_w, 
                 face_landmarks.landmark[10].y * proc_h)      # Forehead
            ], dtype=np.float64)

            # --- STEP 4: Solve PnP ---
            scaled_camera_matrix = camera_matrix.copy()
            if scale_factor < 1.0:
                scaled_camera_matrix[0, 0] = proc_w
                scaled_camera_matrix[1, 1] = proc_w
                scaled_camera_matrix[0, 2] = proc_w / 2.0
                scaled_camera_matrix[1, 2] = proc_h / 2.0

            # --- Bounding Box Calculation (computed BEFORE PnP) ---
            # Needed both for min-size filter and for PnP-failure aspect ratio check
            x_coords = [lm.x for lm in face_landmarks.landmark]
            y_coords = [lm.y for lm in face_landmarks.landmark]

            bx1_proc = int(min(x_coords) * proc_w)
            by1_proc = int(min(y_coords) * proc_h)
            bx2_proc = int(max(x_coords) * proc_w)
            by2_proc = int(max(y_coords) * proc_h)

            # Skip faces too small for reliable detection at 1280px input
            # Lowered to 25px to catch students sitting further back
            MIN_FACE_SIZE = 25
            face_width_proc = bx2_proc - bx1_proc
            face_height_proc = by2_proc - by1_proc
            if face_width_proc < MIN_FACE_SIZE or face_height_proc < MIN_FACE_SIZE:
                continue  # Skip — too small/distant for accurate detection

            # Scale bounding box back to original frame coordinates
            if scale_factor < 1.0:
                bx1 = int(bx1_proc / scale_factor)
                by1 = int(by1_proc / scale_factor)
                bx2 = int(bx2_proc / scale_factor)
                by2 = int(by2_proc / scale_factor)
            else:
                bx1, by1, bx2, by2 = bx1_proc, by1_proc, bx2_proc, by2_proc

            success, rvec, tvec = cv2.solvePnP(
                model_points,
                image_points,
                scaled_camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                # PnP failed — face at extreme angle beyond solver range (~70-90°)
                # Distinguish sideways failure from downward pitch failure
                # using face bounding box aspect ratio:
                #   Portrait (height > width) = face turned sideways = SUSPICIOUS
                #   Landscape (width > height) = face pitched down = writing student

                face_bbox_w = bx2 - bx1
                face_bbox_h = by2 - by1

                if face_bbox_h > face_bbox_w:
                    # Portrait orientation = extreme sideways turn confirmed
                    # Use 89.0 as reported yaw (maximum sideways, direction unknown)
                    # Determine direction from face position in frame:
                    # Face in left half of frame = probably looking right
                    # Face in right half of frame = probably looking left
                    frame_center_x = frame.shape[1] // 2
                    face_center_x = (bx1 + bx2) // 2
                    extreme_yaw = 89.0 if face_center_x < frame_center_x else -89.0

                    print(f"[MEDIAPIPE] PnP fail — extreme sideways angle detected "
                          f"(portrait face, estimated yaw={extreme_yaw:.0f}°)")

                    peeking_detections.append({
                        'label': 'peeking',
                        'display_label': 'Peeking',
                        'conf': 0.7,
                        'box': [bx1, by1, bx2, by2],
                        'yaw': extreme_yaw,
                        'extreme_angle': True
                    })
                else:
                    # Landscape orientation = looking down = writing student
                    # Skip silently — this is innocent behavior
                    print(f"[MEDIAPIPE] PnP fail — landscape face, "
                          f"likely looking down, skipping")
                continue

            # --- STEP 5: Extract Euler Angles ---
            rotation_matrix, _ = cv2.Rodrigues(rvec)
            euler_angles, _, _, _, _, _ = cv2.RQDecomp3x3(rotation_matrix)

            # Guard against degenerate PnP solutions (e.g. face at exactly 90°)
            if np.isnan(euler_angles).any():
                print("[MEDIAPIPE] PnP returned NaN Euler angles — skipping face")
                continue

            yaw = euler_angles[1]    # Y-axis rotation (looking left/right)

            # --- STEP 6: Classification (Yaw Only) ---
            YAW_THRESHOLD = 22  # Lowered to 22 for instant bounding box appearance
            
            if abs(yaw) > YAW_THRESHOLD:
                # Confidence based on yaw severity
                confidence = min(1.0, abs(yaw) / 90.0 * 1.5)

                peeking_detections.append({
                    'label': 'peeking',
                    'display_label': 'Peeking',
                    'conf': confidence,
                    'box': [bx1, by1, bx2, by2],
                    'yaw': yaw
                })

    # --- NMS: Remove Duplicate Detections ---
    peeking_detections.sort(
        key=lambda x: (x['box'][2] - x['box'][0]) * (x['box'][3] - x['box'][1]), 
        reverse=True
    )
    
    filtered_detections = []
    for det in peeking_detections:
        is_duplicate = False
        for existing in filtered_detections:
            box1 = det['box']
            box2 = existing['box']

            x1 = max(box1[0], box2[0])
            y1 = max(box1[1], box2[1])
            x2 = min(box1[2], box2[2])
            y2 = min(box1[3], box2[3])

            intersection = max(0, x2 - x1) * max(0, y2 - y1)
            area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
            area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
            union = area1 + area2 - intersection

            iou = intersection / union if union > 0 else 0
            min_area = min(area1, area2)
            io_min = intersection / min_area if min_area > 0 else 0

            if iou > 0.3 or io_min > 0.8:
                is_duplicate = True
                break

        if not is_duplicate:
            filtered_detections.append(det)

    return filtered_detections



def get_best_evidence_frame(fallback_frame):
    """
    Returns the most recent valid (non-black) frame from the rolling buffer.
    Used by save_evidence_smart() to ensure evidence screenshots have real
    visual content even when the detection thread's frame buffer is empty.

    A frame is considered valid if its mean pixel value > 20.0.
    Threshold of 20.0 chosen because:
      - Pure black frame = mean of 0.0
      - Motion-blurred camera warmup frames = mean of 5-15 (rejected)
      - Genuinely dark real-room footage = mean of 25+ (accepted)
      - 20.0 rejects blurry warmup frames while preserving real dark-room evidence

    Args:
        fallback_frame: The original frame from the detection thread (may be black)
    Returns:
        Best available frame (numpy array)
    """
    with frame_buffer_lock:
        # Search from most recent to oldest
        for buffered_frame in reversed(frame_buffer):
            if buffered_frame is not None and buffered_frame.mean() > 20.0:
                return buffered_frame.copy()
    # If buffer is empty or all frames are black, use fallback
    print("[FRAME BUFFER] Warning: No valid frame in buffer, using fallback")
    return fallback_frame


def save_evidence_smart(frame, label, box_coords, confidence=None,
                        display_label=None, alert_level='warning', face_id=None):
    """
    MODEL A PHASE 2 — Peeking evidence saving, driven by the suspicion state machine.

      alert_level='critical' (or 'critical_directional'):
        - Overlay: red "CRITICAL: SIGNALING DETECTED"
        - Audio beep fires via trigger_alert()
        - Cooldown: 15 seconds per face_id

    Args:
        frame:        Video frame from detection thread (mirrored, 640px)
        label:        Violation type string — only 'peeking' is acted on
        box_coords:   [x1, y1, x2, y2] bounding box in detection-frame space
        confidence:   Detection confidence float (optional)
        display_label: Override for on-screen text (optional)
        alert_level:  'critical', 'critical_directional', or 'clean'
        face_id:      Tracked face ID for per-face cooldown (optional)

    Returns:
        File path string if evidence was saved, None otherwise
    """
    global _peek_cooldowns

    # Handle peeking and mobile_phone labels
    if label not in ('peeking', 'mobile_phone'):
        return None

    # Skip 'clean' level for peeking — nothing to save yet
    if label == 'peeking' and alert_level == 'clean':
        return None

    original_frame = frame
    evidence_frame = get_best_evidence_frame(original_frame)

    # Check if we got the fallback frame
    is_fallback = (evidence_frame is original_frame)
    if is_fallback:
        # Fallback is mirrored (from detection input). Un-mirror for consistent evidence.
        evidence_frame = cv2.flip(evidence_frame, 1)

    # Map box_coords from detection space (mirrored, downscaled) to evidence space (unmirrored, full-res)
    dh, dw = original_frame.shape[:2]
    eh, ew = evidence_frame.shape[:2]
    scale = ew / dw

    x1, y1, x2, y2 = box_coords
    sx1, sy1, sx2, sy2 = x1 * scale, y1 * scale, x2 * scale, y2 * scale
    box_coords = [max(0, int(ew - sx2)), max(0, int(sy1)),
                  min(ew, int(ew - sx1)), min(eh, int(sy2))]

    now = time.time()

    # --- MOBILE PHONE: instant critical, 20s cooldown ---
    if label == 'mobile_phone':
        cooldown_key = f"phone_box_{box_coords[0]}_{box_coords[1]}"
        last_capture = _peek_cooldowns.get(cooldown_key, 0)
        if now - last_capture < 20.0:
            return None

        overlay_text = "VIOLATION: MOBILE PHONE"
        file_prefix = 'mobile_phone'
        box_color = (0, 0, 255)  # Red
        trigger_alert()  # Beep immediately — no duration needed

        ev = evidence_frame.copy()
        h, w = ev.shape[:2]
        cv2.rectangle(ev, (0, h - 65), (w, h), (0, 0, 0), -1)
        ts = datetime.now().strftime("%H:%M:%S")
        cv2.putText(ev, overlay_text, (10, h - 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)
        x1, y1, x2, y2 = box_coords
        cv2.rectangle(ev, (x1, y1), (x2, y2), box_color, 3)
        cv2.putText(ev, "VIOLATION", (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 2)
        cv2.putText(ev, f"Time: {ts}  Conf: {int(confidence * 100)}%", (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        img_path = os.path.join(get_report_dir(), f"{file_prefix}_{int(now)}.jpg")
        cv2.imwrite(img_path, ev)

        _peek_cooldowns[cooldown_key] = now
        print(f"📸 Evidence saved: {os.path.basename(img_path)} [mobile_phone] conf={confidence}")
        return img_path

    # --- PEEKING: existing logic below ---
    # Per-face cooldown check (15 seconds between screenshots for the same face)
    cooldown_key = f"peek_face_{face_id}" if face_id is not None else f"peek_box_{box_coords[0]}"
    last_capture = _peek_cooldowns.get(cooldown_key, 0)
    if now - last_capture < 15.0:
        return None

    # Determine overlay text
    if 'directional' in alert_level:
        overlay_text = "CRITICAL: DIRECTIONAL SIGNALING"
        file_prefix = 'directional_signaling'
    else:
        overlay_text = "CRITICAL: SIGNALING DETECTED"
        file_prefix = 'signaling_detected'

    box_color = (0, 0, 255)  # Red
    trigger_alert()

    # Annotate a copy — never mutate the live frame
    ev = evidence_frame.copy()
    h, w = ev.shape[:2]
    cv2.rectangle(ev, (0, h - 65), (w, h), (0, 0, 0), -1)
    ts = datetime.now().strftime("%H:%M:%S")
    cv2.putText(ev, overlay_text, (10, h - 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)
    x1, y1, x2, y2 = box_coords
    cv2.rectangle(ev, (x1, y1), (x2, y2), box_color, 3)
    label_tag = overlay_text.split(':')[0]  # 'CRITICAL'
    cv2.putText(ev, label_tag, (x1, max(y1 - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 2)
    face_tag = f"face_id={face_id}" if face_id is not None else ""
    cv2.putText(ev, f"Time: {ts}  {face_tag}", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    img_path = os.path.join(get_report_dir(), f"{file_prefix}_{int(now)}.jpg")
    cv2.imwrite(img_path, ev)

    _peek_cooldowns[cooldown_key] = now
    print(f"📸 Evidence saved: {os.path.basename(img_path)} [{alert_level}] face_id={face_id}")
    return img_path


def process_video(input_path, output_path):
    """
    Process video and save with ALL detections drawn on every frame
    Returns: Number of frames processed
    """
    print(f"🎬 Processing video: {os.path.basename(input_path)}")

    try:
        cap = cv2.VideoCapture(input_path)

        if not cap.isOpened():
            print(f"❌ Failed to open video: {input_path}")
            return 0

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(
            f"   📊 Video info: {width}x{height} @ {fps}fps, {total_frames} frames")

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            print(f"❌ Failed to create output video: {output_path}")
            cap.release()
            return 0

        frame_count = 0
        detection_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Convert 4-channel to 3-channel if needed
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # Run detection on this frame — invigilator only
            results = model.predict(
                frame, conf=invigilator_threshold, iou=0.45, verbose=False)

            # Draw ALL detections
            for r in results:
                for box in r.boxes:
                    lbl = model.names[int(box.cls[0])]
                    conf = float(box.conf[0])
                    c = box.xyxy[0].cpu().numpy().astype(int)

                    if lbl == 'invigilator':
                        color = (255, 0, 0)
                        thickness = 2
                    else:
                        color = (0, 255, 0)
                        thickness = 2

                    cv2.rectangle(frame, (c[0], c[1]),
                                (c[2], c[3]), color, thickness)
                    # Add label with confidence - SMART POSITIONING
                    label_text = f"{lbl.replace('_', ' ')}: {int(conf * 100)}%"
                    (text_w, text_h), _ = cv2.getTextSize(
                        label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

                    # If box is too close to top, draw label INSIDE the box
                    t_y = c[1] - 8 if c[1] > 25 else c[1] + text_h + 8

                    cv2.rectangle(
                        frame, (c[0], t_y - text_h - 4), (c[0] + text_w + 8, t_y + 4), color, -1)
                    cv2.putText(frame, label_text, (c[0] + 4, t_y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    detection_count += 1

            # --- MEDIAPIPE PEEKING CHECK (Recorded Video) ---
            peeking_results = detect_peeking_mediapipe(frame)
            for p_det in peeking_results:
                bx1, by1, bx2, by2 = p_det['box']
                display_lbl = p_det['display_label']
                color = (0, 0, 255)

                cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 3)
                label_text = f"{display_lbl}: {int(p_det['conf'] * 100)}%"
                (text_w, text_h), _ = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (bx1, by1 - text_h - 8),
                              (bx1 + text_w + 8, by1), color, -1)
                cv2.putText(frame, label_text, (bx1 + 4, by1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                detection_count += 1

            # Write annotated frame
            out.write(frame)
            frame_count += 1

            # Progress update every 30 frames
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * \
                    100 if total_frames > 0 else 0
                print(
                    f"   ⏳ Progress: {frame_count}/{total_frames} frames ({progress:.1f}%)")

        cap.release()
        out.release()

        print(
            f"   ✅ Video processed: {frame_count} frames, {detection_count} detections")
        return frame_count

    except Exception as e:
        print(f"   ❌ Error processing video: {str(e)}")
        return 0


def process_image(input_path, output_path):
    """
    Process image and save with ALL detections drawn
    Returns: True if successful, False otherwise
    """
    print(f"🖼️ Processing image: {os.path.basename(input_path)}")

    try:
        frame = cv2.imread(input_path)

        if frame is None:
            print(f"   ❌ Failed to read image: {input_path}")
            return False

        # Convert 4-channel to 3-channel if needed
        if len(frame.shape) == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # Run detection — invigilator class only
        results = model.predict(
            frame, conf=invigilator_threshold, iou=0.45, verbose=False)

        detection_count = 0

        # Draw ALL detections
        for r in results:
            for box in r.boxes:
                lbl = model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                c = box.xyxy[0].cpu().numpy().astype(int)

                # Determine color and thickness
                if lbl == 'invigilator':
                    color = (255, 0, 0)  # Blue
                    thickness = 2
                else:
                    color = (0, 255, 0)  # Green
                    thickness = 2

                # Draw bounding box (Thinner, cleaner)
                cv2.rectangle(frame, (c[0], c[1]), (c[2], c[3]), color, 2)

                # Add label with confidence - SMART POSITIONING
                label_text = f"{lbl.replace('_', ' ')}: {int(conf * 100)}%"
                # Use FONT_HERSHEY_DUPLEX for cleaner look, scale 0.5, thickness 1
                (text_w, text_h), _ = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)

                # If box is too close to top, draw label INSIDE the box
                t_y = c[1] - 10 if c[1] > 30 else c[1] + text_h + 10

                # Background rect for text (Slightly transparent look if possible, but solid for now)
                cv2.rectangle(frame, (c[0], t_y - text_h - 5),
                              (c[0] + text_w + 10, t_y + 5), color, -1)

                # White Text, Thinner
                cv2.putText(frame, label_text, (c[0] + 5, t_y),
                            cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

                detection_count += 1

        # --- MEDIAPIPE PEEKING CHECK (Processing Engine) ---
        peeking_results = detect_peeking_mediapipe(frame)
        for p_det in peeking_results:
            bx1, by1, bx2, by2 = p_det['box']
            display_lbl = p_det['display_label']
            color = (0, 0, 255)

            # Thinner Box
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2)
            label_text = f"{display_lbl}: {int(p_det['conf'] * 100)}%"

            (text_w, text_h), _ = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)

            # Smart Positioning
            t_y = by1 - 10 if by1 > 30 else by1 + text_h + 10
            cv2.rectangle(frame, (bx1, t_y - text_h - 5),
                          (bx1 + text_w + 10, t_y + 5), color, -1)
            cv2.putText(frame, label_text, (bx1 + 5, t_y),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)

            detection_count += 1

        # Save annotated image
        cv2.imwrite(output_path, frame)

        print(f"   ✅ Image processed: {detection_count} detection(s) found")
        return True

    except Exception as e:
        print(f"   ❌ Error processing image: {str(e)}")
        return False


# --- ASYNC DETECTION HELPERS (ITERATION 11: LAG FIX) ---
detection_lock = Lock()
latest_detections = []  # List of dicts: {label, conf, box: [x1,y1,x2,y2]}
is_detecting = False
frame_skip_counter = 0  # Frame counter for intelligent skipping
PROCESS_EVERY_N_FRAMES = 2  # Process every 2nd frame (Faster)


# ==============================================================================
# GHOST BOX HELPERS — MODEL A PHASE 1
# ==============================================================================

def update_invigilator_ghosts(new_invigilator_boxes):
    """
    Maintains a persistent registry of invigilator bounding box positions.

    Each time YOLO detects an invigilator, their box is matched to an
    existing ghost (within 150px proximity) and their TTL resets to 20 frames.
    Each frame where a ghost is NOT re-detected, TTL decrements by 1.
    At TTL=0, the ghost is purged.

    This means the invigilator's last known position is "remembered" for
    approximately 20 frames (~0.6s at 30fps) even when YOLO temporarily loses them.

    Args:
        new_invigilator_boxes: List of numpy arrays [x1, y1, x2, y2] from
                               current frame's YOLO invigilator detections.
    """
    global invigilator_ghost_boxes, invigilator_ghost_ttl

    with invigilator_ghost_lock:
        # PHASE A: Try to match each new detection to a nearby existing ghost.
        # If matched, update the ghost position and reset its TTL to 20.
        # refreshed_ghost_indices tracks which ghost LIST INDICES were matched
        # this frame. Only these indices are exempt from TTL decrement in Phase D.
        matched_new_indices = set()
        refreshed_ghost_indices = set()  # FIX: explicit set of matched ghost indices
        for i, ghost_box in enumerate(invigilator_ghost_boxes):
            gc_x = (ghost_box[0] + ghost_box[2]) // 2
            gc_y = (ghost_box[1] + ghost_box[3]) // 2

            for j, new_box in enumerate(new_invigilator_boxes):
                if j in matched_new_indices:
                    continue  # This new box is already matched to another ghost
                nc_x = (new_box[0] + new_box[2]) // 2
                nc_y = (new_box[1] + new_box[3]) // 2
                dist = ((nc_x - gc_x) ** 2 + (nc_y - gc_y) ** 2) ** 0.5

                if dist < 150:  # Within 150px: treat as the same invigilator
                    invigilator_ghost_boxes[i] = new_box  # Refresh position
                    invigilator_ghost_ttl[i] = 20          # Reset TTL countdown
                    matched_new_indices.add(j)
                    refreshed_ghost_indices.add(i)  # FIX: mark this ghost as refreshed
                    break

        # PHASE B: Add completely new invigilators (no nearby ghost found).
        for j, new_box in enumerate(new_invigilator_boxes):
            if j not in matched_new_indices:
                next_idx = len(invigilator_ghost_boxes)
                invigilator_ghost_boxes.append(new_box)
                invigilator_ghost_ttl[next_idx] = 20
                refreshed_ghost_indices.add(next_idx)  # New ghosts are exempt from decrement
                print(f"[GHOST] New invigilator ghost created (index={next_idx})")

        # PHASE D: Rebuild ghost list — keep only survivors (TTL > 0 after decrement).
        # Ghosts in refreshed_ghost_indices keep their TTL unchanged.
        # All other ghosts are decremented by 1. Ghosts reaching TTL=0 are purged.
        surviving_boxes = []
        surviving_ttls = {}
        for i, box in enumerate(invigilator_ghost_boxes):
            current_ttl = invigilator_ghost_ttl.get(i, 0)
            # FIX: use set membership, not TTL value, to decide if ghost was refreshed
            is_refreshed = (i in refreshed_ghost_indices)
            new_ttl = current_ttl if is_refreshed else current_ttl - 1

            if new_ttl > 0:
                new_idx = len(surviving_boxes)
                surviving_boxes.append(box)
                surviving_ttls[new_idx] = new_ttl
            else:
                print(f"[GHOST] Invigilator ghost expired and removed (was index={i})")

        # Replace global lists with the clean survivor set
        invigilator_ghost_boxes.clear()
        invigilator_ghost_boxes.extend(surviving_boxes)
        invigilator_ghost_ttl.clear()
        invigilator_ghost_ttl.update(surviving_ttls)


def calculate_iomin(box_a, box_b):
    """
    Calculates Intersection over Minimum Area (IoMin).

    Unlike standard IoU (Intersection over Union), IoMin measures what
    fraction of the SMALLER box is covered by the intersection.
    This is critical when comparing a small face box against a large
    invigilator body box — standard IoU would give near-zero values
    even when the face is fully inside the body box.

    Args:
        box_a: [x1, y1, x2, y2] — first bounding box
        box_b: [x1, y1, x2, y2] — second bounding box

    Returns:
        float in range [0.0, 1.0] — 1.0 means smaller box fully inside larger
    """
    # Calculate intersection rectangle
    ix1 = max(box_a[0], box_b[0])
    iy1 = max(box_a[1], box_b[1])
    ix2 = min(box_a[2], box_b[2])
    iy2 = min(box_a[3], box_b[3])

    inter_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter_area == 0:
        return 0.0

    # Calculate individual areas (guard against zero-area degenerate boxes)
    area_a = max(1, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(1, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))

    # Divide by the MINIMUM area — this answers: "how much of the smaller box
    # is occupied by the intersection?" Perfect for face-inside-body detection.
    return inter_area / min(area_a, area_b)


def is_face_inside_invigilator(face_box, ghost_boxes, threshold=0.4):
    """
    Returns True if a detected peeking face belongs to the invigilator.

    For each ghost box, we expand it by 15% margin (to handle slight
    misalignment between YOLO's body detection and the face mesh box),
    then calculate IoMin against the face box.

    If IoMin > threshold (default 0.4 = 40% of the face is inside the
    invigilator's expanded box), we conclude this face IS the invigilator
    and suppress the peeking alarm.

    Args:
        face_box:     [x1, y1, x2, y2] — from MediaPipe FaceMesh
        ghost_boxes:  List of [x1, y1, x2, y2] — invigilator ghost positions
        threshold:    IoMin threshold for suppression decision (default 0.4)

    Returns:
        bool — True means "this is the invigilator's face, suppress alarm"
    """
    for ghost_box in ghost_boxes:
        gx1, gy1, gx2, gy2 = int(ghost_box[0]), int(ghost_box[1]), \
                               int(ghost_box[2]), int(ghost_box[3])

        # Expand ghost box by 15% margin in all directions.
        # Reason: YOLO body boxes often cut off the top of the head, so the
        # face mesh bounding box (which includes forehead/hair) might extend
        # slightly above/outside the raw YOLO box.
        gw = gx2 - gx1
        gh = gy2 - gy1
        mx = int(gw * 0.15)  # 15% horizontal margin
        my = int(gh * 0.15)  # 15% vertical margin
        expanded_box = [gx1 - mx, gy1 - my, gx2 + mx, gy2 + my]

        iomin = calculate_iomin(face_box, expanded_box)
        if iomin > threshold:
            return True  # Face is sufficiently inside the invigilator box

    return False  # No ghost box matched — this is a student's face


# ==============================================================================
# FACE TRACKER — MODEL A PHASE 2
# ==============================================================================

def match_face_to_track(new_box, iou_threshold=0.2):
    """
    Finds an existing face track that matches new_box using standard IoU.

    We use standard IoU here (not IoMin) because both boxes being compared
    are face-sized — they have roughly equal areas, so standard IoU is correct.

    Args:
        new_box: [x1, y1, x2, y2] — face box from current MediaPipe output
        iou_threshold: Minimum IoU to consider same face (default 0.3)

    Returns:
        face_id (int) if a match is found, None if this is a new face
    """
    best_iou = 0.0
    best_face_id = None

    for face_id, track in face_tracks.items():
        tb = track['box']  # Previous frame's box for this tracked face
        # Standard IoU: intersection / union
        ix1 = max(new_box[0], tb[0])
        iy1 = max(new_box[1], tb[1])
        ix2 = min(new_box[2], tb[2])
        iy2 = min(new_box[3], tb[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            continue
        area_new = max(1, (new_box[2]-new_box[0]) * (new_box[3]-new_box[1]))
        area_tb  = max(1, (tb[2]-tb[0]) * (tb[3]-tb[1]))
        iou = inter / (area_new + area_tb - inter)
        if iou > best_iou:
            best_iou = iou
            best_face_id = face_id

    if best_iou >= iou_threshold:
        return best_face_id
    return None  # No close enough match — treat as new face


def update_face_tracks(detected_face_boxes):
    """
    Updates the face_tracks registry for each detected peeking face.

    For each new face box:
      - If IoU-matched to existing track: update position, reset frames_lost to 0
      - If no match: create a new track with a fresh face_id
    For all tracks NOT updated: increment frames_lost
    Tracks with frames_lost > 45 are purged (face genuinely gone/new person)

    Args:
        detected_face_boxes: List of [x1, y1, x2, y2] from peeking MediaPipe detections

    Returns:
        box_to_face_id: dict mapping tuple(box) -> face_id for this frame's faces
    """
    global face_tracks, face_id_counter

    box_to_face_id = {}  # Maps each detected box to an assigned face_id
    updated_ids = set()  # Tracks which face_ids were refreshed this frame

    for box in detected_face_boxes:
        face_id = match_face_to_track(box)
        if face_id is not None:
            # Existing face re-detected: update its position and reset lost counter
            face_tracks[face_id]['box'] = box
            face_tracks[face_id]['last_seen_frame'] = current_frame_number
            face_tracks[face_id]['frames_lost'] = 0
            updated_ids.add(face_id)
        else:
            # Brand new face: create a new track entry
            face_id_counter += 1
            face_id = face_id_counter
            face_tracks[face_id] = {
                'box': box,
                'last_seen_frame': current_frame_number,
                'frames_lost': 0
            }
            updated_ids.add(face_id)
            print(f"[FACE TRACKER] New face track created: face_id={face_id}")

        box_to_face_id[tuple(box)] = face_id

    # Increment frames_lost for tracks not seen this frame
    # Purge tracks that have been missing for more than 45 frames (~3s at 15fps)
    to_delete = []
    for face_id, track in face_tracks.items():
        if face_id not in updated_ids:
            track['frames_lost'] += 1
            if track['frames_lost'] > 45:
                to_delete.append(face_id)

    for face_id in to_delete:
        del face_tracks[face_id]
        # Also clean up suspicion state for this face — they've left the frame
        if face_id in student_suspicion:
            del student_suspicion[face_id]
        print(f"[FACE TRACKER] Face track expired: face_id={face_id}")

    return box_to_face_id


# ==============================================================================
# SUSPICION STATE MACHINE — MODEL A PHASE 2
# ==============================================================================

def update_suspicion_state(face_id, yaw, timestamp):
    """
    Cumulative sideways-time tracker per face across a 30-second session window.

    Accumulation logic:
      - While the student is continuously looking sideways, we add the time
        delta to total_sideways_time each frame.
      - If they look forward and then back within 30 seconds, we CONTINUE
        accumulating (the session is still active).
      - If more than 30 seconds pass since the last sideways look, the session
        resets to 0 — this is treated as a genuine break, not cheating.

    Alert levels:
      'clean'    : total_sideways_time < 0.5s
      'warning'  : 0.5s <= total_sideways_time < 3.0s  (Quick Glance)
      'critical' : total_sideways_time >= 3.0s          (Signaling)
      A 'directional' suffix is added if one direction dominates (3x the other)

    Args:
        face_id:   int — the tracked face's unique ID
        yaw:       float — head yaw angle from MediaPipe PnP solver
        timestamp: float — current time.time() value

    Returns:
        tuple: (alert_level: str, total_sideways_time: float)
    """
    global student_suspicion

    # Initialize suspicion state for new face
    if face_id not in student_suspicion:
        student_suspicion[face_id] = {
            'sideways_timestamps': [],     # List of float timestamps where yaw > 30° detected
            'window_duration': 5.0,        # Rolling window size in seconds
            'direction_counts': {'left': 0, 'right': 0},
            'alert_level': 'clean',
            'last_alert_time': 0.0,
            'session_start': timestamp
        }

    state = student_suspicion[face_id]

    # Natural session reset: if no sideways timestamps in last 30 seconds
    # the student has been looking forward — prune will have cleared the list
    # No explicit reset needed — sliding window handles this automatically
    # However reset direction_counts if student has been clean for 30s
    if state['sideways_timestamps']:
        most_recent = state['sideways_timestamps'][-1]
        if timestamp - most_recent > 30.0:
            state['direction_counts'] = {'left': 0, 'right': 0}
            print(f"[SUSPICION] face_id={face_id}: 30s clean — resetting direction counts")

    window_duration = state['window_duration']  # 5.0 seconds

    # Step 1: Add current timestamp to sideways list
    # (This function is ONLY called when yaw > 30°, so every call = sideways frame)
    state['sideways_timestamps'].append(timestamp)

    # Step 2: Prune timestamps outside the rolling window
    # Only keep timestamps from the last 5 seconds
    window_start = timestamp - window_duration
    state['sideways_timestamps'] = [
        t for t in state['sideways_timestamps']
        if t >= window_start
    ]

    # Step 3: Calculate sideways coverage in current window
    # Each timestamp represents one detected sideways frame
    # Average detection interval is ~0.066s (every 2nd frame at 30fps)
    # Use actual time span if enough timestamps exist
    ts_list = state['sideways_timestamps']
    if len(ts_list) >= 2:
        # Use time span between first and last timestamp in window
        # Add one frame interval to include the last frame itself
        sideways_coverage = (ts_list[-1] - ts_list[0]) + 0.066
    elif len(ts_list) == 1:
        sideways_coverage = 0.066  # Single frame detected
    else:
        sideways_coverage = 0.0

    # Step 4: Update direction counts
    direction = 'right' if yaw > 0 else 'left'
    state['direction_counts'][direction] += 1

    # Determine alert level from sideways coverage in window
    if sideways_coverage >= 3.0:
        alert_level = 'critical'
    else:
        alert_level = 'clean'

    # Directional flag — only on critical
    left_c = state['direction_counts']['left']
    right_c = state['direction_counts']['right']
    if alert_level == 'critical' and (left_c > 0 and right_c > 0):
        ratio = max(left_c, right_c) / min(left_c, right_c)
        if ratio >= 3.0:
            alert_level = 'critical_directional'

    state['alert_level'] = alert_level
    return (alert_level, round(sideways_coverage, 2))





# ==============================================================================
# MUTUAL GAZE DETECTION — MODEL A PHASE 3
# ==============================================================================

def classify_gaze_direction(face_box, yaw, frame_width):
    """
    Classify rough gaze direction based on yaw constraint.
    'forward' if abs(yaw) < 25°
    'left' if yaw < -25°
    'right' if yaw > 25°
    """
    cx = (face_box[0] + face_box[2]) // 2
    cy = (face_box[1] + face_box[3]) // 2
    
    looking = 'forward'
    if yaw < -25:
        looking = 'left'
    elif yaw > 25:
        looking = 'right'
        
    return {
        'center_x': cx,
        'center_y': cy,
        'looking': looking,
        'yaw': yaw
    }


def find_mutual_gaze_pairs(gaze_classifications):
    """
    Identifies if two students are looking at each other simultaneously.
    """
    pairs = []
    rights = [g for g in gaze_classifications if g['looking'] == 'right']
    lefts = [g for g in gaze_classifications if g['looking'] == 'left']
    
    for r in rights:
        for l in lefts:
            # Face A (looking right) must be physically to the left of Face B (looking left)
            if r['center_x'] < l['center_x']:
                h_dist = l['center_x'] - r['center_x']
                v_dist = abs(r['center_y'] - l['center_y'])
                
                # Apply spatial constraints (prevent cross-room false positives)
                if h_dist <= MUTUAL_GAZE_MAX_DISTANCE and v_dist <= MUTUAL_GAZE_MAX_VERTICAL:
                    face_a_id = r['face_id']
                    face_b_id = l['face_id']
                    
                    # Consistent primary key constraint: min_max ID sort
                    fid1 = min(face_a_id, face_b_id)
                    fid2 = max(face_a_id, face_b_id)
                    
                    pairs.append({
                        'face_a_id': face_a_id,
                        'face_b_id': face_b_id,
                        'pair_key': f"{fid1}_{fid2}"
                    })
    return pairs


def update_mutual_gaze_sessions(current_pairs, timestamp):
    """
    Maintains active mutual gaze sessions across frames allowing up to 2.0s breaks.
    """
    global mutual_gaze_sessions
    alert_pairs = []
    
    current_pair_keys = {p['pair_key'] for p in current_pairs}
    
    for pair in current_pairs:
        pk = pair['pair_key']
        if pk in mutual_gaze_sessions:
            session = mutual_gaze_sessions[pk]
            session['duration'] = timestamp - session['start_time']
            session['last_seen'] = timestamp
        else:
            mutual_gaze_sessions[pk] = {
                'start_time': timestamp,
                'duration': 0.0,
                'last_seen': timestamp,
                'alert_fired': False
            }
            
    keys_to_remove = []
    for pk, session in mutual_gaze_sessions.items():
        if pk not in current_pair_keys:
            if timestamp - session['last_seen'] > 2.0:
                # Gaze broken for > 2 seconds, remove entirely
                keys_to_remove.append(pk)
        
        # Determine duration alert
        if session['duration'] >= 3.0 and not session['alert_fired']:
            session['alert_fired'] = True
            matching_pair = next((p for p in current_pairs if p['pair_key'] == pk), None)
            if matching_pair:
                alert_pairs.append(matching_pair)

    for pk in keys_to_remove:
        del mutual_gaze_sessions[pk]
        
    return alert_pairs


def save_mutual_gaze_evidence(frame, face_a_box, face_b_box, duration):
    """
    Saves screenshot of a captured mutual gaze with line indicator and bounding boxes.
    """
    global violations_log
    original_frame = frame
    evidence_frame = get_best_evidence_frame(original_frame)
    
    is_fallback = (evidence_frame is original_frame)
    if is_fallback:
        evidence_frame = cv2.flip(evidence_frame, 1)
        
    dh, dw = original_frame.shape[:2]
    eh, ew = evidence_frame.shape[:2]
    scale = ew / dw
    
    def map_box(box):
        sx1, sy1, sx2, sy2 = box[0] * scale, box[1] * scale, box[2] * scale, box[3] * scale
        return [int(max(0, ew - sx2)), int(max(0, sy1)), int(min(ew, ew - sx1)), int(min(eh, sy2))]
        
    face_a_box = map_box(face_a_box)
    face_b_box = map_box(face_b_box)
    
    evidence_frame = evidence_frame.copy()
    h, w = evidence_frame.shape[:2]
    
    ca = ((face_a_box[0] + face_a_box[2]) // 2, (face_a_box[1] + face_a_box[3]) // 2)
    cb = ((face_b_box[0] + face_b_box[2]) // 2, (face_b_box[1] + face_b_box[3]) // 2)
    
    box_color = (0, 0, 255) # Red
    
    cv2.rectangle(evidence_frame, (face_a_box[0], face_a_box[1]), (face_a_box[2], face_a_box[3]), box_color, 3)
    cv2.rectangle(evidence_frame, (face_b_box[0], face_b_box[1]), (face_b_box[2], face_b_box[3]), box_color, 3)
    cv2.line(evidence_frame, ca, cb, box_color, 3)
    
    # Bottom HUD
    cv2.rectangle(evidence_frame, (0, h-65), (w, h), (0, 0, 0), -1)
    ts = datetime.now().strftime("%H:%M:%S")
    
    cv2.putText(evidence_frame, "CRITICAL: MUTUAL SIGNALING DETECTED", (10, h-38), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)
    cv2.putText(evidence_frame, f"Duration: {duration:.1f}s", (10, h-12), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    now = time.time()
    img_path = os.path.join(get_report_dir(), f"mutual_signal_{int(now)}.jpg")
    cv2.imwrite(img_path, evidence_frame)
    
    trigger_alert()
    
    violations_log.append({
        "time": ts,
        "type": "Mutual Signaling",
        "conf": 1.0
    })
    
    print(f"📸 Evidence saved: {os.path.basename(img_path)} [Mutual Signaling]")


# ==============================================================================
# PHONE TRACKER — MULTI-PHONE STATE MACHINE
# ==============================================================================

def match_phone_to_track(new_box, iou_threshold=0.2):
    best_iou = 0.0
    best_phone_id = None
    for phone_id, track in phone_tracks.items():
        tb = track['box']
        ix1 = max(new_box[0], tb[0])
        iy1 = max(new_box[1], tb[1])
        ix2 = min(new_box[2], tb[2])
        iy2 = min(new_box[3], tb[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            continue
        area_new = max(1, (new_box[2]-new_box[0]) * (new_box[3]-new_box[1]))
        area_tb  = max(1, (tb[2]-tb[0]) * (tb[3]-tb[1]))
        iou = inter / (area_new + area_tb - inter)
        if iou > best_iou:
            best_iou = iou
            best_phone_id = phone_id

    if best_iou >= iou_threshold:
        return best_phone_id
    return None

def update_phone_tracks(detected_phone_boxes):
    global phone_tracks, phone_id_counter
    
    box_to_phone_id = {}
    updated_ids = set()
    
    for box in detected_phone_boxes:
        phone_id = match_phone_to_track(box)
        if phone_id is not None:
            phone_tracks[phone_id]['box'] = box
            phone_tracks[phone_id]['frames_lost'] = 0
            phone_tracks[phone_id]['consecutive_frames'] += 1
            updated_ids.add(phone_id)
        else:
            phone_id_counter += 1
            phone_id = phone_id_counter
            phone_tracks[phone_id] = {
                'box': box,
                'frames_lost': 0,
                'consecutive_frames': 1,
                'alarm_fired_at': 0.0,
                'incident_active': False
            }
            updated_ids.add(phone_id)
            print(f"[PHONE TRACKER] New phone track created: phone_id={phone_id}")
            
        box_to_phone_id[tuple(box)] = phone_id

    to_delete = []
    for phone_id, track in phone_tracks.items():
        if phone_id not in updated_ids:
            track['frames_lost'] += 1
            track['consecutive_frames'] = 0  # reset debounce if lost
            # If absent for >2 seconds (~30 frames at 15fps), silence the alarm
            if track['frames_lost'] > 30:
                if track['incident_active']:
                    track['incident_active'] = False
                    print(f"[PHONE TRACKER] Phone {phone_id} absent >2s — incident resolved")
            # If absent for >60 seconds (~900 frames), forget the phone completely
            if track['frames_lost'] > 900:
                to_delete.append(phone_id)
                
    for phone_id in to_delete:
        del phone_tracks[phone_id]
        print(f"[PHONE TRACKER] Phone track expired: phone_id={phone_id}")

    return box_to_phone_id


def run_async_detection(frame_input, full_res_frame=None):
    """
    MODEL A - PHASE 1 + PHASE 2: Ghost Box Suppression + Face Tracking State Machine.

    Execution order:
    STEP 0 → Increment current_frame_number (frame clock for tracker).
    STEP 1 → YOLO first: invigilator ghost boxes + mobile phone evidence.
    STEP 2 → Update ghost registry with this frame's invigilator data.
    STEP 3 → MediaPipe: detect all turning faces.
    STEP 4 → Phase 1 Sensor Fusion: suppress invigilator faces via IoMin.
    STEP 5 → Phase 2 Face Tracking: assign face_ids to peeking detections.
    STEP 6 → Phase 2 Suspicion State Machine: accumulate sideways time per face.
    STEP 7 → Evidence saving with alert_level from state machine.
    """
    global is_detecting, latest_detections, violations_log, current_frame_number

    try:
        # ==================================================================
        # STEP 0: Advance frame clock (used by face tracker for TTL)
        # ==================================================================
        current_frame_number += 1

        # Guard: don't process if session has ended (prevents post-session evidence saving)
        if not session_active and current_source != 0:
            is_detecting = False
            return

        current_frame_dets = []

        # ==================================================================
        # STEP 1: RUN YOLO — Invigilator ghost box + mobile phone detection
        # ==================================================================
        results = model.predict(frame_input, conf=0.25, iou=0.45, verbose=False)
        this_frame_invigilator_boxes = []
        this_frame_phone_boxes = []
        this_frame_phone_confs = {}

        for r in results:
            for box in r.boxes:
                lbl = model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                c = box.xyxy[0].cpu().numpy().astype(int)

                if lbl == 'invigilator' and conf >= invigilator_threshold:
                    this_frame_invigilator_boxes.append(c)
                    current_frame_dets.append({'label': lbl, 'conf': conf, 'box': c})

                # Mobile phone detection — extract boxes for spatial tracking
                elif lbl == 'mobile_phone' and conf >= confidence_threshold:
                    this_frame_phone_boxes.append(c)
                    this_frame_phone_confs[tuple(c)] = conf
                    current_frame_dets.append({
                        'label': lbl, 'conf': conf, 'box': c
                    })

        # ── MULTI-PHONE STATE MACHINE (Spatial Tracking) ─────────────
        now_phone = time.time()
        with phone_tracker_lock:
            box_to_phone_id = update_phone_tracks(this_frame_phone_boxes)
            
            for box in this_frame_phone_boxes:
                box_tuple = tuple(box)
                phone_id = box_to_phone_id[box_tuple]
                track = phone_tracks[phone_id]
                conf = this_frame_phone_confs[box_tuple]
                
                # Layer 1 — Debounce: require 3 consecutive frames
                if track['consecutive_frames'] >= 3:
                    if not track['incident_active']:
                        # Layer 3 — Incident cooldown per phone: 15 seconds
                        since_last = now_phone - track['alarm_fired_at']
                        if since_last >= 15.0:
                            # ✅ NEW INCIDENT for this specific phone
                            track['incident_active'] = True
                            track['alarm_fired_at'] = now_phone

                            # Save evidence (screenshot + beep)
                            evidence_path = save_evidence_smart(
                                frame_input, 'mobile_phone', box, conf
                            )
                            if evidence_path:
                                with violations_lock:
                                    violations_log.append({
                                        "time": datetime.now().strftime("%H:%M:%S"),
                                        "type": "Mobile Phone",
                                        "conf": round(conf, 2),
                                        "alert_level": "critical",
                                        "phone_id": phone_id # Add to log for tracking
                                    })
                                print(f"🚨 [PHONE] NEW INCIDENT (ID {phone_id}) — alarm fired, 15s cooldown started")
                        else:
                            print(f"[PHONE] Cooldown active for ID {phone_id} — {15.0 - since_last:.1f}s remaining")
        # ─────────────────────────────────────────────────────────────

        # ==================================================================
        # STEP 2: Update ghost registry
        # ==================================================================
        update_invigilator_ghosts(this_frame_invigilator_boxes)

        # ==================================================================
        # STEP 3: MediaPipe — all turning faces
        # ==================================================================
        mediapipe_frame = full_res_frame if full_res_frame is not None else frame_input
        peeking_results = detect_peeking_mediapipe(mediapipe_frame)

        # ==================================================================
        # STEP 4: Phase 1 Sensor Fusion — suppress invigilator faces
        # ==================================================================
        with invigilator_ghost_lock:
            current_ghost_snapshot = list(invigilator_ghost_boxes)

        student_peeking = []
        for p_det in peeking_results:
            if is_face_inside_invigilator(p_det['box'], current_ghost_snapshot):
                print(f"[SUPPRESSED] Invigilator head turn ignored "
                      f"(IoMin, ghost_count={len(current_ghost_snapshot)})")
            else:
                student_peeking.append(p_det)
                current_frame_dets.append(p_det)

        with detection_lock:
            latest_detections = list(current_frame_dets)

        # ==================================================================
        # STEP 5: Phase 2 — IoU Face Tracking
        # Get face_id for each confirmed student peeking detection.
        # Only peeking faces are tracked — not all faces in frame.
        # ==================================================================
        peeking_face_boxes = [p['box'] for p in student_peeking]
        box_to_face_id = update_face_tracks(peeking_face_boxes)

        # ==================================================================
        # STEP 6 + 7: Suspicion state machine + evidence saving per face
        # ==================================================================
        now = time.time()
        for p_det in student_peeking:
            box_key = tuple(p_det['box'])
            face_id = box_to_face_id.get(box_key)
            yaw     = p_det.get('yaw', 0)

            # Run suspicion accumulator for this face
            alert_level, total_time = update_suspicion_state(face_id, yaw, now)

            # Save evidence only if alert warrants it (not 'clean')
            if 'critical' in alert_level:
                evidence_path = save_evidence_smart(
                    frame_input, 'peeking', p_det['box'],
                    p_det['conf'],
                    display_label=p_det['display_label'],
                    alert_level=alert_level,
                    face_id=face_id
                )
                if evidence_path:
                    # Map alert_level to a human-readable log entry
                    if 'directional' in alert_level:
                        log_type = 'Directional Signaling'
                    else:
                        log_type = 'Signaling Detected'

                    violations_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "type": log_type,
                        "conf": round(p_det['conf'], 2),
                        "detection_score": round(p_det['conf'], 2),
                        "alert_level": alert_level,
                        "face_id": face_id,
                        "total_sideways_time": total_time
                    })
                    global unique_face_ids_seen
                    if face_id is not None:
                        unique_face_ids_seen.add(face_id)



        # ==================================================================
        # STEP 8: Phase 3 — Mutual Gaze / Signaling Detection
        # ==================================================================
        frame_width = frame_input.shape[1]
        gaze_classifications = []
        for p_det in student_peeking:
            face_box = p_det['box']
            yaw = p_det.get('yaw', 0)
            face_id = box_to_face_id.get(tuple(face_box))
            
            if face_id is not None:
                g_class = classify_gaze_direction(face_box, yaw, frame_width)
                g_class['face_id'] = face_id
                gaze_classifications.append(g_class)

        current_pairs = find_mutual_gaze_pairs(gaze_classifications)
        alert_pairs = update_mutual_gaze_sessions(current_pairs, now)

        for pair in alert_pairs:
            fid_a = pair['face_a_id']
            fid_b = pair['face_b_id']
            if fid_a in face_tracks and fid_b in face_tracks:
                box_a = face_tracks[fid_a]['box']
                box_b = face_tracks[fid_b]['box']
                duration = mutual_gaze_sessions[pair['pair_key']]['duration']
                save_mutual_gaze_evidence(frame_input, box_a, box_b, duration)

        # Final display refresh + housekeeping
        with detection_lock:
            latest_detections = current_frame_dets

        # Prune stale peeking cooldown entries older than 60s to prevent unbounded growth
        now_prune = time.time()
        stale_keys = [k for k, t in _peek_cooldowns.items() if now_prune - t > 60.0]
        for k in stale_keys:
            del _peek_cooldowns[k]

    except Exception as e:
        print(f"⚠️ Async Detection Error: {e}")
    finally:
        is_detecting = False


def generate():
    """
    Video stream generator with improved camera handling
    Supports: Live camera, uploaded videos, and static images
    """
    global current_source, active_camera

    # Check if source is set
    if current_source is None:
        return

    # --- IMAGE LOGIC ---
    if isinstance(current_source, str) and current_source.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            frame = cv2.imread(current_source)
            if frame is None:
                print(f"❌ Failed to read image: {current_source}")
                return

            # Convert 4-channel PNG to 3-channel BGR
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # Check if this is already a processed image (has boxes drawn)
            # If so, SKIP detection to avoid double boxes
            detection_count = 0
            if 'processed_' in os.path.basename(current_source):
                # Just stream the image as-is
                pass
            else:
                # Run detection only for raw images
                results = model.predict(
                    frame, conf=invigilator_threshold, verbose=False)

                detection_count = 0
                for r in results:
                    for box in r.boxes:
                        lbl = model.names[int(box.cls[0])]
                        conf = float(box.conf[0])
                        c = box.xyxy[0].cpu().numpy().astype(int)

                        # Determine color and thickness based on class
                        if lbl == 'invigilator':
                            color = (255, 0, 0)  # Blue for invigilator
                            thickness = 2
                        elif lbl in ['mobile_phone']:
                            color = (0, 0, 255)  # Red for violations
                            thickness = 3
                        else:
                            color = (0, 255, 0)  # Green for others
                            thickness = 2

                        # Draw bounding box
                        cv2.rectangle(
                            frame, (c[0], c[1]), (c[2], c[3]), color, thickness)

                        # Add label with confidence score
                        label_text = f"{lbl.replace('_', ' ')}: {int(conf * 100)}%"

                        # Background for text
                        (text_w, text_h), _ = cv2.getTextSize(
                            label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        cv2.rectangle(
                            frame, (c[0], c[1] - text_h - 10), (c[0] + text_w + 10, c[1]), color, -1)

                        # Draw text
                        cv2.putText(frame, label_text, (c[0] + 5, c[1] - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                        detection_count += 1

                print(
                    f"🔍 Image analysis: {detection_count} detection(s) found")

                # --- MEDIAPIPE PEEKING CHECK (Image Preview) ---
                peeking_results = detect_peeking_mediapipe(frame)
                for p_det in peeking_results:
                    bx1, by1, bx2, by2 = p_det['box']
                    display_lbl = p_det['display_label']
                    color = (0, 0, 255)

                    # Thinner Box
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), color, 2)
                    label_text = f"{display_lbl}: {int(p_det['conf'] * 100)}%"

                    (text_w, text_h), _ = cv2.getTextSize(
                        label_text, cv2.FONT_HERSHEY_DUPLEX, 0.5, 1)

                    # Smart Positioning for Image
                    t_y = by1 - 10 if by1 > 30 else by1 + text_h + 10
                    cv2.rectangle(frame, (bx1, t_y - text_h - 5),
                                  (bx1 + text_w + 10, t_y + 5), color, -1)
                    cv2.putText(frame, label_text, (bx1 + 5, t_y),
                                cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)


                    detection_count += 1

            # Encode and stream
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            while True:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error processing image: {str(e)}")
            return

    # --- VIDEO / LIVE LOGIC ---
    cap = None

    try:
        # Live camera mode
        if current_source == 0:
            with camera_lock:
                # Release any existing camera
                if active_camera is not None:
                    active_camera.release()
                    active_camera = None

                # Initialize new camera
                cap = initialize_camera()
                if cap is None:
                    print("❌ Failed to initialize camera")
                    return

                active_camera = cap

        # Uploaded video mode
        else:
            cap = cv2.VideoCapture(current_source)
            if not cap.isOpened():
                print(f"❌ Failed to open video: {current_source}")
                return

        print("✅ Video stream started (Async Mode)")

        # Global state reset
        global is_detecting, latest_detections
        is_detecting = False
        latest_detections = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ End of stream")
                break

            # Store valid frame in rolling buffer for evidence saving
            # Stored BEFORE flip and resize so evidence images are full resolution
            # and correctly oriented (not mirrored)
            with frame_buffer_lock:
                frame_buffer.append(frame.copy())
                if len(frame_buffer) > FRAME_BUFFER_SIZE:
                    frame_buffer.pop(0)

            # Mirror Effect: Flip frame horizontally for natural view
            frame = cv2.flip(frame, 1)

            # Smart Resize for Display (Optional, but keeps encoding fast)
            # If 1080p, resize to 720p for viewing
            if frame.shape[1] > 1280:
                frame = cv2.resize(
                    frame, (1280, int(frame.shape[0] * 1280 / frame.shape[1])))

            # --- FRAME SKIP LOGIC FOR PERFORMANCE ---
            global frame_skip_counter
            frame_skip_counter += 1
            should_process = (frame_skip_counter % PROCESS_EVERY_N_FRAMES == 0)

            # --- ASYNC INFERENCE TRIGGER ---
            # If no detection is currently running AND it's time to process, start one
            if not is_detecting and should_process:
                is_detecting = True

                # YOLO input: 640px for fast inference
                yolo_input = frame.copy()
                yolo_h, yolo_w = yolo_input.shape[:2]
                if yolo_w > 640:
                    yolo_input = cv2.resize(
                        yolo_input, (640, int(yolo_h * 640 / yolo_w))
                    )

                # MediaPipe input: 1280px for reliable multi-face detection
                mediapipe_input = frame.copy()
                mp_h, mp_w = mediapipe_input.shape[:2]
                if mp_w > 1280:
                    mediapipe_input = cv2.resize(
                        mediapipe_input, (1280, int(mp_h * 1280 / mp_w))
                    )

                Thread(
                    target=run_async_detection,
                    args=(yolo_input, mediapipe_input)
                ).start()

            # --- DRAWING (Non-Blocking) ---
            # Retrieve latest available results
            with detection_lock:
                current_dets = list(latest_detections)  # Weak copy

            # Map detections back to current frame size
            # (Note: This simple mapping assumes aspect ratio is preserved and detection was on similar frame)
            # Since video is continuous, mapping detection logic from t-1 to t is acceptable visually.

            # If we resized the detection input, we'd need to scale boxes up.
            # But currently `latest_detections` are in 640px coordinates.
            # We need scaling factors if frame is not 640px.

            fh, fw = frame.shape[:2]
            # Calculate scale relative to the 640px base we used for detection
            # If we didn't resize in async input, scale is 1. But we DID resize to max 640 width logic.
            scale_x = fw / 640 if fw > 640 else 1.0
            scale_y = fh / (640 * fh / fw) if fw > 640 else 1.0
            # Simplified: just re-calculate based on width if we forced width
            if fw > 640:
                scale = fw / 640
            else:
                scale = 1.0

            for det in current_dets:
                lbl = det['label']
                conf = det['conf']
                box = det['box']  # [x1, y1, x2, y2]

                # Scale Coordinates
                x1 = int(box[0] * scale)
                y1 = int(box[1] * scale)
                x2 = int(box[2] * scale)
                y2 = int(box[3] * scale)

                # Drawing Logic
                if lbl == 'invigilator':
                    color = (255, 165, 0)   # Orange box
                    thickness = 2
                    display_text = f"Invigilator {int(conf * 100)}%"
                elif lbl == 'mobile_phone':
                    color = (0, 0, 255)     # Red box
                    thickness = 3
                    display_text = f"PHONE {int(conf * 100)}%"
                elif lbl == 'peeking':
                    color = (0, 0, 255)     # Red box
                    thickness = 3
                    display_lbl = det.get('display_label', lbl)
                    display_text = f"{display_lbl}: {int(conf * 100)}%"
                    if 'yaw' in det:
                        display_text += f" ({int(det['yaw'])} deg)"
                else:
                    color = (0, 255, 0)
                    thickness = 2
                    display_text = f"{lbl.replace('_', ' ')}: {int(conf * 100)}%"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                (text_w, text_h), _ = cv2.getTextSize(
                    display_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

                # If box is too close to top, draw label INSIDE the box
                t_y = y1 - 8 if y1 > 25 else y1 + text_h + 8

                cv2.rectangle(frame, (x1, t_y - text_h - 4),
                              (x1 + text_w + 8, t_y + 4), color, -1)
                cv2.putText(frame, display_text, (x1 + 4, t_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

            # Encode & yield immediately
            try:
                _, buffer = cv2.imencode(
                    '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

            except Exception as ev:
                print(f"Encoding Error: {ev}")
                break

    except Exception as e:
        print(f"❌ Stream error: {str(e)}")

    finally:
        # Cleanup
        if cap is not None and current_source != 0:
            cap.release()
            print("📹 Video capture released")
        print("🛑 Stream ended")

# --- AUTHENTICATION HELPERS ---
def load_users():
    """Load users from JSON file"""
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'redirect': url_for('login_page')}), 401

            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


# --- ROUTES ---

@app.route('/')
def login_page():
    if 'user' in session:
        return redirect(url_for('selection'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form.get('username')
    password = request.form.get('password')

    users = load_users()

    if username in users and check_password_hash(users[username]['password'], password):
        session['user'] = username
        session['role'] = users[username]['role']

        # --- NEW SESSION INIT ---
        global current_session_id, violations_log, active_violations
        current_session_id = f"Session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        violations_log = []
        active_violations = {}
        print(f"✅ New Session Started: {current_session_id}")

        print(f"✅ User logged in: {username}")
        return redirect(url_for('selection'))

    # Login failed
    return render_template('login.html', error="Invalid username or password")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/select_camera')
@login_required
def select_camera():
    """Display available cameras for selection"""
    cameras = get_available_cameras()
    return render_template('select_camera.html', cameras=cameras)


@app.route('/set_camera/<int:camera_id>', methods=['POST'])
@login_required
def set_camera(camera_id):
    """Set the active camera for proctoring"""
    global selected_camera_index, active_camera, is_detecting
    
    # 1. Stop detection briefly
    is_detecting = False
    
    # 2. Update the index
    selected_camera_index = camera_id
    
    # 3. Release old camera so the generate loop can reconfirm it
    release_camera()
    
    print(f"📹 Selected Camera Index updated to: {camera_id}")
    return jsonify({"status": "success", "camera_id": camera_id})


@app.route('/selection')
@login_required
def selection():
    return render_template('selection.html')

@app.route('/mode/<m>')
@login_required
def set_mode(m):
    global current_source, violations_log, session_active, peeking_sensitivity, invigilator_threshold

    # Check if returning from processing
    is_processed = request.args.get('processed') == 'true'

    if 'peeking_sensitivity' in session:
        peeking_sensitivity = session['peeking_sensitivity']

    # Only reset if explicitly switching modes (not just reloading)
    # Check if this is a fresh mode switch vs a reload
    if not is_processed and not session_active:
        # Release camera when switching modes or fresh load (but not during active session)
        release_camera()
        # Clear previous violations
        violations_log = []
        # Set source based on mode - BUT don't auto-start camera for live mode
        current_source = None  # Will be set when session starts

    print(f"DEBUG: Rendering dashboard. Mode={m}, InvigConf={invigilator_threshold}")

    return render_template('dashboard.html',
                        mode=m,
                        session_active=session_active,
                        invigilator_threshold=invigilator_threshold,
                        peeking_sensitivity=peeking_sensitivity,
                        confidence_threshold=confidence_threshold,
                        current_session_id=current_session_id)


@app.route('/process_data', methods=['POST'])
@login_required
def process_data():

    # Handle file upload, process it, and save annotated version
    print("🔵 DEBUG: process_data route called!")
    global current_source
    file = request.files.get('file')

    if file:
        fname = secure_filename(file.filename)

        # Save original file
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(original_path)
        print(f"📥 File uploaded: {fname}")

        # Create processed filename
        processed_fname = f"processed_{fname}"
        processed_path = os.path.join(
            app.config['PROCESSED_FOLDER'], processed_fname)

        # Determine file type and process
        ext = fname.lower().split('.')[-1]

        if ext in ['mp4', 'avi', 'mov', 'mkv', 'webm']:
            # Process video
            frame_count = process_video(original_path, processed_path)
            if frame_count > 0:
                # Set current source to processed video for display
                current_source = processed_path
                # Clean up original file
                try:
                    os.remove(original_path)
                    print(f"🗑️ Removed original file: {fname}")
                except Exception as e:
                    print(f"⚠️ Could not remove original file: {e}")
            else:
                # If processing failed, use original
                current_source = original_path

        elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
            # Process image
            success = process_image(original_path, processed_path)
            if success:
                # Set current source to processed image for display
                current_source = processed_path
                # Clean up original file
                try:
                    os.remove(original_path)
                    print(f"🗑️ Removed original file: {fname}")
                except Exception as e:
                    print(f"⚠️ Could not remove original file: {e}")
            else:
                # If processing failed, use original
                current_source = original_path
        else:
            print(f"⚠️ Unsupported file format: {ext}")
            current_source = original_path

    return redirect(url_for('set_mode', m='recorded', processed='true'))

@app.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    global peeking_sensitivity, invigilator_threshold
    try:
        data = request.json

        # Invigilator detection confidence
        if 'invig_conf' in data:
            val = float(data['invig_conf'])
            invigilator_threshold = max(0.1, min(1.0, val))

        # Peeking yaw sensitivity
        if 'peeking_sens' in data:
            val = float(data['peeking_sens'])
            peeking_sensitivity = max(0.01, min(0.5, val))
            session['peeking_sensitivity'] = peeking_sensitivity

        print(f"[Settings] Updated -> Invig: {invigilator_threshold}, Peek: {peeking_sensitivity}")

        return jsonify({
            "status": "success",
            "invig_conf": invigilator_threshold,
            "peeking_sens": peeking_sensitivity
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/set_phone_threshold', methods=['POST'])
@login_required
def set_phone_threshold():
    """Update mobile phone detection confidence threshold from dashboard slider"""
    global confidence_threshold
    data = request.get_json()
    if data and 'threshold' in data:
        val = float(data['threshold'])
        if 0.20 <= val <= 0.95:  # Safety bounds
            confidence_threshold = val
            print(f"[Settings] Phone threshold updated -> {confidence_threshold}")
            return jsonify({'status': 'ok', 'threshold': val})
    return jsonify({'status': 'error'}), 400


@app.route('/video_feed')
@login_required
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_logs')
@login_required
def get_logs():
    """Return recent violations with badge/icon data for dashboard display"""
    with violations_lock:
        log_copy = list(violations_log[-20:])

    formatted = []
    for entry in log_copy:
        v_type = entry.get('type', '')

        # Determine badge color and icon for frontend
        if v_type == 'Mobile Phone':
            badge_class = 'badge-danger'
            icon = '📱'
        elif 'Signaling' in v_type and 'Mutual' not in v_type:
            badge_class = 'badge-danger'
            icon = '👁️'
        elif 'Mutual' in v_type:
            badge_class = 'badge-danger'
            icon = '🔗'
        else:
            badge_class = 'badge-warning'
            icon = '⚠️'

        formatted.append({
            'time': entry.get('time', ''),
            'type': v_type,
            'conf': entry.get('conf', 0),
            'badge_class': badge_class,
            'icon': icon,
            'alert_level': entry.get('alert_level', 'critical')
        })

    return jsonify(formatted)


@app.route('/get_stats')
@login_required
def get_stats():
    """Get real-time session statistics with per-type breakdown"""
    with violations_lock:
        log_copy = list(violations_log)

    total = len(log_copy)
    phone_count = sum(
        1 for v in log_copy
        if v.get('type') == 'Mobile Phone'
    )
    peeking_count = sum(
        1 for v in log_copy
        if 'Signaling' in v.get('type', '')
        and 'Mutual' not in v.get('type', '')
    )
    mutual_count = sum(
        1 for v in log_copy
        if v.get('type') == 'Mutual Signaling'
    )

    return jsonify({
        'total': total,
        'total_violations': total,
        'mobile_phone': phone_count,
        'peeking': peeking_count,
        'mutual_signaling': mutual_count,
        'breakdown': {  # Legacy field for backward compat
            **(({'Mobile Phone': phone_count} if phone_count else {})),
            **(({'Signaling': peeking_count} if peeking_count else {})),
            **(({'Mutual Signaling': mutual_count} if mutual_count else {})),
        },
        'session_id': current_session_id,
        'session_active': session_active
    })


@app.route('/phone_alert_status')
@login_required
def phone_alert_status():
    """
    Lightweight endpoint polled by the frontend every second.
    Returns the current phone state machine snapshot so the browser
    alarm can start and stop based on any active tracked phones.
    """
    with phone_tracker_lock:
        any_active = any(track['incident_active'] for track in phone_tracks.values())
        return jsonify({
            'phone_detected': any_active,
            'incident_active': any_active
        })


@app.route('/start_session', methods=['POST'])
@login_required
def start_session():
    """Start a new monitoring session"""
    global session_active, current_session_id, violations_log, active_violations, current_source

    if not session_active:
        session_active = True
        current_session_id = f"Session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        violations_log = []
        active_violations = {}
        current_source = 0  # Initialize camera
        
        global session_start_time, session_end_time, unique_face_ids_seen
        session_start_time = datetime.now()
        session_end_time = None
        unique_face_ids_seen = set()

        # Reset phone state machine for fresh session
        global phone_id_counter  # Must declare global to modify module-level counter
        with phone_tracker_lock:
            phone_tracks.clear()
            phone_id_counter = 0

        # Reset face tracker + suspicion state machine for fresh session
        global face_id_counter, face_tracks, student_suspicion, mutual_gaze_sessions, _peek_cooldowns
        face_id_counter = 0
        face_tracks.clear()
        student_suspicion.clear()
        mutual_gaze_sessions.clear()
        _peek_cooldowns.clear()

        print(f"✅ Session Started: {current_session_id}")
        return jsonify({"status": "success", "session_id": current_session_id})

    return jsonify({"status": "already_active"}), 400


@app.route('/end_session', methods=['POST'])
@login_required
def end_session():
    """End the current monitoring session"""
    global session_active

    if session_active:
        session_active = False
        global session_end_time
        session_end_time = datetime.now()
        violation_count = len(violations_log)
        print(
            f"🛑 Session Ended: {current_session_id} ({violation_count} violations)")

        # Release camera
        release_camera()

        return jsonify({
            "status": "success",
            "violations": violation_count,
            "session_id": current_session_id
        })

    return jsonify({"status": "not_active"}), 400


@app.route('/test_camera')
@login_required
def test_camera():
    """Test if camera is accessible"""
    cap = initialize_camera()
    if cap:
        cap.release()
        return jsonify({
            "status": "success",
            "message": "Camera is accessible and working properly"
        })
    return jsonify({
        "status": "error",
        "message": camera_error or "Camera not found or in use by another application"
    }), 500


@app.route('/camera_status')
@login_required
def camera_status():
    """Get current camera status"""
    global active_camera
    with camera_lock:
        is_active = active_camera is not None

    return jsonify({
        "active": is_active,
        "source": current_source,
        "error": camera_error
    })


@app.route('/download_processed')
@login_required
def download_processed():
   
    # Download the processed file with all detections
   
    global current_source

    if current_source and os.path.exists(current_source):
        # Check if it's a processed file
        if 'processed_outputs' in current_source or current_source.startswith('processed_'):
            try:
                return send_file(
                    current_source,
                    as_attachment=True,
                    download_name=os.path.basename(current_source)
                )
            except Exception as e:
                print(f"❌ Download error: {str(e)}")
                return f"Error downloading file: {str(e)}", 500
        else:
            return "No processed file available. Please upload and process a file first.", 404

    return "No file available for download.", 404


class ExamReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(15, 23, 42)  # Slate 900
        self.cell(0, 10, 'ExamGuard | Monitoring Report', 0, 1, 'C')
        self.set_font('Arial', '', 9)
        self.set_text_color(100, 116, 139)  # Slate 500
        self.cell(
            0, 5, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        self.ln(10)
        # Line break
        self.line(10, 30, 200, 30)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(
            0, 10, f'Page {self.page_no()}/{{nb}} - Confidential', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(241, 245, 249)  # Slate 100
        self.cell(0, 6, f'  {label}', 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, text)
        self.ln()


@app.route('/generate_report')
@login_required
def generate_report():
    global session_start_time, session_end_time, unique_face_ids_seen

    d = get_report_dir()
    if not os.path.exists(d):
        return "No reports found for this session."

    # Separate critical evidence from behavioral warnings
    all_imgs = [i for i in os.listdir(d) if i.endswith('.jpg')]
    warning_imgs = [i for i in all_imgs if i.startswith('quick_glance')]
    warning_count = len(warning_imgs)

    EXCLUDED_PREFIXES = ('quick_glance',)
    imgs = [
        i for i in all_imgs
        if i.endswith('.jpg') and not i.startswith(EXCLUDED_PREFIXES)
    ]
    imgs.sort()  # Sort by timestamp for chronological order

    if not imgs:
        if warning_count > 0:
            return f"No critical violations recorded. {warning_count} behavioral warning(s) logged - visible in session dashboard only."
        return "No violations recorded in this session."

    # Calculate session duration
    if session_start_time and session_end_time:
        duration = session_end_time - session_start_time
        total_seconds = int(duration.total_seconds())
        duration_str = f"{total_seconds // 60:02d} min {total_seconds % 60:02d} sec"
        start_str = session_start_time.strftime("%H:%M:%S")
        end_str = session_end_time.strftime("%H:%M:%S")
        date_str = session_start_time.strftime("%B %d, %Y")
    else:
        duration_str = "N/A"
        start_str = "N/A"
        end_str = "N/A"
        date_str = datetime.now().strftime("%B %d, %Y")

    # Build violation stats from critical images only
    stats = {}
    for img in imgs:
        try:
            img_name = img.replace('.jpg', '')
            # Explicit filename-to-type mapping for accurate stats
            if img_name.startswith('mobile_phone'):
                violation_type = 'Mobile Phone'
            elif img_name.startswith('signaling_detected'):
                violation_type = 'Signaling Detected'
            elif img_name.startswith('directional_signaling'):
                violation_type = 'Directional Signaling'
            elif img_name.startswith('mutual_signal'):
                violation_type = 'Mutual Signaling'
            else:
                parts = img_name.rsplit('_', 1)
                violation_type = parts[0].replace('_', ' ').title()
            stats[violation_type] = stats.get(violation_type, 0) + 1
        except:
            continue

    critical_count = len(imgs)
    unique_students = len(unique_face_ids_seen)

    # UFM Recommendation logic
    if critical_count == 0:
        recommendation = "NO ACTION REQUIRED - Clean monitoring session."
        rec_color = (0, 150, 0)
    elif critical_count <= 2:
        recommendation = "REVIEW RECOMMENDED - Critical evidence attached for invigilator review."
        rec_color = (200, 100, 0)
    else:
        recommendation = "FORMAL UFM SUBMISSION RECOMMENDED - Multiple critical violations detected."
        rec_color = (180, 0, 0)

    # Get first and last violation times from log
    critical_logs = [
        log for log in violations_log
        if 'critical' in log.get('alert_level', '')
        or log.get('type') in ['Signaling Detected', 'Directional Signaling', 'Mutual Signaling', 'Mobile Phone']
    ]
    first_violation = critical_logs[0]['time'] if critical_logs else "N/A"
    last_violation = critical_logs[-1]['time'] if critical_logs else "N/A"

    pdf = ExamReport()
    pdf.alias_nb_pages()
    pdf.add_page()

    # ── COVER PAGE ──────────────────────────────────────
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 22)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 12, 'ExamGuard', 0, 1, 'C')

    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, 'AI Based Student Behavior Monitoring System', 0, 1, 'C')
    pdf.ln(5)

    # Red separator line
    pdf.set_draw_color(180, 0, 0)
    pdf.set_line_width(0.8)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(8)

    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, 'EXAMINATION MONITORING REPORT', 0, 1, 'C')

    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 7, 'CONFIDENTIAL', 0, 1, 'C')
    pdf.ln(10)

    # Session metadata box
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(200, 200, 200)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(15, 23, 42)

    meta_items = [
        ('Exam Date', date_str),
        ('Session ID', current_session_id or 'N/A'),
        ('Start Time', start_str),
        ('End Time', end_str),
        ('Duration', duration_str),
        ('Invigilator', session.get('user', 'Unknown').title()),
        ('Role', session.get('role', 'Invigilator').title()),
        ('Report Generated', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]

    for label, value in meta_items:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 9, f'  {label}:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 9, value, 0, 1)

    pdf.ln(5)
    pdf.set_draw_color(180, 0, 0)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())

    pdf.add_page()

    # ── VISUAL EVIDENCE LOG ──────────────────────────────
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, 'Visual Evidence Log', 0, 1)
    pdf.set_draw_color(180, 0, 0)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    for i, img in enumerate(imgs):
        try:
            # Parse metadata from filename
            base = img.replace('.jpg', '')
            parts = base.rsplit('_', 1)
            label = parts[0].replace('_', ' ').upper()
            ts = datetime.fromtimestamp(int(parts[1])).strftime('%H:%M:%S')
        except:
            label = "UNKNOWN VIOLATION"
            ts = "N/A"

        img_path = os.path.join(d, img)

        try:
            im_cv = cv2.imread(img_path)
            if im_cv is None:
                continue
            ih, iw, _ = im_cv.shape
            target_w = 150
            aspect = ih / iw
            print_h = target_w * aspect

            # Check page space — need room for card header + image + footer
            if pdf.get_y() + print_h + 45 > 270:
                pdf.add_page()

            # Evidence card header
            pdf.set_fill_color(15, 23, 42)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 8, f'  EVIDENCE #{i+1}   |   {label}   |   Detected at {ts}', 0, 1, 'L', 1)

            # Find matching log entry for this image timestamp
            matched_log = None
            for log in violations_log:
                if log.get('time') == ts:
                    matched_log = log
                    break

            # Metadata row below header
            pdf.set_fill_color(241, 245, 249)
            pdf.set_text_color(15, 23, 42)
            pdf.set_font('Arial', '', 9)

            face_id_display = f"face_id={matched_log.get('face_id', 'N/A')}" if matched_log else ''
            conf_display = f"Detection Score: {int(matched_log.get('conf', 0)*100)}%" if matched_log else ''
            sideways_display = f"Behavioral Evidence: {matched_log.get('total_sideways_time', 'N/A')}s sustained" if matched_log else ''

            metadata_line = '   '.join(filter(None, [face_id_display, conf_display, sideways_display]))
            pdf.cell(0, 7, f'  {metadata_line}', 0, 1, 'L', 1)
            pdf.ln(2)

            # Evidence image centered
            x_pos = (210 - target_w) / 2
            current_y = pdf.get_y()
            pdf.image(img_path, x=x_pos, y=current_y, w=target_w)
            pdf.set_y(current_y + print_h + 3)

            # Caption below image
            pdf.set_font('Arial', 'I', 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(0, 5, f'Figure {i+1}: {label} detected at {ts}', 0, 1, 'C')
            pdf.ln(10)

        except Exception as e:
            print(f"Error adding evidence image {img}: {e}")
            continue

    pdf.add_page()

    # ── EXAMINER SIGN-OFF ────────────────────────────────
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, 'Invigilator Acknowledgement', 0, 1)
    pdf.set_draw_color(180, 0, 0)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(0, 8,
        'I confirm that this report accurately represents the AI monitoring '
        'session conducted under my supervision. The evidence images and '
        'timestamps are system-generated and unmodified.', 0, 'L')
    pdf.ln(10)

    # Sign-off fields
    signoff_fields = [
        ('Invigilator Name', session.get('user', '').title()),
        ('Session ID', current_session_id or 'N/A'),
        ('Report Date', datetime.now().strftime("%Y-%m-%d")),
        ('Signature', ''),
        ('Date Signed', ''),
        ('UFM Committee Reference No.', ''),
    ]

    for label, prefill in signoff_fields:
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(80, 10, f'{label}:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(15, 23, 42)
        # Draw line for signature fields
        if prefill:
            pdf.cell(0, 10, prefill, 0, 1)
        else:
            pdf.cell(0, 10, '_' * 40, 0, 1)

    pdf.ln(15)

    # System integrity statement
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(0, 6,
        'SYSTEM INTEGRITY NOTICE: This report was generated automatically '
        'by ExamGuard AI Behavior Monitoring System. All detection timestamps '
        'are system-generated. All evidence images are unmodified frame captures. '
        f'System Version: ExamGuard v1.0 | Session: {current_session_id}',
        0, 'L', 1)

    # Save and return
    rep_name = f"ExamGuard_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    report_path = os.path.join(d, rep_name)
    pdf.output(report_path)
    return send_file(report_path, as_attachment=True)


# Cleanup on shutdown
@atexit.register
def cleanup():
    """Release camera on application shutdown"""
    print("\n🛑 Shutting down ExamGuard...")
    release_camera()
    print("✅ Cleanup complete")


if __name__ == '__main__':
    print("🚀 Starting ExamGuard - AI Exam Monitoring System")
    print("=" * 50)

    # Threaded=True stream ko smooth banata hai
    try:
        app.run(debug=True, use_reloader=False, port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        cleanup()
