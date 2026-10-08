from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import asyncio
import sounddevice as sd
import numpy as np
import threading
import google.generativeai as genai
import edge_tts
import pygame
from pydub import AudioSegment
import os
import io
import re
import queue
from faster_whisper import WhisperModel

# COLE SUA CHAVE DE API DIRETAMENTE AQUI:
CHAVE_API_GEMINI = "AQ.Ab8RN6KB4fYW-ohdrZUjJKZ8cH2RUvf5c49Gv0pVRwkh89Z5vQ"

genai.configure(api_key=CHAVE_API_GEMINI)

# Configuração da personalidade
system_instruction = (
    "Você é o C.Y.N.I.C., um assistente virtual altamente inteligente, "
    "levemente sarcástico, ácido e leal. "
    "Execute as tarefas, mas faça comentários irônicos sobre a simplicidade delas. "
    "Responda de forma concisa e cortante em português."
)

generation_config = {"temperature": 0.7}
model_gemini = genai.GenerativeModel(
    model_name="gemini-3.8-flash",
    system_instruction=system_instruction,
    generation_config=generation_config
)

pygame.mixer.init()
app = FastAPI()

print("Iniciando motores... Carregando o FASTER-Whisper.")
model_whisper = WhisperModel("small", device="cpu", compute_type="int8")
print("C.Y.N.I.C.: Audicao turbo carregada!")

# --- SISTEMA DE FILAS PARA NÃO TRAVAR O SERVIDOR ---
fila_texto = queue.Queue()
fila_audio = queue.Queue()

async def _tts_bytes(texto):
    com = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="+2%")
    buf = bytearray()
    async for chunk in com.stream():
        if chunk["type"] == "audio":
            buf += chunk["data"]
    return bytes(buf)

def _aplicar_efeito(mp3_bytes):
    sound = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    shifted = sound._spawn(sound.raw_data, overrides={'frame_rate': int(sound.frame_rate * 0.85)})
    shifted = shifted.set_frame_rate(44100)
    atraso = (AudioSegment.silent(duration=20) + shifted).apply_gain(-2)
    robot = shifted.overlay(atraso)
    out = io.BytesIO()
    robot.export(out, format="wav")
    out.seek(0)
    return out

# Trabalhador 1: Transforma texto em Voz sem travar nada
def worker_tts():
    while True:
        frase = fila_texto.get()
        try:
            mp3 = asyncio.run(_tts_bytes(frase))
            fila_audio.put(_aplicar_efeito(mp3))
        except Exception as e:
            print(f"Erro TTS: {e}")

# Trabalhador 2: Toca a Voz sem travar nada
def worker_player():
    while True:
        wav = fila_audio.get()
        try:
            som = pygame.mixer.Sound(file=wav)
            canal = som.play()
            while canal.get_busy():
                pygame.time.wait(20)
        except Exception as e:
            print(f"Erro player: {e}")

threading.Thread(target=worker_tts, daemon=True).start()
threading.Thread(target=worker_player, daemon=True).start()

# --- FRONTEND (CÉREBRO VERDE) ---
html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>C.Y.N.I.C. Interface</title>
    <style>
        body {
            background-color: #000000;
            color: #00ff66;
            font-family: 'Courier New', Courier, monospace;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            overflow: hidden;
            text-align: center;
            padding: 20px;
        }
        
        .core-container {
            position: relative;
            width: 260px;
            height: 260px;
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 40px;
        }

        .ring {
            position: absolute;
            width: 100%;
            height: 100%;
            border: 2px dashed rgba(0, 255, 102, 0.25);
            border-radius: 50%;
            animation: spin 20s linear infinite;
        }

        .ring-inner {
            position: absolute;
            width: 75%;
            height: 75%;
            border: 1px solid rgba(0, 255, 102, 0.4);
            border-radius: 50%;
            animation: spin-reverse 12s linear infinite;
        }

        .brain-core {
            width: 140px;
            height: 140px;
            stroke: #00ff66;
            fill: none;
            stroke-width: 1.2;
            stroke-linecap: round;
            stroke-linejoin: round;
            filter: drop-shadow(0 0 12px rgba(0, 255, 102, 0.7));
            transition: all 0.3s ease;
        }

        .core-container.active .brain-core {
            stroke: #00ff33;
            filter: drop-shadow(0 0 25px rgba(0, 255, 51, 1));
            animation: pulse-brain 0.7s infinite alternate;
        }

        .core-container.active .ring {
            border-color: rgba(0, 255, 102, 0.7);
            animation: spin 5s linear infinite;
        }

        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes spin-reverse { 0% { transform: rotate(360deg); } 100% { transform: rotate(0deg); } }
        @keyframes pulse-brain { 0% { transform: scale(0.96); opacity: 0.85; } 100% { transform: scale(1.08); opacity: 1; } }

        .status-text {
            font-size: 1.2em;
            text-shadow: 0 0 8px #00ff66;
            letter-spacing: 3px;
            max-width: 90%;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
    <div class="core-container" id="core-container">
        <div class="ring"></div>
        <div class="ring-inner"></div>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="brain-core">
            <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
            <path d="M9 13a4.5 4.5 0 0 0 3-4"/>
            <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/>
            <path d="M3.477 10.896a4 4 0 0 1 .585-.396"/>
            <path d="M6 18a4 4 0 0 1-1.967-.516"/>
            <path d="M12 13h4"/>
            <path d="M12 18h6a2 2 0 0 1 2 2v1"/>
            <path d="M12 8h8"/>
            <path d="M16 8V5a2 2 0 0 1 2-2"/>
            <circle cx="16" cy="13" r=".8" fill="#00ff66"/>
            <circle cx="18" cy="3" r=".8" fill="#00ff66"/>
            <circle cx="20" cy="21" r=".8" fill="#00ff66"/>
            <circle cx="20" cy="8" r=".8" fill="#00ff66"/>
        </svg>
    </div>
    
    <div class="status-text" id="status">ESCUTANDO TUDO O QUE VOCÊ DIZ...</div>

    <script>
        var ws = new WebSocket("ws://localhost:8000/ws");
        var statusDiv = document.getElementById('status');
        var containerDiv = document.getElementById('core-container');
        
        ws.onmessage = function(event) {
            var data = JSON.parse(event.data);
            statusDiv.innerHTML = data.mensagem;
            
            if(data.estado === "ouvindo" || data.estado === "processando" || data.estado === "respondendo") {
                containerDiv.classList.add("active");
            } else {
                containerDiv.classList.remove("active");
            }
        };
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

def motor_de_audicao(loop, websocket):
    asyncio.run_coroutine_threadsafe(
        websocket.send_json({"estado": "pronto", "mensagem": "ONLINE. Estou ouvindo."}), loop)
    
    fs = 16000  
    
    while True:
        try:
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"estado": "ouvindo", "mensagem": "MONITORANDO..."}), loop)
            
            frames = []
            has_spoken = False
            silence_chunks = 0
            
            with sd.InputStream(samplerate=fs, channels=1, dtype='int16') as stream:
                while True:
                    data, _ = stream.read(1600) # 0.1s
                    volume = np.abs(data).mean()
                    
                    if volume > 12:
                        has_spoken = True
                        silence_chunks = 0
                        frames.append(data)
                    elif has_spoken:
                        frames.append(data)
                        silence_chunks += 1
                    
                    if has_spoken and silence_chunks >= 7: # Corta com 0.7s de silencio
                        break
            
            if not frames:
                continue

            gravacao = np.concatenate(frames, axis=0)
            gravacao_float32 = gravacao.flatten().astype(np.float32) / 32768.0

            segments, _ = model_whisper.transcribe(
                gravacao_float32, 
                language="pt", 
                beam_size=1,
                initial_prompt="C.Y.N.I.C., assistente."
            )
            
            texto_reconhecido = " ".join(s.text for s in segments).strip()
            if not texto_reconhecido or len(texto_reconhecido) <= 2:
                continue
                
            print(f"Capturado: {texto_reconhecido}")
            
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"estado": "processando", "mensagem": "PROCESSANDO..."}), loop)
            
            resposta_ia = model_gemini.generate_content(texto_reconhecido)
            texto_resposta = resposta_ia.text.strip()
            
            print(f"C.Y.N.I.C.: {texto_resposta}")
            
            # Envia pro navegador (AWAITED corretamente)
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"estado": "respondendo", "mensagem": f"C.Y.N.I.C.: {texto_resposta}"}), loop)
            
            # Envia pra Fila de Voz (não trava nada)
            fila_texto.put(texto_resposta)
            
            import time
            time.sleep(1) 
            
        except Exception as e:
            print(f"Erro no ciclo de áudio: {e}")
            import time
            time.sleep(1)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    threading.Thread(target=motor_de_audicao, args=(loop, websocket), daemon=True).start()
    
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass