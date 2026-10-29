import os
import datetime
import time
import subprocess
import queue
import firebase_admin
from firebase_admin import credentials, firestore

# ==============================================================================
# 1. FIREBASE INITIALIZATION 
# ==============================================================================
cred = credentials.Certificate("serviceAccountKey.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ==============================================================================
# 2. CONFIGURATION 
# ==============================================================================
YOUTUBE_STREAM_KEY = "pacp-we6v-b3d5-9dvf-dhpz"
RTMP_URL = os.getenv("YOUTUBE_STREAM_URL", "rtmp://a.rtmp.youtube.com/live2")
STREAM_KEY = os.getenv("YOUTUBE_STREAM_KEY", YOUTUBE_STREAM_KEY)

OUTPUT_DIR = "elite_courts_raw_matches"
RESOLUTION = "1280x720"
RECORD_FPS = 30.0  

ffmpeg_proc = None
is_pipeline_active = False
log_file = None

command_queue = queue.Queue()

# ==============================================================================
# 3. DYNAMIC HARDWARE SCANNER ENGINE
# ==============================================================================
def get_hardware_indexes():
    """
    Dynamically scans macOS AVFoundation devices to locate the exact indexes
    for 'Global Shutter Camera' and 'MacBook Pro Microphone'.
    """
    print("🔍 Scanning connected system media hardware...")
    cmd = ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', '']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _, stderr = proc.communicate()
    
    video_idx = None
    audio_idx = None
    in_video_section = False
    in_audio_section = False
    
    for line in stderr.split('\n'):
        if "AVFoundation video devices:" in line:
            in_video_section = True
            in_audio_section = False
            continue
        elif "AVFoundation audio devices:" in line:
            in_video_section = False
            in_audio_section = True
            continue
            
        if in_video_section and "Global Shutter Camera" in line:
            try:
                video_idx = line.split('[')[2].split(']')[0]
                print(f"   📹 Detected Global Shutter Camera at index: {video_idx}")
            except Exception:
                pass
        elif in_audio_section and "MacBook Pro Microphone" in line:
            try:
                audio_idx = line.split('[')[2].split(']')[0]
                print(f"   🎙️ Detected MacBook Pro Microphone at index: {audio_idx}")
            except Exception:
                pass

    if video_idx is None:
        print("⚠️ CRITICAL WARNING: 'Global Shutter Camera' not found! Defaulting to index 0.")
        video_idx = "0"
    if audio_idx is None:
        print("⚠️ WARNING: 'MacBook Pro Microphone' not found! Defaulting to index 0.")
        audio_idx = "0"
        
    return f"{video_idx}:{audio_idx}"

# ==============================================================================
# 4. PURE FFMPEG ENGINE
# ==============================================================================
def start_match_pipeline(enable_stream=False):
    """Launches FFmpeg with improved audio buffering to eliminate choppiness."""
    global ffmpeg_proc, is_pipeline_active, log_file
    
    if is_pipeline_active:
        return

    resolved_device_indexes = get_hardware_indexes()
    print(f"⚙️ Mapping Arena Media Hardware via indices: [{resolved_device_indexes}]...")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(OUTPUT_DIR, f"match_{timestamp}.mp4")

    # ── FIX 1: thread_queue_size absorbs mic packet jitter before FFmpeg
    #           processes them — the main cause of choppy audio on macOS.
    # ── FIX 2: async=44100 gives the resampler a full 1-second smoothing
    #           buffer instead of just 1 sample (async=1).
    # ── FIX 3: Added -af loudnorm to normalize mic input levels which
    #           prevents sudden volume drops that sound like choppiness.

    cmd = [
        'ffmpeg', '-y',

        # ── Input: video device with large thread queue to prevent drop
        '-f', 'avfoundation',
        '-framerate', str(RECORD_FPS),
        '-video_size', RESOLUTION,
        '-thread_queue_size', '4096',       # FIX 1: absorbs capture jitter
        '-i', resolved_device_indexes,
    ]

    # Shared audio filter chain used in both modes
    audio_filter = (
        'aresample=async=44100'             # FIX 2: full 1-second resample buffer
        ':min_hard_comp=0.100000'
        ':first_pts=0,'
        'loudnorm'                          # FIX 3: normalize mic levels
    )

    if enable_stream and STREAM_KEY:
        print("🚀 Booting Engine: [Local Recording + Live YouTube Broadcast]...")
        cmd += [
            '-filter_complex',
            f'[0:v]split=2[v1][v2];[0:a]{audio_filter},asplit=2[a1][a2]',

            # Output 1: Local file
            '-map', '[v1]', '-map', '[a1]',
            '-c:v', 'h264_videotoolbox', '-b:v', '4000k', '-realtime', '1',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',  # raised to 192k
            '-pix_fmt', 'yuv420p', filepath,

            # Output 2: RTMP stream
            '-map', '[v2]', '-map', '[a2]',
            '-c:v', 'h264_videotoolbox', '-realtime', '1', '-g', '60',
            '-b:v', '4500k', '-maxrate', '5000k', '-bufsize', '9000k',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',  # raised to 192k
            '-pix_fmt', 'yuv420p',
            '-f', 'flv', f"{RTMP_URL}/{STREAM_KEY}"
        ]
    else:
        print("📹 Booting Engine: [Local Recording Only]...")
        cmd += [
            '-map', '0:v', '-map', '0:a',
            '-af', audio_filter,
            '-c:v', 'h264_videotoolbox', '-b:v', '4000k', '-realtime', '1',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',  # raised to 192k
            '-pix_fmt', 'yuv420p',
            filepath
        ]

    log_file = open("ffmpeg_debug.log", "w")
    ffmpeg_proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=log_file,
        stdin=subprocess.PIPE
    )
    is_pipeline_active = True
    print(f"✅ Hardware capture pipeline initialized. Recording to: {filepath}")

def stop_match_pipeline():
    """Gracefully shuts down FFmpeg, escalating to terminate/kill if it won't quit in time."""
    global ffmpeg_proc, is_pipeline_active, log_file
    if not is_pipeline_active:
        return
        
    print("\n🛑 Halting court hardware capture engines cleanly...")
    is_pipeline_active = False
    
    if ffmpeg_proc:
        try:
            if ffmpeg_proc.poll() is None:
                if ffmpeg_proc.stdin:
                    ffmpeg_proc.stdin.write(b'q\n')
                    ffmpeg_proc.stdin.flush()
                # FIX 4: RTMP outputs can take longer than 5s to flush/close on
                # shutdown. If the graceful 'q' quit doesn't land in time, escalate
                # to terminate() and finally kill() instead of letting the
                # TimeoutExpired exception crash the whole daemon loop.
                try:
                    ffmpeg_proc.wait(timeout=5)
                    print("💾 Media engine closed safely. Video file saved.")
                except subprocess.TimeoutExpired:
                    print("⚠️ FFmpeg didn't quit gracefully in time — sending SIGTERM...")
                    ffmpeg_proc.terminate()
                    try:
                        ffmpeg_proc.wait(timeout=5)
                        print("💾 Media engine terminated. Video file saved.")
                    except subprocess.TimeoutExpired:
                        print("⚠️ Still not responding — killing process (file may be incomplete).")
                        ffmpeg_proc.kill()
                        ffmpeg_proc.wait(timeout=5)
            else:
                print("⚠️ FFmpeg exited early before shutdown command was processed.")
        except (BrokenPipeError, OSError):
            print("⚠️ Pipe broken. Process terminated abruptly by the OS.")
        finally:
            if ffmpeg_proc.poll() is None:
                ffmpeg_proc.kill()
            ffmpeg_proc = None
            
    if log_file:
        log_file.close()
        log_file = None
        
    print("💤 Hardware returned to standby mode.\n")

# ==============================================================================
# 5. FIRESTORE REALTIME DAEMON HOOK
# ==============================================================================
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        if not doc.exists:
            continue
        status = doc.to_dict().get("status", "idle")
        print(f"🔄 Firestore Update → Command Received: {status.upper()}")
        command_queue.put(status)

db.collection("arena_hardware_control").document("court_1").on_snapshot(on_snapshot)

# ==============================================================================
# 6. MAIN EXECUTION LOOP
# ==============================================================================
print("⚡ Elite Courts Listener Daemon Online. Waiting for cloud triggers...")
print("   Tip: check ffmpeg_debug.log for audio error details if issues persist.\n")

try:
    while True:
        try:
            status = command_queue.get_nowait()
            
            if status == "idle" and is_pipeline_active:
                stop_match_pipeline()
            elif status == "recording" and not is_pipeline_active:
                start_match_pipeline(enable_stream=False)
            elif status == "streaming" and not is_pipeline_active:
                start_match_pipeline(enable_stream=True)
                
            command_queue.task_done()
        except queue.Empty:
            pass
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nShutting down daemon safely via user interrupt.")
    stop_match_pipeline()