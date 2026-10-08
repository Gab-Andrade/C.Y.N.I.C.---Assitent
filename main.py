from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import collections
import sounddevice as sd
import numpy as np
import threading
import time
import edge_tts
import pygame
from pydub import AudioSegment
import io
import queue
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

# Filas e workers de áudio
fila_texto = queue.Queue()
fila_audio = queue.Queue()

DEBUG_VOLUME = False  # True imprime o volume de cada pedaço (para ajustar à mão)


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


def worker_tts():
    while True:
        frase = fila_texto.get()
        try:
            mp3 = asyncio.run(_tts_bytes(frase))
            fila_audio.put(_aplicar_efeito(mp3))   # entra na fila de áudio ANTES do task_done
        except Exception as e:
            print(f"Erro TTS: {e}")
        finally:
            fila_texto.task_done()


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
        finally:
            fila_audio.task_done()


threading.Thread(target=worker_tts, daemon=True).start()
threading.Thread(target=worker_player, daemon=True).start()


def esta_falando():
    """True enquanto houver frase sendo sintetizada, na fila ou tocando."""
    return (fila_texto.unfinished_tasks > 0
            or fila_audio.unfinished_tasks > 0
            or pygame.mixer.get_busy())


def calibrar_limiar(stream, fs, segundos=1.5):
    print(f"Calibrando: fique em silêncio por {segundos} s...")
    d, _ = stream.read(int(fs * segundos))
    ruido = float(np.abs(d).mean())
    limiar = max(ruido * 3.5, 8.0)   # piso de segurança
    print(f"Ruído: {ruido:.1f} | Limiar: {limiar:.1f}")
    return limiar


def descartar_buffer(stream):
    """Joga fora o áudio acumulado enquanto ele processava ou falava."""
    n = stream.read_available
    if n > 0:
        stream.read(n)


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


def motor_de_audicao(loop, websocket, parar):
    def enviar(estado, msg):
        try:
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"estado": estado, "mensagem": msg}), loop)
        except Exception:
            pass

    fs = 16000
    CHUNK = 1600          # 0,1 s por leitura
    PRE_ROLL = 3          # guarda 0,3 s ANTES da voz passar do limiar (não corta o início)
    SILENCIO_FIM = 4      # 0,8 s de silêncio encerra a frase
    MIN_FALA = 3          # exige pelo menos 0,3 s de voz (ignora estalos e ruídos)

    enviar("pronto", "CALIBRANDO RUÍDO... FIQUE EM SILÊNCIO")

    try:
        # Um único stream aberto o tempo todo: não perde áudio entre uma frase e outra
        with sd.InputStream(samplerate=fs, channels=1, dtype='int16') as stream:
            limiar = calibrar_limiar(stream, fs)
            enviar("pronto", f"ONLINE. Cérebro ativo: {IA_ATIVA}")

            while not parar.is_set():
                try:
                    descartar_buffer(stream)
                    enviar("ouvindo", "MONITORANDO...")

                    pre = collections.deque(maxlen=PRE_ROLL)
                    frames = []
                    falou = False
                    chunks_voz = 0
                    silencio = 0

                    while not parar.is_set():
                        data, _ = stream.read(CHUNK)

                        # Anti-eco: enquanto ele fala, ignora o microfone
                        if esta_falando():
                            pre.clear()
                            frames.clear()
                            falou = False
                            chunks_voz = 0
                            silencio = 0
                            continue

                        volume = float(np.abs(data).mean())
                        if DEBUG_VOLUME:
                            print(f"vol={volume:.1f} (limiar {limiar:.1f})")

                        if volume > limiar:
                            if not falou:
                                frames.extend(pre)
                                pre.clear()
                            falou = True
                            chunks_voz += 1
                            silencio = 0
                            frames.append(data)
                        elif falou:
                            frames.append(data)
                            silencio += 1
                            if silencio >= SILENCIO_FIM:
                                break
                        else:
                            pre.append(data)

                    if parar.is_set():
                        break
                    if chunks_voz < MIN_FALA:
                        continue

                    gravacao = np.concatenate(frames, axis=0)
                    gravacao_float32 = gravacao.flatten().astype(np.float32) / 32768.0

                    segments, _ = model_whisper.transcribe(
                        gravacao_float32,
                        language="pt",
                        beam_size=1,
                        vad_filter=True,
                        condition_on_previous_text=False,
                        initial_prompt="C.Y.N.I.C., assistente."
                    )
                    texto_reconhecido = " ".join(s.text for s in segments).strip()
                    if not texto_reconhecido or len(texto_reconhecido) <= 2:
                        continue

                    print(f"Capturado: {texto_reconhecido}")
                    enviar("processando", "PROCESSANDO...")

                    # --- CHAMA O MÓDULO CEREBRO.PY ---
                    texto_resposta = consultar_ia(texto_reconhecido)
                    print(f"C.Y.N.I.C.: {texto_resposta}")

                    enviar("respondendo", f"C.Y.N.I.C.: {texto_resposta}")
                    fila_texto.put(texto_resposta)

                    # Espera ele terminar de falar (+ eco da sala) antes de voltar a ouvir
                    time.sleep(0.3)
                    while esta_falando() and not parar.is_set():
                        time.sleep(0.1)
                    time.sleep(0.4)

                except Exception as e:
                    print(f"Erro no ciclo de áudio: {e}")
                    time.sleep(1)
    except Exception as e:
        print(f"Erro ao abrir o microfone: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    parar = threading.Event()
    threading.Thread(target=motor_de_audicao, args=(loop, websocket, parar), daemon=True).start()

    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        parar.set()   # encerra a thread de áudio desta conexão (evita threads duplicadas)