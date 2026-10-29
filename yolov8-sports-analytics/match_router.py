import os
import subprocess
import time

def process_match_video(match_video_path, match_id, user_tier):
    print(f"\n🏁 Match {match_id} finished. Processing video for tier: {user_tier.upper()}")
    
    if user_tier == "free":
        # --- FREE TIER LOGIC ---
        print("Uploading full raw match to YouTube...")
        
        # In a real app, this would call your YouTube API script
        # e.g., subprocess.run(['python3', 'youtube_uploader.py', match_video_path])
        youtube_url = mock_youtube_upload(match_video_path)
        
        print(f"✅ Success! Match available at: {youtube_url}")
        update_firestore_record(match_id, {"full_video_url": youtube_url, "highlights": []})

    elif user_tier == "premium":
        # --- PREMIUM TIER LOGIC ---
        print("Premium user detected. Firing up the AI Highlight Engine...")
        
        # 1. Run the YOLO highlight extractor we built
        # We pass the match_video_path as an argument to the extractor
        subprocess.run(['python3', 'highlight_engine.py', '--input', match_video_path])
        
        # 2. Find the generated clips in the output folder
        output_dir = 'elite_courts_highlights'
        clips = [f for f in os.listdir(output_dir) if f.endswith('.mp4')]
        
        if not clips:
            print("No highlights found for this match.")
            return

        print(f"Uploading {len(clips)} highlight clips to Firebase Storage...")
        
        # In a real app, this would use the firebase-admin SDK
        firebase_urls = mock_firebase_upload(output_dir, clips, match_id)
        
        print("✅ AI Processing Complete!")
        update_firestore_record(match_id, {"highlights": firebase_urls})

    else:
        print("❌ Error: Unknown user tier.")

# --- Helper Functions (To be replaced with actual API calls) ---

def mock_youtube_upload(video_path):
    time.sleep(2) # Simulate upload time
    return "https://youtube.com/watch?v=unlisted_id_123"

def mock_firebase_upload(directory, clips, match_id):
    urls = []
    for clip in clips:
        # Simulate firebase-admin bucket.blob().upload_from_filename()
        time.sleep(1) 
        urls.append(f"gs://elite-courts.appspot.com/highlights/{match_id}/{clip}")
    return urls

def update_firestore_record(match_id, data):
    # Simulate writing to your Firestore database so the app can see it
    print(f"📝 Updating Firebase Document for Match {match_id}: {data}")

# --- Test the Router ---
if __name__ == "__main__":
    # Test a free user
    process_match_video("tactical_match_test.mp4", "match_001", "free")
    
    print("-" * 40)
    
    # Test a premium user
    process_match_video("tactical_match_test.mp4", "match_002", "premium")