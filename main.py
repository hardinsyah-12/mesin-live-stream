import subprocess
import os
import signal
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Variabel global untuk menyimpan proses streaming yang sedang berjalan
current_stream_process = None

class StreamRequest(BaseModel):
    video_url: str
    stream_key: str

def run_ffmpeg(video_url: str, stream_key: str):
    global current_stream_process
    
    # URL tujuan RTMP YouTube
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    # Perintah sakti FFmpeg untuk me-loop video secara konstan ke YouTube
    # Menggunakan opsi -c:v copy agar super hemat CPU (tidak membebani server gratisan)
    command = [
        "ffmpeg",
        "-re",                  # Membaca video sesuai kecepatan aslinya (real-time)
        "-stream_loop", "-1",   # Loop video tanpa batas (terus-menerus)
        "-i", video_url,        # Input video dari link Google Drive yang Anda masukkan
        "-c:v", "copy",         # Copy video langsung tanpa rendering ulang (Hemat CPU!)
        "-c:a", "aac",          # Memastikan audio berformat AAC standar YouTube
        "-f", "flv",            # Format output untuk live streaming
        rtmp_url
    ]
    
    try:
        # Menjalankan FFmpeg di latar belakang
        current_stream_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        current_stream_process.wait()
    except Exception as e:
        print(f"Error saat streaming: {str(e)}")

@app.post("/start")
async def start_stream(request: StreamRequest, background_tasks: BackgroundTasks):
    global current_stream_process
    
    # Jika ada streaming yang masih jalan, matikan dulu sebelum mulai yang baru
    if current_stream_process and current_stream_process.poll() is None:
        raise HTTPException(status_code=400, detail="Streaming sedang berjalan. Hentikan dulu!")
    
    # Jalankan streaming di latar belakang agar web tidak memicu timeout
    background_tasks.add_task(run_ffmpeg, request.video_url, request.stream_key)
    return {"status": "success", "message": "Streaming berhasil dijalankan di server cloud!"}

@app.post("/stop")
async def stop_stream():
    global current_stream_process
    
    if current_stream_process and current_stream_process.poll() is None:
        # Mengirim sinyal berenti secara halus ke FFmpeg
        current_stream_process.terminate()
        current_stream_process = None
        return {"status": "success", "message": "Streaming berhasil dihentikan!"}
    
    return {"status": "error", "message": "Tidak ada streaming yang sedang berjalan."}

@app.get("/status")
async def get_status():
    global current_stream_process
    if current_stream_process and current_stream_process.poll() is None:
        return {"status": "streaming", "message": "Server sedang melakukan live streaming."}
    return {"status": "idle", "message": "Server sedang istirahat (tidak ada live)."}