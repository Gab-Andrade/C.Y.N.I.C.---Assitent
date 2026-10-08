from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import sounddevice as sd
import numpy as np
import threading
import edge_tts
import pygame
from pydub import AudioSegment
import os
import io
import queue
import concurrent.futures
from faster_whisper import WhisperModel

# Importa a função de IA modularizada do arquivo cerebro.py
from cerebro import consultar_ia, IA_ATIVA

pygame.mixer.init()
app = FastAPI()

# Monta a pasta estática para servir o HTML, CSS e JS separadamente
app.mount("/static", StaticFiles(directory="static"), name="static")

print("Iniciando motores... Carregando o FASTER-Whisper.")
model_whisper = WhisperModel("small", device="cpu", compute_type="int8")
print("C.Y.N.I.C.: Audição turbo carregada!")

# Filas e workers de áudio (mantendo o desempenho sem travar)
fila_texto = queue.Queue()
fila_audio = queue.Queue()

async def _tts_bytes(texto):
    com = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="-2%")
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

def worker_tts():
    while True:
        frase = fila_texto.get()
        try:
            mp3 = asyncio.run(_tts_bytes(frase))
            fila_audio.put(_aplicar_efeito(mp3))
        except Exception as e:
            print(f"Erro TTS: {e}")

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

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

def motor_de_audicao(loop, websocket):
    asyncio.run_coroutine_threadsafe(
        websocket.send_json({"estado": "pronto", "mensagem": f"ONLINE. Cérebro ativo: {IA_ATIVA}"}), loop)
    
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
                    data, _ = stream.read(1600)
                    volume = np.abs(data).mean()
                    
                    if volume > 12:
                        has_spoken = True
                        silence_chunks = 0
                        frames.append(data)
                    elif has_spoken:
                        frames.append(data)
                        silence_chunks += 1
                    
                    if has_spoken and silence_chunks >= 7:
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
            
            # --- CHAMA O MÓDULO CEREBRO.PY ---
            texto_resposta = consultar_ia(texto_reconhecido)
            
            print(f"C.Y.N.I.C.: {texto_resposta}")
            
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"estado": "respondendo", "mensagem": f"C.Y.N.I.C.: {texto_resposta}"}), loop)
            
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