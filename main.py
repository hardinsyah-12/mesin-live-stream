import subprocess
import os
import signal
import time
import re
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI()

current_stream_process = None

class StreamRequest(BaseModel):
    video_url: str
    stream_key: str
    duration_hours: float = 12.0

# --- FUNGSI SAKTI: MENGUBAH LINK DRIVE MENJADI DIRECT LINK MP4 ---
def get_direct_download_link(url: str) -> str:
    # Jika bukan link google drive, kembalikan url asli
    if "drive.google.com" not in url:
        return url
    
    # Mencari pola ID File Google Drive
    match = re.search(r'/d/([^/]+)', url) or re.search(r'id=([^&]+)', url)
    if match:
        file_id = match.group(1)
        # Mengubahnya menjadi URL Direct Stream/Download khusus video mentah
        return f"https://docs.google.com/uc?export=download&id={file_id}"
    return url

def run_ffmpeg(video_url: str, stream_key: str, duration_hours: float):
    global current_stream_process
    
    # Konversi URL ke tautan unduhan langsung agar FFmpeg bisa membaca videonya
    direct_video_url = get_direct_download_link(video_url)
    print(f"Mengonversi Link. Hasil Direct Link: {direct_video_url}")
    
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    command = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", direct_video_url,  # Menggunakan direct link yang sudah dikonversi
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        rtmp_url
    ]
    
    try:
        current_stream_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        waktu_mulai = time.time()
        batas_detik = float(duration_hours) * 3600
        
        print(f"Streaming dimulai ke YouTube. Berhenti otomatis dalam {duration_hours} jam.")
        
        while True:
            if current_stream_process.poll() is not None:
                # Ambil pesan eror dari output FFmpeg jika ada
                output, _ = current_stream_process.communicate()
                print(f"FFmpeg berhenti. Log output: {output.decode('utf-8', errors='ignore')}")
                break
            
            waktu_berjalan = time.time() - waktu_mulai
            if waktu_berjalan >= batas_detik:
                print("Batas waktu terpenuhi! Mematikan live otomatis...")
                current_stream_process.terminate()
                current_stream_process.wait()
                break
                
            time.sleep(10)
            
    except Exception as e:
        print(f"Error saat streaming: {str(e)}")
    finally:
        current_stream_process = None

@app.post("/start")
async def start_stream(request: StreamRequest, background_tasks: BackgroundTasks):
    global current_stream_process
    
    if current_stream_process and current_stream_process.poll() is None:
        raise HTTPException(status_code=400, detail="Streaming sedang berjalan. Hentikan dulu!")
    
    background_tasks.add_task(run_ffmpeg, request.video_url, request.stream_key, request.duration_hours)
    return {
        "status": "success", 
        "message": f"Streaming dikirim ke Render dengan durasi {request.duration_hours} jam!"
    }

@app.post("/stop")
async def stop_stream():
    global current_stream_process
    
    if current_stream_process and current_stream_process.poll() is None:
        current_stream_process.terminate()
        current_stream_process.wait()
        current_stream_process = None
        return {"status": "success", "message": "Streaming dihentikan manual!"}
    
    return {"status": "error", "message": "Tidak ada streaming yang sedang berjalan."}

@app.get("/status")
async def get_status():
    global current_stream_process
    if current_stream_process and current_stream_process.poll() is None:
        return {"status": "streaming", "message": "Server sedang melakukan live streaming."}
    return {"status": "idle", "message": "Server sedang istirahat."}
