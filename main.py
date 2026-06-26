import subprocess
import os
import time
import re
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from multiprocessing import Process

app = FastAPI()
current_pid = None

# =====================================================================
# 🛠️ INPUT KUNCI RAHASIA DI SINI
# =====================================================================
API_KEY_GOOGLE = "AIzaSyCmoEmQlqY0jJrbU1kP0NOnNFo-DZYvlVI"
TOKEN_BOT = "8874310524:AAFLCMqAGVyfeHaSRIfiCx5F89Jo9wQCxKw"
# =====================================================================

class StreamRequest(BaseModel):
    video_url: str
    stream_key: str
    duration_hours: float = 12.0

def dapatkan_link_gdrive_api(url_input: str) -> str:
    if "drive.google.com" not in url_input:
        return url_input
        
    match = re.search(r'/d/([^/]+)', url_input) or re.search(r'id=([^&]+)', url_input)
    if match:
        file_id = match.group(1)
        print(f"[SYSTEM] Mengonversi File ID Drive Besar: {file_id}")
        # Jalur API resmi ini akan menerobos halaman peringatan virus secara legal
        return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={API_KEY_GOOGLE}"
    return url_input

def proses_inti_ffmpeg(video_url: str, stream_key: str, duration_hours: float):
    print("=== [PROSES FFmpeg STRATEGI GOOGLE API DIMULAI] ===")
    
    # Otomatis konversi link Sheets kembali ke Google Drive jika user menginput link drive
    link_siap_putar = dapatkan_link_gdrive_api(video_url)
    print(f"-> Target Link Video Akhir: '{link_siap_putar[:60]}...' (Disamarkan)")
    
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    command = [
        "ffmpeg",
        "-re",
        "-stream_loop", "-1",
        "-i", link_siap_putar,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        rtmp_url
    ]
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        waktu_mulai = time.time()
        batas_detik = float(duration_hours) * 3600
        print(f"🚀 Streaming Didorong Lewat Jalur API! PID: {process.pid}")
        
        while True:
            if process.poll() is not None:
                output, _ = process.communicate()
                print(f"⚠️ LOG FFmpeg: \n{output.decode('utf-8', errors='ignore')}")
                break
            if (time.time() - waktu_mulai) >= batas_detik:
                process.terminate()
                process.wait()
                break
            time.sleep(5)
    except Exception as e:
        print(f"❌ Gangguan Sistem FFmpeg: {str(e)}")
    print("=== [PROSES FFmpeg BERAKHIR] ===")

@app.post("/start")
async def start_stream(request: StreamRequest):
    global current_pid
    print("=== [SINYAL START MASUK] ===")
    if current_pid:
        try: os.kill(current_pid, 9)
        except: pass
        current_pid = None
        
    p = Process(target=proses_inti_ffmpeg, args=(request.video_url, request.stream_key, request.duration_hours))
    p.start()
    current_pid = p.pid
    return {"status": "success", "message": f"Streaming dipicu dengan PID {p.pid}"}

@app.post("/stop")
async def stop_stream():
    global current_pid
    if current_pid:
        try: os.kill(current_pid, 9)
        except: pass
        current_pid = None
    return {"status": "success", "message": "Streaming dihentikan!"}

@app.post(f"/bot/{TOKEN_BOT}")
async def terima_pesan_telegram(update: dict):
    return {"status": "ok"}
