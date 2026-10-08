from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import whisper
import asyncio
import sounddevice as sd
import numpy as np
import threading
import google.generativeai as genai
import edge_tts
import pygame
from pydub import AudioSegment
import os

# COLE SUA CHAVE DE API DIRETAMENTE AQUI:
CHAVE_API_GEMINI = "AQ.Ab8RN6LUBvIfLLysRsgVoT-UubRVnEdWJNgrhoCaYd11YWVfUA"

genai.configure(api_key=CHAVE_API_GEMINI)

# Configuração da personalidade (Manual do Projeto)
system_instruction = (
    "Você é o C.Y.N.I.C., um assistente pessoal virtual altamente inteligente, "
    "mas levemente sarcástico, ácido e muito leal a quem está usando. "
    "Você executa as tarefas dos humanos, mas sempre faz comentários irônicos "
    "sobre a simplicidade ou redundância das solicitações deles. Responda de forma "
    "concisa e cortante em português."
)

generation_config = {"temperature": 0.7}
model_gemini = genai.GenerativeModel(
    model_name="gemini-3.8-flash",
    system_instruction=system_instruction,
    generation_config=generation_config
)

# Inicializa o mixer de áudio para reprodução de voz
pygame.mixer.init()

app = FastAPI()

print("Iniciando motores... Carregando o modelo Whisper (aguarde).")
model_whisper = whisper.load_model("small") 
print("C.Y.N.I.C.: Sistema de audição carregado!")

# --- FUNÇÃO DE SÍNTESE DE VOZ ROBÓTICA AVANÇADA ---
async def gerar_e_tocar_voz_robotica(texto):
    arquivo_temp_raw = "temp_voice.mp3"
    arquivo_temp_robot = "temp_robot.wav"
    
    # 1. Gera a voz via Edge TTS já levemente acelerada (menos pausa humana)
    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="-2%")
    await communicate.save(arquivo_temp_raw)
    
    # 2. Carrega o áudio no Pydub
    sound = AudioSegment.from_file(arquivo_temp_raw)
    
    # Passo A: Pitch Shift (Deixa a voz um pouco mais "fria" e digital)
    sample_rate = int(sound.frame_rate * 0.85)
    sound_shifted = sound._spawn(sound.raw_data, overrides={'frame_rate': sample_rate})
    sound_shifted = sound_shifted.set_frame_rate(44100)
    
    # Passo B: Efeito Metálico / Comb Filter (O verdadeiro som de robô)
    atraso = AudioSegment.silent(duration=15) + sound_shifted
    atraso = atraso.apply_gain(-2) 
    
    # Sobrepõe o áudio original com o atraso metálico
    sound_robot = sound_shifted.overlay(atraso)
    
    # Salva o áudio final processado
    sound_robot.export(arquivo_temp_robot, format="wav")
    
    # 3. Reproduz o áudio nos alto-falantes
    pygame.mixer.music.load(arquivo_temp_robot)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
        
    pygame.mixer.music.unload()
    
    # Limpa os arquivos temporários do PC
    if os.path.exists(arquivo_temp_raw):
        os.remove(arquivo_temp_raw)
    if os.path.exists(arquivo_temp_robot):
        os.remove(arquivo_temp_robot)

html = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>C.Y.N.I.C. Interface</title>
    <style>
        body {
            background-color: #050505;
            color: #00ffcc;
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
        .core {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: radial-gradient(circle, #00ffcc 10%, transparent 70%);
            box-shadow: 0 0 20px #00ffcc, 0 0 60px #00ffcc;
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }
        .core.active {
            animation: pulse 1s infinite alternate;
            background: radial-gradient(circle, #ff0055 10%, transparent 70%); 
            box-shadow: 0 0 30px #ff0055, 0 0 80px #ff0055;
        }
        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.7; }
            100% { transform: scale(1.2); opacity: 1; }
        }
        .status-text {
            font-size: 1.3em;
            text-shadow: 0 0 5px #00ffcc, 0 0 15px #00ffcc;
            letter-spacing: 2px;
            max-width: 90%;
        }
    </style>
</head>
<body>
    <div class="core" id="core-ia"></div>
    <div class="status-text" id="status">ESCUTANDO TUDO O QUE VOCÊ DIZ...</div>

    <script>
        var ws = new WebSocket("ws://localhost:8000/ws");
        var statusDiv = document.getElementById('status');
        var coreDiv = document.getElementById('core-ia');
        
        ws.onmessage = function(event) {
            var data = JSON.parse(event.data);
            statusDiv.innerHTML = data.mensagem;
            
            if(data.estado === "ouvindo" || data.estado === "processando" || data.estado === "respondendo") {
                coreDiv.classList.add("active");
            } else {
                coreDiv.classList.remove("active");
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
    try:
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({"estado": "pronto", "mensagem": "ONLINE. Estou ouvindo cada palavra sua (infelizmente)."}),
            loop
        )
    except Exception:
        return
    
    fs = 16000  
    duracao = 5 
    
    while True:
        try:
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"estado": "ouvindo", "mensagem": "MONITORANDO..."}),
                    loop
                )
            except Exception:
                break
            
            gravacao = sd.rec(int(duracao * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait() 
            
            if gravacao is None or len(gravacao) == 0:
                continue

            volume = np.abs(gravacao).mean()
            if volume < 5:
                continue
                
            gravacao_float32 = gravacao.flatten().astype(np.float32) / 32768.0
            
            if len(gravacao_float32) == 0:
                continue

            # Prompt Inicial para calibrar o ouvido do C.Y.N.I.C.
            result = model_whisper.transcribe(
                gravacao_float32, 
                language="pt", 
                fp16=False,
                initial_prompt="C.Y.N.I.C., Cybernetic Yielding Network & Intelligent Core, Jarvis, Grok, GLaDOS, assistente, sistema."
            )
            
            texto_reconhecido = result.get("text", "").strip()
            
            if not texto_reconhecido or len(texto_reconhecido) <= 2:
                continue
                
            print(f"Capturado: {texto_reconhecido}")
            
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"estado": "processando", "mensagem": "PROCESSANDO SEUS RUÍDOS..."}),
                    loop
                )
            except Exception:
                pass
            
            # Chama o Cérebro (Gemini)
            try:
                resposta_ia = model_gemini.generate_content(texto_reconhecido)
                texto_resposta = resposta_ia.text.strip()
            except Exception as gemini_err:
                print(f"ERRO NA API DO GEMINI: {gemini_err}")
                texto_resposta = f"Erro na conexão com o meu cérebro brilhante: {gemini_err}"
            
            print(f"C.Y.N.I.C.: {texto_resposta}")
            
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"estado": "respondendo", "mensagem": f"C.Y.N.I.C.: {texto_resposta}"}),
                    loop
                )
            except Exception:
                pass
            
            # FALA A RESPOSTA EM VOZ ALTA (COM O EFEITO METÁLICO)
            try:
                asyncio.run_coroutine_threadsafe(
                    gerar_e_tocar_voz_robotica(texto_resposta),
                    loop
                ).result()
            except Exception as voice_err:
                print(f"Erro na geração de voz: {voice_err}")

            import time
            time.sleep(1) 
            
        except Exception as e:
            print(f"Aviso no ciclo de áudio: {e}")
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