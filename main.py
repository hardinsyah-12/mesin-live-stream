import subprocess
import os
import time
import re
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from multiprocessing import Process

app = FastAPI()

# Variabel global untuk melacak ID proses
current_pid = None

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
    if "api.telegram.org" not in url_input:
        return url_input
        
    match = re.search(r'file_id=([A-Za-z0-9_-]+)', url_input) or re.search(r'/videos/([A-Za-z0-9_-]+)', url_input)
    if not match:
        return url_input
        
    file_id = match.group(1)
    print(f"[SYSTEM] Ekstrak ID Sukses: {file_id}")
    
    url_get_file = f"https://api.telegram.org/bot{TOKEN_BOT}/getFile?file_id={file_id}"
    try:
        respon = requests.get(url_get_file, timeout=10).json()
        if respon.get("ok"):
            file_path = respon["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{TOKEN_BOT}/{file_path}"
    except Exception as e:
        print(f"Gagal koneksi ke Telegram API: {str(e)}")
        
    return url_input

def proses_inti_ffmpeg(video_url: str, stream_key: str, duration_hours: float):
    print("=== [PROSES FFmpeg JALUR MANDIRI DIMULAI] ===")
    
    link_siap_putar = dapatkan_jalur_resmi_telegram(video_url)
    print(f"-> Target Link Video: '{link_siap_putar}'")
    
    rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{stream_key}"
    
    command = [
        "ffmpeg",
        "-headers", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n",
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
        
        print(f"🚀 Streaming Didorong ke YouTube! PID: {process.pid}")
        
        while True:
            if process.poll() is not None:
                output, _ = process.communicate()
                print(f"⚠️ LOG FFmpeg: \n{output.decode('utf-8', errors='ignore')}")
                break
            
            if (time.time() - waktu_mulai) >= batas_detik:
                print("Durasi jadwal habis! Mematikan otomatis...")
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
    print(f"Payload Mentah: video_url={request.video_url}")
    
    # Paksa matikan jika ada sisa proses lama
    if current_pid:
        try:
            os.kill(current_pid, 9)
            print("✅ Mematikan proses streaming lama di latar belakang.")
        except:
            pass
        current_pid = None
        
    # Jalankan menggunakan multiprocessing mandiri agar tidak dibekukan Render
    p = Process(target=proses_inti_ffmpeg, args=(request.video_url, request.stream_key, request.duration_hours))
    p.start()
    current_pid = p.pid # Simpan ID prosesnya
    
    return {"status": "success", "message": f"Proses mandiri berhasil dipicu dengan PID {p.pid}!"}


@app.post("/stop")
async def stop_stream():
    global current_pid
    print("=== [SINYAL STOP MASUK] ===")
    if current_pid:
        try:
            os.kill(current_pid, 9)
            print(f"✅ Berhasil mematikan paksa PID {current_pid}")
        except:
            pass
        current_pid = None
    return {"status": "success", "message": "Streaming dihentikan!"}


@app.post(f"/bot/{TOKEN_BOT}")
async def terima_pesan_telegram(update: dict):
    if "message" in update:
        pesan = update["message"]
        chat_id = pesan["chat"]["id"]
        if "video" in pesan:
            file_id = pesan["video"]["file_id"]
            link_sheets = f"https://api.telegram.org/file/bot{TOKEN_BOT}/getFile?file_id={file_id}"
            teks_balasan = f"🎉 **ID VIDEO SUKSES!**\n\nSalin link ini ke Sheets:\n`{link_sheets}`"
            requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", json={"chat_id": chat_id, "text": teks_balasan, "parse_mode": "Markdown"})
    return {"status": "ok"}

@app.on_event("startup")
def set_webhook_telegram():
    nama_app_render = os.environ.get("RENDER_EXTERNAL_URL", "https://mesin-live-stream.onrender.com")
    requests.get(f"https://api.telegram.org/bot{TOKEN_BOT}/setWebhook?url={nama_app_render}/bot/{TOKEN_BOT}")
