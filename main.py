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
# 🛠️ TOKEN BOT TELEGRAM RESMI IBU
# =====================================================================
TOKEN_BOT = "8874310524:AAFLCMqAGVyfeHaSRIfiCx5F89Jo9wQCxKw"
# =====================================================================

class StreamRequest(BaseModel):
    video_url: str
    stream_key: str
    duration_hours: float = 12.0

def dapatkan_jalur_resmi_telegram(url_input: str) -> str:
    # Jika bukan link telegram, biarkan apa adanya
    if "api.telegram.org" not in url_input:
        return url_input
        
    # Ekstrak file_id dari link apa pun yang diinput user
    match = re.search(r'file_id=([A-Za-z0-9_-]+)', url_input) or re.search(r'/videos/([A-Za-z0-9_-]+)', url_input)
    if not match:
        return url_input
        
    file_id = match.group(1)
    print(f"[SYSTEM] Mengekstrak File ID Sukses: {file_id}")
    
    # Minta jalur asli ke Telegram API resmi
    url_get_file = f"https://api.telegram.org/bot{TOKEN_BOT}/getFile?file_id={file_id}"
    try:
        respon = requests.get(url_get_file, timeout=10).json()
        if respon.get("ok"):
            file_path = respon["result"]["file_path"]
            # Ini adalah link download file streaming resmi dari cloud Telegram!
            link_resmi = f"https://api.telegram.org/file/bot{TOKEN_BOT}/{file_path}"
            return link_resmi
    except Exception as e:
        print(f"Gagal koneksi ke Telegram API: {str(e)}")
        
    return url_input

def run_ffmpeg(video_url: str, stream_key: str, duration_hours: float):
    global current_stream_process
    
    print("=== [PROSES FFmpeg DIMULAI] ===")
    
    # Konversi link ke jalur unduhan stream resmi Telegram
    link_siap_putar = dapatkan_jalur_resmi_telegram(video_url)
    print(f"-> Target Link Video: '{link_siap_putar}'")
    
    if not stream_key:
        print("❌ EROR: Stream Key Kosong!")
        return

    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    command = [
        "ffmpeg",
        "-headers", f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
        "-re",
        "-stream_loop", "-1",
        "-i", link_siap_putar,
        "-c:v", "copy",
        "-c:a", "aac",
        "-f", "flv",
        rtmp_url
    ]
    
    try:
        current_stream_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        waktu_mulai = time.time()
        batas_detik = float(duration_hours) * 3600
        
        print("🚀 Mesin FFmpeg Aktif! Mendorong data streaming ke YouTube...")
        
        while True:
            if current_stream_process.poll() is not None:
                output, _ = current_stream_process.communicate()
                print(f"⚠️ LOG OUTPUT FFmpeg: \n{output.decode('utf-8', errors='ignore')}")
                break
            
            waktu_berjalan = time.time() - waktu_mulai
            if waktu_berjalan >= batas_detik:
                print("Durasi habis, mematikan live otomatis.")
                current_stream_process.terminate()
                current_stream_process.wait()
                break
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Gangguan Sistem FFmpeg: {str(e)}")
    finally:
        current_stream_process = None
        print("=== [PROSES FFmpeg BERAKHIR] ===")


@app.post("/start")
async def start_stream(request: StreamRequest, background_tasks: BackgroundTasks):
    global current_stream_process
    
    print("=== [SINYAL START MASUK] ===")
    print(f"Payload Mentah: video_url={request.video_url}, duration={request.duration_hours}")
    
    if current_stream_process and current_stream_process.poll() is None:
        print("⚠️ Hentikan proses lama yang masih mengambang...")
        current_stream_process.terminate()
        current_stream_process.wait()
        current_stream_process = None
        
    background_tasks.add_task(run_ffmpeg, request.video_url, request.stream_key, request.duration_hours)
    return {"status": "success", "message": "Perintah diproses server!"}


@app.post("/stop")
async def stop_stream():
    global current_stream_process
    print("=== [SINYAL STOP MASUK] ===")
    if current_stream_process and current_stream_process.poll() is None:
        current_stream_process.terminate()
        current_stream_process.wait()
        current_stream_process = None
        print("✅ FFmpeg berhasil dimatikan.")
    return {"status": "success", "message": "Siaran dihentikan!"}


@app.post(f"/bot/{TOKEN_BOT}")
async def terima_pesan_telegram(update: dict):
    if "message" in update:
        pesan = update["message"]
        chat_id = pesan["chat"]["id"]
        
        if "video" in pesan:
            file_id = pesan["video"]["file_id"]
            # Bot sekarang cukup memberikan link ID konvensional yang bersih ke Ibu Feni
            link_sheets = f"https://api.telegram.org/file/bot{TOKEN_BOT}/getFile?file_id={file_id}"
            
            teks_balasan = (
                "🎉 **ID VIDEO BERHASIL DIAMBIL!** 🎉\n\n"
                "Silakan salin seluruh tautan di bawah ini dan masukkan ke **Kolom B Google Sheets** Anda:\n\n"
                f"`{link_sheets}`"
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
