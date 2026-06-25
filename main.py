import subprocess
import os
import signal
import time
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Variabel global untuk menyimpan proses streaming yang sedang berjalan
current_stream_process = None

class StreamRequest(BaseModel):
    video_url: str
    stream_key: str
    duration_hours: float = 12.0  # Tambahan: Default otomatis 12 jam jika tidak diisi

def run_ffmpeg(video_url: str, stream_key: str, duration_hours: float):
    global current_stream_process
    
    # URL tujuan RTMP YouTube
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    command = [
        "ffmpeg",
        "-re",                  # Membaca video sesuai kecepatan aslinya
        "-stream_loop", "-1",   # Loop video tanpa batas
        "-i", video_url,        # Input video dari link Google Drive
        "-c:v", "copy",         # Hemat CPU!
        "-c:a", "aac",          # Audio standar YouTube
        "-f", "flv",            # Format output
        rtmp_url
    ]
    
    try:
        # Menjalankan FFmpeg di latar belakang
        current_stream_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        # --- LOGIKA PENGHENTIAN OTOMATIS BERDASARKAN DURASI ---
        waktu_mulai = time.time()
        batas_detik = float(duration_hours) * 3600  # Mengubah jam menjadi hitungan detik
        
        print(f"Streaming dimulai. Otomatis berhenti dalam {duration_hours} jam.")
        
        while True:
            # 1. Cek apakah FFmpeg mati sendiri karena eror jaringan/link video rusak
            if current_stream_process.poll() is not None:
                print("FFmpeg berhenti di tengah jalan.")
                break
            
            # 2. Hitung apakah durasi streaming sudah melewati batas jam yang diminta
            waktu_berjalan = time.time() - waktu_mulai
            if waktu_berjalan >= batas_detik:
                print(f"Batas waktu {duration_hours} jam terpenuhi! Mematikan live otomatis...")
                current_stream_process.terminate()
                current_stream_process.wait()
                break
                
            time.sleep(10)  # Cek ulang setiap 10 detik agar hemat memori server
            
    except Exception as e:
        print(f"Error saat streaming: {str(e)}")
    finally:
        current_stream_process = None

@app.post("/start")
async def start_stream(request: StreamRequest, background_tasks: BackgroundTasks):
    global current_stream_process
    
    # Jika ada streaming yang masih jalan, matikan dulu sebelum mulai yang baru
    if current_stream_process and current_stream_process.poll() is None:
        raise HTTPException(status_code=400, detail="Streaming sedang berjalan. Hentikan dulu!")
    
    # Jalankan streaming di latar belakang beserta data durasi jamnya
    background_tasks.add_task(run_ffmpeg, request.video_url, request.stream_key, request.duration_hours)
    return {
        "status": "success", 
        "message": f"Streaming berhasil dijalankan di server cloud selama {request.duration_hours} jam otomatis!"
    }

@app.post("/stop")
async def stop_stream():
    global current_stream_process
    
    if current_stream_process and current_stream_process.poll() is None:
        current_stream_process.terminate()
        current_stream_process.wait()
        current_stream_process = None
        return {"status": "success", "message": "Streaming berhasil dihentikan secara manual!"}
    
    return {"status": "error", "message": "Tidak ada streaming yang sedang berjalan."}

@app.get("/status")
async def get_status():
    global current_stream_process
    if current_stream_process and current_stream_process.poll() is None:
        return {"status": "streaming", "message": "Server sedang melakukan live streaming."}
    return {"status": "idle", "message": "Server sedang istirahat (tidak ada live)."}
