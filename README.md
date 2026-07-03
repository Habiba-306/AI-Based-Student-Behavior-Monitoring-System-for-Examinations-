<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ExamGuard — README</title>
<style>
  :root {
    --primary: #1e40af;
    --primary-light: #3b82f6;
    --accent: #0ea5e9;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --dark: #0f172a;
    --card: #1e293b;
    --border: #334155;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --phase1: #8b5cf6;
    --phase2: #06b6d4;
    --phase3: #f59e0b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--dark);
    color: var(--text);
    line-height: 1.6;
  }

  /* ── HERO ── */
  .hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    padding: 80px 40px 60px;
    text-align: center;
    position: relative;
    overflow: hidden;
    border-bottom: 1px solid var(--border);
  }
  .hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(59,130,246,0.15) 0%, transparent 70%);
  }
  .hero-icon { font-size: 72px; margin-bottom: 20px; display: block; }
  .hero h1 {
    font-size: clamp(28px, 5vw, 52px);
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 16px;
    position: relative;
  }
  .hero p {
    font-size: 18px;
    color: var(--muted);
    max-width: 700px;
    margin: 0 auto 32px;
    position: relative;
  }
  .badge-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px;
    position: relative;
  }
  .badge {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  .badge-blue { background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
  .badge-purple { background: rgba(139,92,246,0.2); color: #a78bfa; border: 1px solid rgba(139,92,246,0.3); }
  .badge-green { background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
  .badge-orange { background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
  .badge-cyan { background: rgba(6,182,212,0.2); color: #22d3ee; border: 1px solid rgba(6,182,212,0.3); }

  /* ── NAV ── */
  .nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(15,23,42,0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 0 40px;
    display: flex;
    gap: 0;
    overflow-x: auto;
  }
  .nav a {
    color: var(--muted);
    text-decoration: none;
    padding: 16px 18px;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
  }
  .nav a:hover { color: var(--text); border-bottom-color: var(--primary-light); }

  /* ── LAYOUT ── */
  .container { max-width: 1100px; margin: 0 auto; padding: 60px 32px; }
  .section { margin-bottom: 80px; }
  .section-title {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 32px;
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .section-title .icon {
    width: 44px; height: 44px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
  }

  /* ── STATS ROW ── */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 40px;
  }
  .stat-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px 20px;
    text-align: center;
    transition: transform 0.2s;
  }
  .stat-card:hover { transform: translateY(-3px); }
  .stat-number { font-size: 32px; font-weight: 800; margin-bottom: 4px; }
  .stat-label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }

  /* ── PHASE CARDS ── */
  .phase-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
  .phase-card {
    background: var(--card);
    border-radius: 16px;
    padding: 28px;
    border: 1px solid var(--border);
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    cursor: pointer;
  }
  .phase-card:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(0,0,0,0.4); }
  .phase-card .phase-glow {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
  }
  .phase1 .phase-glow { background: linear-gradient(90deg, var(--phase1), #c4b5fd); }
  .phase2 .phase-glow { background: linear-gradient(90deg, var(--phase2), #7dd3fc); }
  .phase3 .phase-glow { background: linear-gradient(90deg, var(--phase3), #fde68a); }
  .phone-phase .phase-glow { background: linear-gradient(90deg, var(--danger), #fca5a5); }
  .phase-icon { font-size: 36px; margin-bottom: 16px; display: block; }
  .phase-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
  .phase-desc { color: var(--muted); font-size: 14px; line-height: 1.7; margin-bottom: 16px; }
  .phase-tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .tag {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 20px;
    font-weight: 500;
  }
  .tag-purple { background: rgba(139,92,246,0.15); color: #a78bfa; }
  .tag-cyan { background: rgba(6,182,212,0.15); color: #22d3ee; }
  .tag-orange { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .tag-red { background: rgba(239,68,68,0.15); color: #f87171; }
  .tag-green { background: rgba(16,185,129,0.15); color: #34d399; }

  /* ── ARCHITECTURE ── */
  .arch-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.8;
    color: #94a3b8;
    overflow-x: auto;
    position: relative;
  }
  .arch-box .hl-blue { color: #60a5fa; }
  .arch-box .hl-purple { color: #a78bfa; }
  .arch-box .hl-cyan { color: #22d3ee; }
  .arch-box .hl-orange { color: #fbbf24; }
  .arch-box .hl-green { color: #34d399; }
  .arch-box .hl-red { color: #f87171; }

  /* ── TABLES ── */
  .table-wrap { overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
  table { width: 100%; border-collapse: collapse; }
  thead { background: rgba(30,64,175,0.3); }
  th { padding: 14px 16px; text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); font-weight: 600; }
  td { padding: 14px 16px; border-top: 1px solid var(--border); font-size: 14px; }
  tr:hover td { background: rgba(255,255,255,0.03); }
  .good { color: var(--success); font-weight: 600; }
  .great { color: #60a5fa; font-weight: 700; }
  .up { color: var(--success); }

  /* ── CODE BLOCK ── */
  .code-block {
    background: #0d1117;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.8;
    overflow-x: auto;
    position: relative;
  }
  .code-block .comment { color: #6e7681; }
  .code-block .keyword { color: #ff7b72; }
  .code-block .string { color: #a5d6ff; }
  .code-block .number { color: #79c0ff; }
  .code-block .func { color: #d2a8ff; }

  /* ── ALGO GRID ── */
  .algo-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
  .algo-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    transition: border-color 0.2s;
  }
  .algo-card:hover { border-color: var(--primary-light); }
  .algo-num { font-size: 24px; font-weight: 800; color: var(--border); margin-bottom: 8px; }
  .algo-name { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
  .algo-type { font-size: 11px; color: var(--accent); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
  .algo-desc { font-size: 13px; color: var(--muted); }

  /* ── STEPS ── */
  .steps { display: flex; flex-direction: column; gap: 0; }
  .step {
    display: flex;
    gap: 20px;
    padding: 24px 0;
    border-bottom: 1px solid var(--border);
    position: relative;
  }
  .step:last-child { border-bottom: none; }
  .step-num {
    width: 40px; height: 40px;
    border-radius: 50%;
    background: var(--primary);
    color: white;
    font-weight: 700;
    font-size: 16px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
  }
  .step-content h4 { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
  .step-content p { font-size: 14px; color: var(--muted); }

  /* ── ENDPOINTS ── */
  .method {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    font-family: monospace;
    margin-right: 8px;
  }
  .method-get { background: rgba(16,185,129,0.2); color: #34d399; }
  .method-post { background: rgba(245,158,11,0.2); color: #fbbf24; }
  .endpoint-path { font-family: monospace; color: #60a5fa; }

  /* ── FOOTER ── */
  .footer {
    background: var(--card);
    border-top: 1px solid var(--border);
    padding: 60px 40px;
    text-align: center;
  }
  .footer h3 { font-size: 24px; margin-bottom: 12px; }
  .footer p { color: var(--muted); margin-bottom: 24px; }
  .info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    max-width: 800px;
    margin: 0 auto 40px;
    text-align: left;
  }
  .info-item { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  .info-label { font-size: 11px; color: var(--muted); text-transform: uppercase; margin-bottom: 4px; }
  .info-value { font-size: 14px; font-weight: 500; }

  /* ── COPY BTN ── */
  .copy-btn {
    position: absolute; top: 12px; right: 12px;
    background: var(--border);
    color: var(--muted);
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .copy-btn:hover { background: var(--primary); color: white; }

  /* ── COLLAPSIBLE ── */
  .collapsible { background: none; border: 1px solid var(--border); color: var(--text); width: 100%; text-align: left; padding: 16px 20px; border-radius: 10px; cursor: pointer; font-size: 15px; font-weight: 500; display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; transition: all 0.2s; }
  .collapsible:hover { border-color: var(--primary-light); background: rgba(59,130,246,0.05); }
  .collapsible-content { display: none; padding: 20px; background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-top: none; border-radius: 0 0 10px 10px; margin-top: -8px; margin-bottom: 8px; font-size: 14px; color: var(--muted); line-height: 1.8; }
  .collapsible-content ul { padding-left: 20px; }
  .collapsible-content li { margin-bottom: 6px; }
  .chevron { transition: transform 0.2s; }
  .open .chevron { transform: rotate(180deg); }

  /* ── PROGRESS BARS ── */
  .metric-row { margin-bottom: 16px; }
  .metric-label { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 14px; }
  .metric-name { color: var(--text); }
  .metric-val { font-weight: 600; }
  .bar-bg { background: rgba(255,255,255,0.06); border-radius: 20px; height: 8px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 20px; transition: width 1.5s ease; }

  @media (max-width: 600px) {
    .nav { padding: 0 16px; }
    .container { padding: 40px 16px; }
    .hero { padding: 60px 20px 40px; }
  }
</style>
</head>
<body>

<!-- HERO -->
<section class="hero">
  <span class="hero-icon">🛡️</span>
  <h1>ExamGuard</h1>
  <p>AI-Based Student Behavior Monitoring System for Examinations — Real-time proctoring using Sensor Fusion, Behavioural State Machines & Mutual Gaze Detection</p>
  <div class="badge-row">
    <span class="badge badge-blue">🐍 Python 3.12</span>
    <span class="badge badge-cyan">⚗️ Flask 3.x</span>
    <span class="badge badge-orange">🎯 YOLO11m</span>
    <span class="badge badge-purple">👁️ MediaPipe</span>
    <span class="badge badge-green">📊 mAP50: 91.9%</span>
    <span class="badge badge-blue">⚡ 11.3ms Inference</span>
    <span class="badge badge-purple">🎓 FYP 2026</span>
  </div>
</section>

<!-- NAV -->
<nav class="nav">
  <a href="#overview">Overview</a>
  <a href="#features">Features</a>
  <a href="#architecture">Architecture</a>
  <a href="#results">Results</a>
  <a href="#algorithms">Algorithms</a>
  <a href="#installation">Installation</a>
  <a href="#usage">Usage</a>
  <a href="#api">API</a>
  <a href="#config">Config</a>
  <a href="#structure">Structure</a>
</nav>

<div class="container">

  <!-- OVERVIEW -->
  <section class="section" id="overview">
    <div class="section-title">
      <div class="icon" style="background:rgba(59,130,246,0.15)">📌</div>
      Overview
    </div>

    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-number" style="color:#60a5fa">91.9%</div>
        <div class="stat-label">Overall mAP50</div>
      </div>
      <div class="stat-card">
        <div class="stat-number" style="color:#34d399">95.8%</div>
        <div class="stat-label">Invigilator mAP50</div>
      </div>
      <div class="stat-card">
        <div class="stat-number" style="color:#f59e0b">87.9%</div>
        <div class="stat-label">Phone mAP50</div>
      </div>
      <div class="stat-card">
        <div class="stat-number" style="color:#a78bfa">11.3ms</div>
        <div class="stat-label">Inference Speed</div>
      </div>
      <div class="stat-card">
        <div class="stat-number" style="color:#22d3ee">6,556</div>
        <div class="stat-label">Training Images</div>
      </div>
      <div class="stat-card">
        <div class="stat-number" style="color:#f87171">2,726</div>
        <div class="stat-label">Lines of Code</div>
      </div>
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr><th>Problem</th><th>ExamGuard Solution</th></tr></thead>
        <tbody>
          <tr><td>Invigilator cannot monitor 30+ students at once</td><td class="good">Real-time AI detection with instant beep alerts</td></tr>
          <tr><td>Invigilator head turns trigger false alarms</td><td class="good">Phase 1 Sensor Fusion — Ghost Box IoMin Suppression</td></tr>
          <tr><td>Brief glances escape detection</td><td class="good">Phase 2 Sliding Window Cumulative State Machine</td></tr>
          <tr><td>Coordinated cheating between pairs invisible</td><td class="good">Phase 3 Mutual Gaze Pair Detection</td></tr>
          <tr><td>Manual evidence collection unreliable</td><td class="good">Automated timestamped PDF evidence reports</td></tr>
          <tr><td>No formal UFM committee documentation</td><td class="good">9-page professional PDF with signature fields</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- FEATURES -->
  <section class="section" id="features">
    <div class="section-title">
      <div class="icon" style="background:rgba(139,92,246,0.15)">✨</div>
      Core Features
    </div>

    <div class="phase-grid">
      <div class="phase-card phase1">
        <div class="phase-glow"></div>
        <span class="phase-icon">🔮</span>
        <div class="phase-title">Phase 1 — Sensor Fusion</div>
        <div class="phase-desc">YOLO11m detects the invigilator and creates a Ghost Box with 20-frame TTL. IoMin (not IoU) checks if any peeking face is inside the invigilator body box — suppressing all false alerts.</div>
        <div class="phase-tags">
          <span class="tag tag-purple">Ghost Box TTL</span>
          <span class="tag tag-purple">IoMin</span>
          <span class="tag tag-purple">YOLO11m</span>
        </div>
      </div>

      <div class="phase-card phase2">
        <div class="phase-glow"></div>
        <span class="phase-icon">🧠</span>
        <div class="phase-title">Phase 2 — State Machine</div>
        <div class="phase-desc">MediaPipe FaceMesh + PnP Solver extracts yaw and pitch angles. 5-second sliding window accumulates sideways time. face_id tracker maintains identity across frames. 3.0s threshold triggers CRITICAL alert.</div>
        <div class="phase-tags">
          <span class="tag tag-cyan">PnP Solver</span>
          <span class="tag tag-cyan">Sliding Window</span>
          <span class="tag tag-cyan">IoU Tracker</span>
        </div>
      </div>

      <div class="phase-card phase3">
        <div class="phase-glow"></div>
        <span class="phase-icon">🔗</span>
        <div class="phase-title">Phase 3 — Mutual Gaze</div>
        <div class="phase-desc">Identifies student pairs simultaneously looking at each other. Spatial constraints: ≤600px horizontal, ≤150px vertical. 3-second sustained mutual gaze triggers CRITICAL alert with connecting-line evidence image.</div>
        <div class="phase-tags">
          <span class="tag tag-orange">Pair Matching</span>
          <span class="tag tag-orange">Gaze Direction</span>
          <span class="tag tag-orange">Novel Feature</span>
        </div>
      </div>

      <div class="phase-card phone-phase">
        <div class="phase-glow"></div>
        <span class="phase-icon">📱</span>
        <div class="phase-title">Mobile Phone Detection</div>
        <div class="phase-desc">YOLO11m trained on 6,556 images achieves 93.3% precision and 83.0% recall on mobile phone detection. Immediate CRITICAL alert with red bounding box evidence screenshot.</div>
        <div class="phase-tags">
          <span class="tag tag-red">93.3% Precision</span>
          <span class="tag tag-red">83.0% Recall</span>
          <span class="tag tag-red">Instant Alert</span>
        </div>
      </div>
    </div>
  </section>

  <!-- ARCHITECTURE -->
  <section class="section" id="architecture">
    <div class="section-title">
      <div class="icon" style="background:rgba(6,182,212,0.15)">🏗️</div>
      System Architecture
    </div>
    <div class="arch-box">
<pre>
<span class="hl-blue">┌─────────────────────────────────────────────────────────────────┐</span>
<span class="hl-blue">│                    ExamGuard Detection Pipeline                 │</span>
<span class="hl-blue">├─────────────────────────────────────────────────────────────────┤</span>
<span class="hl-blue">│                                                                 │</span>
<span class="hl-blue">│  Camera Input (Webcam / USB)                                    │</span>
<span class="hl-blue">│       │                                                         │</span>
<span class="hl-blue">│       ├── Frame A (640px) ──────►</span> <span class="hl-orange">YOLO11m</span>                       │
<span class="hl-blue">│       │                          ├──</span> <span class="hl-green">invigilator</span> <span class="hl-blue">→</span> <span class="hl-purple">Ghost Box TTL │</span>
<span class="hl-blue">│       │                          └──</span> <span class="hl-red">mobile_phone</span> <span class="hl-blue">→</span> <span class="hl-red">Instant Alert │</span>
<span class="hl-blue">│       │                                                         │</span>
<span class="hl-blue">│       └── Frame B (1280px) ────►</span> <span class="hl-cyan">MediaPipe FaceMesh</span>            │
<span class="hl-blue">│                                  └── PnP Head Pose Solver       │</span>
<span class="hl-blue">│                                       ├── Pitch (up/down)       │</span>
<span class="hl-blue">│                                       └── Yaw (left/right)      │</span>
<span class="hl-blue">│                                                │                │</span>
<span class="hl-blue">│                             ┌──────────────────▼─────────────┐ │</span>
<span class="hl-purple">│                             │     PHASE 1 — Sensor Fusion    │ │</span>
<span class="hl-purple">│                             │  IoMin check vs Ghost Boxes    │ │</span>
<span class="hl-purple">│                             │  Invigilator faces → SUPPRESS  │ │</span>
<span class="hl-purple">│                             └──────────────────┬─────────────┘ │</span>
<span class="hl-blue">│                                                │                │</span>
<span class="hl-blue">│                             ┌──────────────────▼─────────────┐ │</span>
<span class="hl-cyan">│                             │     PHASE 2 — State Machine    │ │</span>
<span class="hl-cyan">│                             │  IoU Face Tracker → face_id    │ │</span>
<span class="hl-cyan">│                             │  5s Sliding Window → 3s → CRIT│ │</span>
<span class="hl-cyan">│                             └──────────────────┬─────────────┘ │</span>
<span class="hl-blue">│                                                │                │</span>
<span class="hl-blue">│                             ┌──────────────────▼─────────────┐ │</span>
<span class="hl-orange">│                             │     PHASE 3 — Mutual Gaze      │ │</span>
<span class="hl-orange">│                             │  Pair Matching → 3s Duration   │ │</span>
<span class="hl-orange">│                             │  Connecting Line Evidence       │ │</span>
<span class="hl-orange">│                             └──────────────────┬─────────────┘ │</span>
<span class="hl-blue">│                                                │                │</span>
<span class="hl-blue">│                  ┌─────────────────────────────▼─────────────┐ │</span>
<span class="hl-green">│                  │  Flask Dashboard + PDF Report Generator   │ │</span>
<span class="hl-green">│                  │  Live Log │ Stats │ Evidence Archive       │ │</span>
<span class="hl-green">│                  └───────────────────────────────────────────┘ │</span>
<span class="hl-blue">└─────────────────────────────────────────────────────────────────┘</span>
</pre>
    </div>
  </section>

  <!-- RESULTS -->
  <section class="section" id="results">
    <div class="section-title">
      <div class="icon" style="background:rgba(16,185,129,0.15)">📊</div>
      Model Performance Results
    </div>

    <div style="margin-bottom:40px">
      <div class="metric-row">
        <div class="metric-label"><span class="metric-name">Overall mAP50</span><span class="metric-val" style="color:#60a5fa">91.9%</span></div>
        <div class="bar-bg"><div class="bar-fill" style="width:91.9%;background:linear-gradient(90deg,#1e40af,#3b82f6)"></div></div>
      </div>
      <div class="metric-row">
        <div class="metric-label"><span class="metric-name">Invigilator mAP50</span><span class="metric-val" style="color:#34d399">95.8%</span></div>
        <div class="bar-bg"><div class="bar-fill" style="width:95.8%;background:linear-gradient(90deg,#065f46,#10b981)"></div></div>
      </div>
      <div class="metric-row">
        <div class="metric-label"><span class="metric-name">Mobile Phone mAP50</span><span class="metric-val" style="color:#f59e0b">87.9%</span></div>
        <div class="bar-bg"><div class="bar-fill" style="width:87.9%;background:linear-gradient(90deg,#92400e,#f59e0b)"></div></div>
      </div>
      <div class="metric-row">
        <div class="metric-label"><span class="metric-name">Mobile Phone Recall (Previous: 56.6%)</span><span class="metric-val" style="color:#a78bfa">83.0%</span></div>
        <div class="bar-bg"><div class="bar-fill" style="width:83%;background:linear-gradient(90deg,#4c1d95,#8b5cf6)"></div></div>
      </div>
      <div class="metric-row">
        <div class="metric-label"><span class="metric-name">Invigilator Precision</span><span class="metric-val" style="color:#22d3ee">95.9%</span></div>
        <div class="bar-bg"><div class="bar-fill" style="width:95.9%;background:linear-gradient(90deg,#0e7490,#06b6d4)"></div></div>
      </div>
    </div>

    <div class="table-wrap" style="margin-bottom:24px">
      <table>
        <thead><tr><th>Metric</th><th>Old Model</th><th>New Model</th><th>Change</th></tr></thead>
        <tbody>
          <tr><td>Overall mAP50</td><td>0.815</td><td class="great">0.919</td><td class="up">↑ +10.4%</td></tr>
          <tr><td>Phone mAP50</td><td>0.673</td><td class="great">0.879</td><td class="up">↑ +30.6% 🚀</td></tr>
          <tr><td>Phone Recall</td><td style="color:var(--danger)">0.566</td><td class="great">0.830</td><td class="up">↑ +26.4% 🚀</td></tr>
          <tr><td>Phone Precision</td><td>0.876</td><td class="great">0.933</td><td class="up">↑ +5.7%</td></tr>
          <tr><td>Invigilator mAP50</td><td>0.958</td><td class="great">0.958</td><td style="color:var(--muted)">Maintained ✅</td></tr>
          <tr><td>Inference Speed</td><td>27.5ms</td><td class="great">11.3ms</td><td class="up">↑ 2.4× faster ⚡</td></tr>
        </tbody>
      </table>
    </div>

    <div class="table-wrap">
      <table>
        <thead><tr><th>Hyperparameter</th><th>Value</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Model</td><td class="good">YOLO11m</td><td>20M params, 68.2 GFLOPs, 126 layers</td></tr>
          <tr><td>Epochs</td><td class="good">100</td><td>Full training, no early stopping</td></tr>
          <tr><td>Batch Size</td><td class="good">16</td><td>Optimized for T4 GPU (15GB VRAM)</td></tr>
          <tr><td>Optimizer</td><td class="good">AdamW</td><td>Stable adaptive weight updates</td></tr>
          <tr><td>Learning Rate (lr0)</td><td class="good">0.01</td><td>Correctly scaled for batch=16</td></tr>
          <tr><td>Image Size</td><td class="good">640×640</td><td>Standard YOLO input resolution</td></tr>
          <tr><td>Dataset</td><td class="good">6,556 images</td><td>78% train / 12% valid / 10% test</td></tr>
          <tr><td>Training Duration</td><td class="good">4h 23m</td><td>Tesla T4 GPU, Google Colab</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- ALGORITHMS -->
  <section class="section" id="algorithms">
    <div class="section-title">
      <div class="icon" style="background:rgba(245,158,11,0.15)">🔬</div>
      Algorithms Used
    </div>
    <div class="algo-grid">
      <div class="algo-card"><div class="algo-num">01</div><div class="algo-name">YOLO11m</div><div class="algo-type">Deep Learning</div><div class="algo-desc">Single-shot object detector. Detects mobile_phone and invigilator classes. 10.8ms inference = real-time.</div></div>
      <div class="algo-card"><div class="algo-num">02</div><div class="algo-name">PnP Solver</div><div class="algo-type">Geometric Algorithm</div><div class="algo-desc">6-point Perspective-n-Point via cv2.solvePnP(). Extracts pitch, yaw, roll Euler angles from facial landmarks.</div></div>
      <div class="algo-card"><div class="algo-num">03</div><div class="algo-name">MediaPipe FaceMesh</div><div class="algo-type">Deep Learning</div><div class="algo-desc">478 landmark detection. static_image_mode=True for async compatibility. 1280px input for multi-face detection.</div></div>
      <div class="algo-card"><div class="algo-num">04</div><div class="algo-name">IoU Matching</div><div class="algo-type">Computational Geometry</div><div class="algo-desc">Intersection over Union for face tracker identity matching across frames. Threshold: 0.2.</div></div>
      <div class="algo-card"><div class="algo-num">05</div><div class="algo-name">IoMin (Custom)</div><div class="algo-type">Custom Geometry</div><div class="algo-desc">Intersection over Minimum area. Correctly detects small face inside large invigilator body box where IoU fails.</div></div>
      <div class="algo-card"><div class="algo-num">06</div><div class="algo-name">Sliding Window</div><div class="algo-type">Temporal Algorithm</div><div class="algo-desc">5-second rolling timestamp window. Accumulates sideways detection frames. Immune to detection gaps/flicker.</div></div>
      <div class="algo-card"><div class="algo-num">07</div><div class="algo-name">Ghost Box TTL</div><div class="algo-type">Reference Counting</div><div class="algo-desc">20-frame Time-To-Live for invigilator positions. refreshed_ghost_indices set prevents premature expiry.</div></div>
      <div class="algo-card"><div class="algo-num">08</div><div class="algo-name">Finite State Machine</div><div class="algo-type">State Machine</div><div class="algo-desc">Per face_id behavioral state: clean → critical. 30-second session window. Direction consistency tracking.</div></div>
      <div class="algo-card"><div class="algo-num">09</div><div class="algo-name">Mutual Gaze Pairs</div><div class="algo-type">Graph Algorithm</div><div class="algo-desc">O(n²) pair matching. Left-looking face right-of right-looking face. Spatial + temporal constraints.</div></div>
      <div class="algo-card"><div class="algo-num">10</div><div class="algo-name">PnP Failure Heuristic</div><div class="algo-type">Classification</div><div class="algo-desc">Face aspect ratio discriminates extreme sideways (portrait → CRITICAL) from writing (landscape → suppress).</div></div>
      <div class="algo-card"><div class="algo-num">11</div><div class="algo-name">Ring Buffer Filter</div><div class="algo-type">Buffer Algorithm</div><div class="algo-desc">5-frame ring buffer. frame.mean() > 20.0 rejects black/blurry warmup frames. Newest-first search.</div></div>
      <div class="algo-card"><div class="algo-num">12</div><div class="algo-name">Non-Max Suppression</div><div class="algo-type">Greedy Selection</div><div class="algo-desc">YOLO internal. Removes duplicate bounding boxes. IoU threshold: 0.45. Confidence threshold: 0.25.</div></div>
    </div>
  </section>

  <!-- INSTALLATION -->
  <section class="section" id="installation">
    <div class="section-title">
      <div class="icon" style="background:rgba(16,185,129,0.15)">⚙️</div>
      Installation
    </div>
    <div class="steps">
      <div class="step">
        <div class="step-num">1</div>
        <div class="step-content">
          <h4>Clone Repository</h4>
          <div class="code-block" style="margin-top:10px"><pre><span class="keyword">git</span> clone https://github.com/yourusername/examguard.git
<span class="keyword">cd</span> examguard</pre></div>
        </div>
      </div>
      <div class="step">
        <div class="step-num">2</div>
        <div class="step-content">
          <h4>Install Dependencies</h4>
          <div class="code-block" style="margin-top:10px"><pre><span class="comment"># Python 3.12 required</span>
<span class="keyword">pip</span> install -r requirements.txt

<span class="comment"># For GPU support (CUDA 12.x)</span>
<span class="keyword">pip</span> install torch torchvision --index-url https://download.pytorch.org/whl/cu128</pre></div>
        </div>
      </div>
      <div class="step">
        <div class="step-num">3</div>
        <div class="step-content">
          <h4>Initialize Users</h4>
          <div class="code-block" style="margin-top:10px"><pre><span class="keyword">python</span> init_users.py
<span class="comment"># Default: admin / admin123</span></pre></div>
        </div>
      </div>
      <div class="step">
        <div class="step-num">4</div>
        <div class="step-content">
          <h4>Place Model Weights</h4>
          <p>Copy your trained <code>best.pt</code> to the project root directory. Update the model path in <code>app.py</code> if needed.</p>
        </div>
      </div>
      <div class="step">
        <div class="step-num">5</div>
        <div class="step-content">
          <h4>Run ExamGuard</h4>
          <div class="code-block" style="margin-top:10px"><pre><span class="keyword">python</span> app.py
<span class="comment"># Open: http://127.0.0.1:5000</span></pre></div>
        </div>
      </div>
    </div>
  </section>

  <!-- USAGE -->
  <section class="section" id="usage">
    <div class="section-title">
      <div class="icon" style="background:rgba(59,130,246,0.15)">▶️</div>
      Usage Guide
    </div>
    <button class="collapsible" onclick="toggleCollapsible(this)">
      🔐 Step 1 — Login <span class="chevron">▼</span>
    </button>
    <div class="collapsible-content">
      Login with invigilator credentials. Default: <strong>admin / admin123</strong>. Additional users can be added via <code>add_user.py</code> or by editing <code>users.json</code>.
    </div>

    <button class="collapsible" onclick="toggleCollapsible(this)">
      🎥 Step 2 — Select Mode <span class="chevron">▼</span>
    </button>
    <div class="collapsible-content">
      <ul>
        <li><strong>Live Proctoring</strong> — Real-time camera monitoring with instant alerts</li>
        <li><strong>Post-Exam Analysis</strong> — Upload recorded video for offline violation detection</li>
      </ul>
    </div>

    <button class="collapsible" onclick="toggleCollapsible(this)">
      📹 Step 3 — Select Camera <span class="chevron">▼</span>
    </button>
    <div class="collapsible-content">
      System auto-detects connected cameras. Supports laptop webcam and external USB cameras. Multi-room proctoring available — assign different cameras to different exam halls.
    </div>

    <button class="collapsible" onclick="toggleCollapsible(this)">
      🚀 Step 4 — Start Session & Monitor <span class="chevron">▼</span>
    </button>
    <div class="collapsible-content">
      Click <strong>Start Session</strong>. Live dashboard displays real-time violation log, detection stats, and live camera feed with bounding boxes. Audio beep fires on CRITICAL violations.
    </div>

    <button class="collapsible" onclick="toggleCollapsible(this)">
      📄 Step 5 — Generate PDF Report <span class="chevron">▼</span>
    </button>
    <div class="collapsible-content">
      Click <strong>Generate Report</strong> after session ends. Downloads a 9-page professional PDF evidence document including invigilator signature fields and UFM Committee Reference Number field.
    </div>
  </section>

  <!-- API -->
  <section class="section" id="api">
    <div class="section-title">
      <div class="icon" style="background:rgba(6,182,212,0.15)">🌐</div>
      API Endpoints
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Method</th><th>Endpoint</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/</td><td>Home — redirect to login</td></tr>
          <tr><td><span class="method method-post">POST</span></td><td class="endpoint-path">/login</td><td>Authenticate invigilator</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/logout</td><td>End session, redirect to login</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/selection</td><td>Mode selection page</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/select_camera</td><td>Camera selection page</td></tr>
          <tr><td><span class="method method-post">POST</span></td><td class="endpoint-path">/set_camera/&lt;id&gt;</td><td>Set active camera index</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/mode/&lt;m&gt;</td><td>Dashboard (live or recorded)</td></tr>
          <tr><td><span class="method method-post">POST</span></td><td class="endpoint-path">/start_session</td><td>Begin monitoring session</td></tr>
          <tr><td><span class="method method-post">POST</span></td><td class="endpoint-path">/end_session</td><td>End session, save stats</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/video_feed</td><td>MJPEG live video stream</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/get_logs</td><td>JSON violation log (last 20)</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/get_stats</td><td>JSON session statistics</td></tr>
          <tr><td><span class="method method-get">GET</span></td><td class="endpoint-path">/generate_report</td><td>Download PDF evidence report</td></tr>
          <tr><td><span class="method method-post">POST</span></td><td class="endpoint-path">/update_settings</td><td>Update detection thresholds</td></tr>
          <tr><td><span class="method method-post">POST</span></td><td class="endpoint-path">/upload_video</td><td>Upload recorded video file</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <!-- CONFIG -->
  <section class="section" id="config">
    <div class="section-title">
      <div class="icon" style="background:rgba(245,158,11,0.15)">⚙️</div>
      Configuration Thresholds
    </div>
    <div class="code-block" style="position:relative">
      <button class="copy-btn" onclick="copyCode(this)">Copy</button>
<pre><span class="comment"># ── Detection Thresholds ──────────────────────────────────────</span>
confidence_threshold     = <span class="number">0.60</span>   <span class="comment"># Mobile phone minimum confidence</span>
invigilator_threshold    = <span class="number">0.80</span>   <span class="comment"># Invigilator minimum confidence</span>

<span class="comment"># ── Peeking Detection ─────────────────────────────────────────</span>
YAW_THRESHOLD            = <span class="number">30.0</span>   <span class="comment"># Degrees — sideways head turn</span>
PITCH_THRESHOLD          = <span class="number">25.0</span>   <span class="comment"># Degrees — head must be level (not writing)</span>

<span class="comment"># ── State Machine ─────────────────────────────────────────────</span>
CRITICAL_DURATION        = <span class="number">3.0</span>    <span class="comment"># Seconds accumulated → CRITICAL alert</span>
WINDOW_DURATION          = <span class="number">5.0</span>    <span class="comment"># Seconds — sliding window size</span>
SESSION_RESET            = <span class="number">30.0</span>   <span class="comment"># Seconds inactive → session reset</span>

<span class="comment"># ── Ghost Box ─────────────────────────────────────────────────</span>
GHOST_TTL                = <span class="number">20</span>     <span class="comment"># Frames to persist invigilator position</span>
GHOST_MATCH_DISTANCE     = <span class="number">150</span>    <span class="comment"># Pixels — center point matching radius</span>

<span class="comment"># ── Mutual Gaze ───────────────────────────────────────────────</span>
MUTUAL_GAZE_MAX_DISTANCE = <span class="number">600</span>    <span class="comment"># Pixels horizontal between students</span>
MUTUAL_GAZE_MAX_VERTICAL = <span class="number">150</span>    <span class="comment"># Pixels vertical between students</span>
MUTUAL_GAZE_MIN_DURATION = <span class="number">3.0</span>    <span class="comment"># Seconds sustained → CRITICAL</span>

<span class="comment"># ── Multi-Face Detection ──────────────────────────────────────</span>
MEDIAPIPE_MAX_FACES      = <span class="number">10</span>     <span class="comment"># Maximum simultaneous faces</span>
MEDIAPIPE_INPUT_RES      = <span class="number">1280</span>   <span class="comment"># Pixels — MediaPipe resolution</span>
MIN_FACE_SIZE            = <span class="number">40</span>     <span class="comment"># Pixels — minimum face width for PnP</span></pre>
    </div>
  </section>

  <!-- STRUCTURE -->
  <section class="section" id="structure">
    <div class="section-title">
      <div class="icon" style="background:rgba(139,92,246,0.15)">📁</div>
      Project Structure
    </div>
    <div class="code-block">
<pre><span class="string">ExamGuard_Project/</span>
│
├── <span class="func">app.py</span>                  <span class="comment"># Core application (2726 lines)</span>
│   ├── Phase 1              <span class="comment"># Sensor fusion & ghost box system</span>
│   ├── Phase 2              <span class="comment"># Face tracking & cumulative state machine</span>
│   └── Phase 3              <span class="comment"># Mutual gaze pair detection</span>
│
├── <span class="func">best.pt</span>                 <span class="comment"># Trained YOLO11m weights (40.5MB)</span>
├── <span class="func">init_users.py</span>           <span class="comment"># User initialization script</span>
├── <span class="func">add_user.py</span>             <span class="comment"># Add new invigilator accounts</span>
├── <span class="func">users.json</span>              <span class="comment"># User credentials store</span>
├── <span class="func">requirements.txt</span>        <span class="comment"># Python dependencies</span>
│
├── <span class="string">templates/</span>
│   ├── <span class="func">login.html</span>          <span class="comment"># Authentication page</span>
│   ├── <span class="func">selection.html</span>      <span class="comment"># Mode selection (Live / Recorded)</span>
│   ├── <span class="func">select_camera.html</span>  <span class="comment"># Multi-room camera selection</span>
│   └── <span class="func">dashboard.html</span>      <span class="comment"># Main monitoring dashboard</span>
│
├── <span class="string">static/css/</span>
│   └── <span class="func">style.css</span>           <span class="comment"># Application styling</span>
│
├── <span class="string">Reports/</span>                <span class="comment"># Generated evidence (auto-created)</span>
│   └── <span class="string">YYYY-MM-DD/</span>
│       ├── <span class="func">signaling_*.jpg</span> <span class="comment"># Peeking evidence screenshots</span>
│       ├── <span class="func">mobile_phone_*.jpg</span>  <span class="comment"># Phone evidence screenshots</span>
│       ├── <span class="func">mutual_signal_*.jpg</span> <span class="comment"># Mutual gaze evidence</span>
│       └── <span class="func">report_*.pdf</span>    <span class="comment"># PDF evidence reports</span>
│
└── <span class="string">uploads/</span>                <span class="comment"># Uploaded video files</span></pre>
    </div>
  </section>

</div>

<!-- FOOTER -->
<div class="footer">
  <h3>🛡️ ExamGuard</h3>
  <p>Built for Academic Integrity — Protecting the value of honest education</p>
  <div class="info-grid">
    <div class="info-item"><div class="info-label">Project</div><div class="info-value">AI-Based Student Behavior Monitoring</div></div>
    <div class="info-item"><div class="info-label">Student</div><div class="info-value">Habiba (f22-0164)</div></div>
    <div class="info-item"><div class="info-label">University</div><div class="info-value">University of Haripur, KPK</div></div>
    <div class="info-item"><div class="info-label">Department</div><div class="info-value">BS Computer Science</div></div>
    <div class="info-item"><div class="info-label">Year</div><div class="info-value">2026</div></div>
    <div class="info-item"><div class="info-label">License</div><div class="info-value">Academic — All Rights Reserved</div></div>
  </div>
  <p style="color:var(--muted);font-size:13px">Made with ❤️ using Python • Flask • YOLO11m • MediaPipe • OpenCV</p>
</div>

<script>
  function toggleCollapsible(btn) {
    btn.classList.toggle('open');
    const content = btn.nextElementSibling;
    content.style.display = content.style.display === 'block' ? 'none' : 'block';
  }

  function copyCode(btn) {
    const pre = btn.parentElement.querySelector('pre');
    navigator.clipboard.writeText(pre.innerText).then(() => {
      btn.textContent = 'Copied!';
      setTimeout(() => btn.textContent = 'Copy', 2000);
    });
  }

  // Animate bars on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.querySelectorAll('.bar-fill').forEach(bar => {
          const w = bar.style.width;
          bar.style.width = '0';
          setTimeout(() => bar.style.width = w, 100);
        });
      }
    });
  }, { threshold: 0.3 });

  document.querySelectorAll('#results').forEach(s => observer.observe(s));

  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      document.querySelector(a.getAttribute('href'))
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
</script>
</body>
</html>
