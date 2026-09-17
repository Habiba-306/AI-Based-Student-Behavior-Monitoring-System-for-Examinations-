🛡️ ExamGuard — AI-Based Student Behavior Monitoring System for Examinations
Real-time examination proctoring and cheating detection using YOLOv8, MediaPipe 6-Point PnP Head-Pose Estimation, and Multi-State Tracking Machines.

Python Flask YOLOv8 MediaPipe OpenCV FPDF

🎮 Overview
ExamGuard is an automated, real-time AI-powered examination proctoring system designed to detect and log suspicious student behaviors during exams. It operates via live webcam stream or uploaded video, providing real-time visual tracking, audible alarms, and automated forensic PDF reports.

Key Innovation: Multi-model sensor fusion combining YOLOv8 object detection with an upper-face 6-point Perspective-n-Point (PnP) rigid head geometry solver and persistent tracking state machines (Ghost Box Invigilator Suppression, Cumulative Suspicion Tracking, Spatial Phone Tracking, and Mutual Gaze Detection).

✨ Features
👁️ Peeking & Head Pose Detection: 6-point PnP solver detects sideways head turns (
≥Here is a clean, properly formatted `README.md` file that you can copy and paste directly into your ExamGuard repository. I have fixed the broken unicode characters (≥, ≤, ~) and ensured all markdown formatting (tables, code blocks, headings) renders correctly.

---

```markdown
# 🛡️ ExamGuard — AI-Based Student Behavior Monitoring System for Examinations

Real-time examination proctoring and cheating detection using YOLOv8, MediaPipe 6-Point PnP Head-Pose Estimation, and Multi-State Tracking Machines.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=flat&logo=flask&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-00BFFF?style=flat&logo=ultralytics&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0097A7?style=flat&logo=google&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white)
![FPDF](https://img.shields.io/badge/FPDF-FF6F00?style=flat&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat)

---

## 🎮 Overview

ExamGuard is an automated, real-time AI-powered examination proctoring system designed to detect and log suspicious student behaviors during exams. It operates via live webcam stream or uploaded video, providing real-time visual tracking, audible alarms, and automated forensic PDF reports.

**Key Innovation:** Multi-model sensor fusion combining YOLOv8 object detection with an upper-face 6-point Perspective-n-Point (PnP) rigid head geometry solver and persistent tracking state machines (Ghost Box Invigilator Suppression, Cumulative Suspicion Tracking, Spatial Phone Tracking, and Mutual Gaze Detection).

---

## ✨ Features

- 👁️ **Peeking & Head Pose Detection:** 6-point PnP solver detects sideways head turns (≥22° yaw) with extreme angle fallback.
- 📱 **Mobile Phone Detection & Tracking:** YOLOv8 phone detection with 3-frame spatial debouncing and 15s per-phone cooldown.
- 🔗 **Mutual Gaze Detection:** Flags pairs of students maintaining direct eye contact for ≥3 seconds.
- 👮 **Invigilator Ghost Box Suppression:** Ghost Box system (20-frame TTL) prevents invigilator movement from triggering false alerts.
- 📊 **Automated Forensic PDF Reports:** Auto-generates formal evidence reports with timestamped screenshots, metadata, and invigilator sign-off fields.
- 🎥 **Flexible Input Modes:** Live webcam proctoring, recorded video processing, and single-image analysis.
- 🔐 **Secure Authentication:** Role-based login system with hashed password validation.
- 🔔 **Real-Time Audio Alerts:** Instant audible alerts on critical cheating incidents.

---

## 🚀 Installation

### Prerequisites

- Python 3.9 or higher
- Webcam (for live mode)
- Windows 10/11 (or Linux/macOS)

### Step 1: Clone the Repository

```bash
git clone https://github.com/Habiba-306/AI-Based-Student-Behavior-Monitoring-System-for-Examinations-.git
cd AI-Based-Student-Behavior-Monitoring-System-for-Examinations-
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

**Alternative (Manual Install):**

```bash
pip install flask ultralytics mediapipe opencv-python numpy fpdf werkzeug
```

### Step 3: Prepare Model & Users

- Make sure `best.pt` is in the project root folder.
- Initialize default user credentials:

```bash
python init_users.py
```

### Step 4: Run the Application

```bash
python app.py
```

### Step 5: Start Proctoring!

1. Open browser at `http://127.0.0.1:5000`
2. Log in with credentials (`admin` / `admin123`)
3. Select **Live Proctoring** or **Recorded Video / Image**
4. Click **▶ Start Session** to launch real-time AI monitoring
5. When finished, click **⏹ End Session** and **📄 Generate Report** to download the PDF

---

## 📁 Project Structure

```
ExamGuard_Project/
├── app.py                  # Main Flask app, stream generator & state machines (2500+ lines)
├── models.py               # Singleton initialization for YOLOv8 and MediaPipe
├── utils.py                # Pure spatial math utilities (IoU, IoMin, gaze classification)
├── best.pt                 # Custom-trained YOLOv8 model weights (~38 MB)
├── users.json              # Encrypted user authentication data
├── init_users.py           # Default user creation script
├── add_user.py             # Script to add custom invigilator accounts
├── templates/              # HTML Frontend Templates
│   ├── login.html          # Authentication page
│   ├── selection.html      # Mode selection (Live / Recorded / Image)
│   ├── dashboard.html      # Main monitoring dashboard UI
│   └── select_camera.html  # Multi-camera selection modal
├── static/                 # CSS, JavaScript & branding assets
├── uploads/                # Directory for uploaded input videos/images
├── processed_outputs/      # Directory for annotated video/image outputs
├── Reports/                # Session evidence images and generated PDF reports
└── requirements.txt        # Project dependencies
```

---

## 👁️ How Detection & State Machines Work

| Detection Layer | Algorithm / Model | Trigger Condition | Action Taken |
|----------------|-------------------|-------------------|--------------|
| 👮 Invigilator Filtering | YOLOv8 + IoMin Ghost Box | Face inside invigilator box (IoMin > 0.4) | Suppress false peeking alert |
| 👁️ Peeking Detection | MediaPipe 6-Point PnP | Head Yaw angle ≥ 22° | Flagged as peeking face |
| ⏱️ Suspicion Accumulator | Sliding 5s Window | Sideways time ≥ 3.0s | Escalate to Critical alert + Screenshot |
| 📱 Mobile Phone | YOLOv8 + IoU Spatial Tracker | 3 consecutive frames @ ≥60% conf | Fire 15s alarm & screenshot |
| 🔗 Mutual Gaze | Yaw Direction + Proximity | Pair distance ≤ 600px, duration ≥ 3.0s | Mutual Signaling alert + Evidence |

---

## 🎮 Proctoring Rules & Escalation

| Behavior | Duration / Condition | Alert Level | Action |
|----------|---------------------|-------------|--------|
| Quick Glance | < 0.5s sideways | 🟢 Clean | Logged silently in background |
| Sustained Glance | 0.5s – 3.0s sideways | 🟡 Warning | Dashboard alert displayed |
| Signaling / Peeking | ≥ 3.0s sustained sideways | 🔴 Critical | Audio Beep + Evidence Screenshot |
| Directional Peeking | ≥ 3.0s (Dominant direction 3×) | 🔴 Critical Directional | Audio Beep + Evidence Screenshot |
| Mobile Phone | 3 consecutive frames | 🔴 Critical Phone | Immediate Beep + Evidence Screenshot |
| Mutual Signaling | 2 students gaze ≥ 3.0s | 🔴 Critical Mutual | Connecting Line Screenshot + Beep |

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| PnP Head Pose Solver Speed | < 8 ms per frame |
| YOLOv8 Object Detection Speed | ~15–25 ms (CPU) / ~5 ms (GPU) |
| Async Processing Skip | Every 2nd Frame (smooth 30 FPS stream) |
| Face Tracking Continuity | 45 frames tolerance |
| Ghost Box Persistence TTL | 20 frames (~0.6s) |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Flask (Python 3.9+) |
| Object Detection | YOLOv8 (Ultralytics) |
| Face Mesh & PnP Pose | MediaPipe + OpenCV + NumPy |
| Spatial Math & Utilities | Custom IoU & IoMin algorithms |
| PDF Report Engine | FPDF |
| Frontend | HTML5, CSS3, JavaScript, MJPEG Stream |

---

## 💡 Possible Extensions

- 🏷️ Add Face Recognition to match student faces against institutional seating charts
- 📐 Add pitch tilt detection to catch students looking down at hidden chits under desks
- 🗄️ Persist violation logs to PostgreSQL / SQLite database
- 📧 Email PDF reports automatically to exam administrators on session completion
- 🎥 Add multi-camera synchronization for large examination halls

---

## 📝 License

This project is developed for Final Year Project academic purposes. Feel free to use and modify.

---

⭐ **If you found this project helpful, consider giving it a star!**

---

## 📫 Connect

- **GitHub:** [Habiba-306](https://github.com/Habiba-306)
- **Repository:** [AI-Based-Student-Behavior-Monitoring-System-for-Examinations-](https://github.com/Habiba-306/AI-Based-Student-Behavior-Monitoring-System-for-Examinations-)
```

---

**Copy everything above (from the first `#` to the last line) and paste it into your `README.md` file.** It will render correctly on GitHub. Let me know if you need any adjustments! 🚀
22
∘
≥22 
∘
  yaw) with extreme angle fallback.
📱 Mobile Phone Detection & Tracking: YOLOv8 phone detection with 3-frame spatial debouncing and 15s per-phone cooldown.
🔗 Mutual Gaze Detection: Flags pairs of students maintaining direct eye contact for 
≥
3
≥3 seconds.
👮 Invigilator Ghost Box Suppression: Ghost Box system (20-frame TTL) prevents invigilator movement from triggering false alerts.
📊 Automated Forensic PDF Reports: Auto-generates formal evidence reports with timestamped screenshots, metadata, and invigilator sign-off fields.
🎥 Flexible Input Modes: Live webcam proctoring, recorded video processing, and single-image analysis.
🔐 Secure Authentication: Role-based login system with hashed password validation.
🔔 Real-Time Audio Alerts: Instant audible alerts on critical cheating incidents.
🚀 Installation
Prerequisites
Python 3.9 or higher
Webcam (for live mode)
Windows 10/11 (or Linux/macOS)
Step 1: Clone the Repository
bash

git clone https://github.com/Habiba-306/AI-Based-Student-Behavior-Monitoring-System-for-Examinations-.git
cd AI-Based-Student-Behavior-Monitoring-System-for-Examinations-
Step 2: Install Dependencies
bash

pip install -r requirements.txt
Alternative (Manual Install):

bash

pip install flask ultralytics mediapipe opencv-python numpy fpdf werkzeug
Step 3: Prepare Model & Users
Make sure best.pt is in the project root folder.
Initialize default user credentials:

bash

python init_users.py
Step 4: Run the Application
bash

python app.py
Step 5: Start Proctoring!
Open browser at http://127.0.0.1:5000
Log in with credentials (admin / admin123)
Select Live Proctoring or Recorded Video / Image
Click ▶ Start Session to launch real-time AI monitoring
When finished, click ⏹ End Session and 📄 Generate Report to download the PDF
📁 Project Structure

ExamGuard_Project/
├── app.py                  # Main Flask app, stream generator & state machines (2500+ lines)
├── models.py               # Singleton initialization for YOLOv8 and MediaPipe
├── utils.py                # Pure spatial math utilities (IoU, IoMin, gaze classification)
├── best.pt                 # Custom-trained YOLOv8 model weights (~38 MB)
├── users.json              # Encrypted user authentication data
├── init_users.py           # Default user creation script
├── add_user.py             # Script to add custom invigilator accounts
├── templates/              # HTML Frontend Templates
│   ├── login.html          # Authentication page
│   ├── selection.html      # Mode selection (Live / Recorded / Image)
│   ├── dashboard.html      # Main monitoring dashboard UI
│   └── select_camera.html  # Multi-camera selection modal
├── static/                 # CSS, JavaScript & branding assets
├── uploads/                # Directory for uploaded input videos/images
├── processed_outputs/      # Directory for annotated video/image outputs
├── Reports/                # Session evidence images and generated PDF reports
└── requirements.txt        # Project dependencies
👁️ How Detection & State Machines Work
Detection Layer	Algorithm / Model	Trigger Condition	Action Taken
👮 Invigilator Filtering	YOLOv8 + IoMin Ghost Box	Face inside invigilator box (
IoMin
>
0.4
IoMin>0.4)	Suppress false peeking alert
👁️ Peeking Detection	MediaPipe 6-Point PnP	Head Yaw angle 
≥
22
∘
≥22 
∘
 	Flagged as peeking face
⏱️ Suspicion Accumulator	Sliding 5s Window	Sideways time 
≥
3.0
s
≥3.0s	Escalate to Critical alert + Screenshot
📱 Mobile Phone	YOLOv8 + IoU Spatial Tracker	3 consecutive frames @ 
≥
60
%
≥60% conf	Fire 15s alarm & screenshot
🔗 Mutual Gaze	Yaw Direction + Proximity	Pair distance 
≤
600
px
≤600px, duration 
≥
3.0
s
≥3.0s	Mutual Signaling alert + Evidence
🎮 Proctoring Rules & Escalation
Behavior	Duration / Condition	Alert Level	Action
Quick Glance	
<
0.5
s
<0.5s sideways	🟢 Clean	Logged silently in background
Sustained Glance	
0.5
s
−
3.0
s
0.5s−3.0s sideways	🟡 Warning	Dashboard alert displayed
Signaling / Peeking	
≥
3.0
s
≥3.0s sustained sideways	🔴 Critical	Audio Beep + Evidence Screenshot
Directional Peeking	
≥
3.0
s
≥3.0s (Dominant direction 
3
×
3×)	🔴 Critical Directional	Audio Beep + Evidence Screenshot
Mobile Phone	3 consecutive frames	🔴 Critical Phone	Immediate Beep + Evidence Screenshot
Mutual Signaling	2 students gaze 
≥
3.0
s
≥3.0s	🔴 Critical Mutual	Connecting Line Screenshot + Beep
📊 Performance
Metric	Value
PnP Head Pose Solver Speed	
<
8
ms
<8ms per frame
YOLOv8 Object Detection Speed	
∼
15
-
25
ms
∼15-25ms (CPU) / 
∼
5
ms
∼5ms (GPU)
Async Processing Skip	Every 2nd Frame (smooth 30 FPS stream)
Face Tracking Continuity	45 frames tolerance
Ghost Box Persistence TTL	20 frames (
∼
0.6
s
∼0.6s)
🛠️ Tech Stack
Component	Technology
Backend Framework	Flask (Python 3.9+)
Object Detection	YOLOv8 (Ultralytics)
Face Mesh & PnP Pose	MediaPipe + OpenCV + NumPy
Spatial Math & Utilities	Custom IoU & IoMin algorithms
PDF Report Engine	FPDF
Frontend	HTML5, CSS3, JavaScript, MJPEG Stream
💡 Possible Extensions
🏷️ Add Face Recognition to match student faces against institutional seating charts
📐 Add pitch tilt detection to catch students looking down at hidden chits under desks
🗄️ Persist violation logs to PostgreSQL / SQLite database
📧 Email PDF reports automatically to exam administrators on session completion
🎥 Add multi-camera synchronization for large examination halls
📝 License
This project is developed for Final Year Project academic purposes. Feel free to use and modify.

⭐ If you found this project helpful, consider giving it a star!

📫 Connect
GitHub: Habiba-306
Repository: AI-Based-Student-Behavior-Monitoring-System-for-Examinations-
