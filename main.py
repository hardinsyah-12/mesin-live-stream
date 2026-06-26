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
    
    # PELACAKAN 2: Memastikan fungsi pembacaan dimulai
    print("=== [PROSES FFmpeg DIMULAI] ===")
    print(f"-> Menerima URL Video: '{video_url}'")
    print(f"-> Menerima Stream Key: '{stream_key[:5]}...' (Disamarkan)")
    print(f"-> Durasi Terkunci: {duration_hours} Jam")
    
    if not video_url or not stream_key:
        print("❌ EROR KRUSIAL: Data Link Video atau Stream Key Kosong / Tidak Terbaca!")
        return

    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
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
        
        print("🚀 FFmpeg Berhasil Dipicu! Mengalirkan data ke YouTube...")
        
        while True:
            if current_stream_process.poll() is not None:
                output, _ = current_stream_process.communicate()
                print(f"⚠️ LOG FFmpeg MOGOK: \n{output.decode('utf-8', errors='ignore')}")
                break
            
            waktu_berjalan = time.time() - waktu_mulai
            if waktu_berjalan >= batas_detik:
                print("Waktu jadwal habis, menghentikan live otomatis...")
                current_stream_process.terminate()
                current_stream_process.wait()
                break
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Gangguan Sistem FFmpeg: {str(e)}")
    finally:
        current_stream_process = None
        print("=== [PROSES FFmpeg BERAKHIR/DIHENTIKAN] ===")


@app.post("/start")
async def start_stream(request: StreamRequest, background_tasks: BackgroundTasks):
    global current_stream_process
    
    # PELACAKAN 1: Mencetak payload mentah yang masuk dari Google Sheets
    print("=== [SINYAL START MASUK] ===")
    print(f"Payload Mentah: video_url={request.video_url}, duration={request.duration_hours}")
    
    if current_stream_process and current_stream_process.poll() is None:
        print("⚠️ Peringatan: Ada streaming yang masih aktif di memori.")
        raise HTTPException(status_code=400, detail="Streaming sedang berjalan.")
        
    background_tasks.add_task(run_ffmpeg, request.video_url, request.stream_key, request.duration_hours)
    return {"status": "success", "message": "Perintah Start Diterima Python!"}


@app.post("/stop")
async def stop_stream():
    global current_stream_process
    print("=== [SINYAL STOP MASUK] ===")
    if current_stream_process and current_stream_process.poll() is None:
        current_stream_process.terminate()
        current_stream_process.wait()
        current_stream_process = None
        print("✅ Berhasil mematikan paksa FFmpeg.")
    return {"status": "success", "message": "Siaran dihentikan!"}


@app.post(f"/bot/{TOKEN_BOT}")
async def terima_pesan_telegram(update: dict):
    if "message" in update:
        pesan = update["message"]
        chat_id = pesan["chat"]["id"]
        
        if "video" in pesan:
            file_id = pesan["video"]["file_id"]
            direct_link_bypass = f"https://api.telegram.org/file/bot{TOKEN_BOT}/videos/{file_id}.mp4"
            
            teks_balasan = (
                "🎉 **BOT BERHASIL MEMBYPASS PROTEKSI FILE BESAR!** 🎉\n\n"
                "Silakan gunakan jalur alternatif langsung ini untuk dimasukkan ke **Kolom B Google Sheets** Anda:\n\n"
                f"`{direct_link_bypass}`"
            )
            url_kirim = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
            requests.post(url_kirim, json={"chat_id": chat_id, "text": teks_balasan, "parse_mode": "Markdown"})
    return {"status": "ok"}


@app.on_event("startup")
def set_webhook_telegram():
    nama_app_render = os.environ.get("RENDER_EXTERNAL_URL", "https://mesin-live-stream.onrender.com")
    url_webhook = f"{nama_app_render}/bot/{TOKEN_BOT}"
    url_set = f"https://api.telegram.org/bot{TOKEN_BOT}/setWebhook?url={url_webhook}"
    requests.get(url_set)
    print("Sistem Bot Telegram berhasil dihubungkan ke server Render!")
