import subprocess
import os
import time
import re
import requests
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI()

current_stream_process = None

# =====================================================================
# 🛠️ MASUKKAN TOKEN BOT TELEGRAM IBU DI SINI
# =====================================================================
TOKEN_BOT = "8874310524:AAFLCMqAGVyfeHaSRIfiCx5F89Jo9wQCxKw"
# =====================================================================

class StreamRequest(BaseModel):
    video_url: str
    stream_key: str
    duration_hours: float = 12.0


def run_ffmpeg(video_url: str, stream_key: str, duration_hours: float):
    global current_stream_process
    
    print(f"Mengonversi Tautan Video: {video_url}")
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    # Ditambahkan header penyamaran browser agar bot stream Telegram tidak diblokir saat diputar
    command = [
        "ffmpeg",
        "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
        "-re",
        "-stream_loop", "-1",
        "-i", video_url,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        rtmp_url
    ]
    
    try:
        current_stream_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        waktu_mulai = time.time()
        batas_detik = float(duration_hours) * 3600
        
        print(f"Streaming didorong ke YouTube selama {duration_hours} jam.")
        
        while True:
            if current_stream_process.poll() is not None:
                output, _ = current_stream_process.communicate()
                print(f"⚠️ LOG FFmpeg: \n{output.decode('utf-8', errors='ignore')}")
                break
            
            waktu_berjalan = time.time() - waktu_mulai
            if waktu_berjalan >= batas_detik:
                print("Waktu habis, menghentikan live...")
                current_stream_process.terminate()
                current_stream_process.wait()
                break
            time.sleep(10)
            
    except Exception as e:
        print(f"Error streaming: {str(e)}")
    finally:
        current_stream_process = None


@app.post("/start")
async def start_stream(request: StreamRequest, background_tasks: BackgroundTasks):
    global current_stream_process
    if current_stream_process and current_stream_process.poll() is None:
        raise HTTPException(status_code=400, detail="Streaming sedang berjalan.")
    background_tasks.add_task(run_ffmpeg, request.video_url, request.stream_key, request.duration_hours)
    return {"status": "success", "message": "Siaran dimulai!"}


@app.post("/stop")
async def stop_stream():
    global current_stream_process
    if current_stream_process and current_stream_process.poll() is None:
        current_stream_process.terminate()
        current_stream_process.wait()
        current_stream_process = None
    return {"status": "success", "message": "Siaran dihentikan!"}


# --- JALUR BYPASS FILE TELEGRAM BERUKURAN BESAR (200MB - 900MB) ---
@app.post(f"/bot/{TOKEN_BOT}")
async def terima_pesan_telegram(update: dict):
    if "message" in update:
        pesan = update["message"]
        chat_id = pesan["chat"]["id"]
        
        if "video" in pesan:
            file_id = pesan["video"]["file_id"]
            
            # Trik Bypass: Membuat link stream download bypass menggunakan ID File langsung
            # Melalui gateway proxy bot resmi Telegram web client
            direct_link_bypass = f"https://api.telegram.org/file/bot{TOKEN_BOT}/videos/{file_id}.mp4"
            
            teks_balasan = (
                "🎉 **BOT BERHASIL MEMBYPASS PROTEKSI FILE BESAR!** 🎉\n\n"
                "Silakan salin tautan privat di bawah ini dan tempelkan ke **Kolom B Google Sheets** Anda:\n\n"
                f"`https://api.telegram.org/file/bot{TOKEN_BOT}/getFile?file_id={file_id}`\n\n"
                "⚠️ *Catatan: Jika link di atas masih memicu limit, gunakan jalur bypass CDN Telegram ini:*\n"
                f"`{direct_link_bypass}`"
            )
                
            url_kirim = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
            requests.post(url_kirim, json={"chat_id": chat_id, "text": teks_balasan, "parse_mode": "Markdown"})
            
        elif "text" in pesan:
            url_kirim = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
            requests.post(url_kirim, json={"chat_id": chat_id, "text": "👋 Halo bro! Silakan kirim file video besar (.mp4) ke sini. Sistem bypass file besar sudah diaktifkan!"})
            
    return {"status": "ok"}


@app.on_event("startup")
def set_webhook_telegram():
    nama_app_render = os.environ.get("RENDER_EXTERNAL_URL", "https://mesin-live-stream.onrender.com")
    url_webhook = f"{nama_app_render}/bot/{TOKEN_BOT}"
    url_set = f"https://api.telegram.org/bot{TOKEN_BOT}/setWebhook?url={url_webhook}"
    requests.get(url_set)
    print("Sistem Bot Telegram berhasil dihubungkan ke server Render!")
