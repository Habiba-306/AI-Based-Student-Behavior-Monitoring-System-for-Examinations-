// Dashboard Logic for ExamGuard
document.addEventListener('DOMContentLoaded', function () {
    const violationTable = document.getElementById('violation-table');
    const waitMsg = document.getElementById('wait-msg');
    const videoStream = document.getElementById('video-stream');
    const connectionStatus = document.getElementById('connection-status');
    const systemStatus = document.getElementById('system-status');

    // Handle video load error
    videoStream.onerror = function () {
        this.style.display = 'none';
        waitMsg.style.display = 'block';
        updateStatus('disconnected');
    };

    videoStream.onload = function () {
        this.style.display = 'block';
        waitMsg.style.display = 'none';
        updateStatus('connected');
    };

    function updateStatus(status) {
        if (status === 'connected') {
            connectionStatus.innerHTML = '<span class="status-dot active"></span> Live Feed Active';
            connectionStatus.classList.remove('text-danger');
            connectionStatus.classList.add('text-success');
            systemStatus.textContent = 'Monitoring Active';
            systemStatus.className = 'badge badge-green';
        } else {
            connectionStatus.innerHTML = '<span class="status-dot inactive"></span> Feed Disconnected';
            connectionStatus.classList.remove('text-success');
            connectionStatus.classList.add('text-danger');
            systemStatus.textContent = 'System Paused';
            systemStatus.className = 'badge badge-yellow';
        }
    }

    // ===========================================================
    // PHONE ALARM — Web Audio API (start/stop state model)
    // One AudioContext, one OscillatorNode created per incident.
    // Alarm starts on phone_detected: true (False→True transition).
    // Alarm stops when incident_active: false (phone gone >2 s).
    // ===========================================================
    let audioCtx = null;
    let alarmOscillator = null;
    let alarmGain = null;
    let phoneAlarmActive = false;   // Tracks our JS-side alarm state
    let flashBanner = null;         // Red banner DOM element (created on demand)

    function getAudioContext() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        // Resume if browser suspended it (autoplay policy)
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        return audioCtx;
    }

    function startPhoneAlarm() {
        if (phoneAlarmActive) return;   // Already running — don't stack
        phoneAlarmActive = true;

        const ctx = getAudioContext();

        // Gain node for volume control & clean fade-out
        alarmGain = ctx.createGain();
        alarmGain.gain.setValueAtTime(0.8, ctx.currentTime);
        alarmGain.connect(ctx.destination);

        // Two-tone siren: oscillator sweeps between 880 Hz and 1200 Hz
        alarmOscillator = ctx.createOscillator();
        alarmOscillator.type = 'square';
        alarmOscillator.frequency.setValueAtTime(880, ctx.currentTime);
        alarmOscillator.connect(alarmGain);
        alarmOscillator.start();

        // LFO to sweep frequency — creates siren effect
        const lfo = ctx.createOscillator();
        const lfoGain = ctx.createGain();
        lfo.frequency.setValueAtTime(2, ctx.currentTime);  // 2 Hz sweep rate
        lfoGain.gain.setValueAtTime(320, ctx.currentTime); // ±320 Hz sweep depth
        lfo.connect(lfoGain);
        lfoGain.connect(alarmOscillator.frequency);
        lfo.start();

        // Store lfo reference for cleanup
        alarmOscillator._lfo = lfo;
        alarmOscillator._lfoGain = lfoGain;

        // Show red flash banner
        showPhoneBanner(true);

        console.warn('[PHONE ALARM] Started — waiting for incident to resolve');
    }

    function stopPhoneAlarm() {
        if (!phoneAlarmActive) return;
        phoneAlarmActive = false;

        if (alarmOscillator) {
            // Fade out over 0.3 s to avoid click artifact
            const ctx = getAudioContext();
            alarmGain.gain.setTargetAtTime(0, ctx.currentTime, 0.1);
            try {
                alarmOscillator._lfo.stop(ctx.currentTime + 0.4);
                alarmOscillator.stop(ctx.currentTime + 0.4);
            } catch(e) { /* already stopped */ }
            alarmOscillator = null;
            alarmGain = null;
        }

        // Hide flash banner
        showPhoneBanner(false);

        console.log('[PHONE ALARM] Stopped — incident resolved');
    }

    function showPhoneBanner(visible) {
        if (!flashBanner) {
            flashBanner = document.createElement('div');
            flashBanner.id = 'phone-alert-banner';
            flashBanner.style.cssText = [
                'position:fixed', 'top:0', 'left:0', 'width:100%',
                'padding:14px', 'background:#cc0000',
                'color:#fff', 'font-size:1.1rem', 'font-weight:bold',
                'text-align:center', 'z-index:99999',
                'letter-spacing:1px', 'box-shadow:0 4px 16px rgba(0,0,0,0.5)',
                'animation:phonePulse 0.8s infinite alternate'
            ].join(';');
            flashBanner.textContent = '🚨 MOBILE PHONE DETECTED — VIOLATION IN PROGRESS';

            // Inject pulse keyframes once
            if (!document.getElementById('phone-alarm-style')) {
                const style = document.createElement('style');
                style.id = 'phone-alarm-style';
                style.textContent = `
                    @keyframes phonePulse {
                        from { background:#cc0000; }
                        to   { background:#ff2222; }
                    }`;
                document.head.appendChild(style);
            }
            document.body.prepend(flashBanner);
        }
        flashBanner.style.display = visible ? 'block' : 'none';
    }

    // ===========================================================
    // PHONE STATE POLLER — checks /phone_alert_status every 1 s
    // Only reacts to state TRANSITIONS (not repeated same-state)
    // ===========================================================
    let prevPhoneDetected = false;

    function pollPhoneStatus() {
        fetch('/phone_alert_status')
            .then(res => res.json())
            .then(data => {
                const detected = data.incident_active === true;

                if (detected && !prevPhoneDetected) {
                    // Transition: False → True  →  START alarm
                    startPhoneAlarm();
                } else if (!detected && prevPhoneDetected) {
                    // Transition: True → False  →  STOP alarm
                    stopPhoneAlarm();
                }
                prevPhoneDetected = detected;
            })
            .catch(() => {
                // Server not reachable — stop alarm for safety
                if (phoneAlarmActive) stopPhoneAlarm();
            });
    }

    setInterval(pollPhoneStatus, 1000);

    // ===========================================================
    // VIOLATION LOG POLLER — polls /get_logs every 1 s
    // ===========================================================
    setInterval(() => {
        fetch('/get_logs')
            .then(res => res.json())
            .then(data => {
                let rows = '';

                if (data && data.length > 0) {
                    if (videoStream.style.display !== 'none') {
                        updateStatus('connected');
                    }

                    data.forEach(log => {
                        const typeClass = getViolationClass(log.type);
                        rows += `
                            <tr class="fade-in">
                                <td><span class="font-mono">${log.time}</span></td>
                                <td><span class="badge ${typeClass}">${formatLabel(log.type)}</span></td>
                                <td>
                                    <div class="progress-bar-container">
                                        <div class="progress-bar" style="width: ${log.conf * 100}%"></div>
                                        <span class="progress-text">${Math.round(log.conf * 100)}%</span>
                                    </div>
                                </td>
                                <td>
                                    <span class="icon-check">✅</span> Evidence Saved
                                </td>
                            </tr>
                        `;
                    });
                } else {
                    rows = `
                        <tr>
                            <td colspan="4" class="empty-state">
                                <div class="empty-icon">🛡️</div>
                                <p>No violations detected yet.</p>
                                <small>AI is actively monitoring the session.</small>
                            </td>
                        </tr>
                    `;
                }

                if (violationTable.innerHTML !== rows) {
                    violationTable.innerHTML = rows;
                }
            })
            .catch(err => {
                console.log("Waiting for server...");
                updateStatus('disconnected');
            });
    }, 1000);

    function formatLabel(label) {
        return label.replace(/_/g, ' ').toUpperCase();
    }

    function getViolationClass(type) {
        const t = type.toLowerCase();
        if (t.includes('mobile') || t.includes('phone')) return 'badge-red';
        if (t.includes('directional')) return 'badge-red';
        if (t.includes('signal') || t.includes('mutual')) return 'badge-red';
        if (t.includes('peek')) return 'badge-yellow';
        return 'badge-blue';
    }
});
