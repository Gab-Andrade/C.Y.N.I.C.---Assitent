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

# COLE SUA CHAVE DE API NOVA AQUI:
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

# --- FUNÇÃO DE SÍNTESE DE VOZ ROBÓTICA GRAVE E LENTA ---
async def gerar_e_tocar_voz_robotica(texto):
    arquivo_temp_raw = "temp_voice.mp3"
    arquivo_temp_robot = "temp_robot.wav"
    
    # 1. Gera a voz via Edge TTS mais cadenciada (-10%)
    communicate = edge_tts.Communicate(texto, "pt-BR-AntonioNeural", rate="2%")
    await communicate.save(arquivo_temp_raw)
    
    # 2. Carrega o áudio no Pydub
    sound = AudioSegment.from_file(arquivo_temp_raw)
    
    # Passo A: Pitch Shift mais grave (0.85 engrossa o timbre)
    sample_rate = int(sound.frame_rate * 0.85)
    sound_shifted = sound._spawn(sound.raw_data, overrides={'frame_rate': sample_rate})
    sound_shifted = sound_shifted.set_frame_rate(44100)
    
    # Passo B: Efeito Metálico / Comb Filter
    atraso = AudioSegment.silent(duration=20) + sound_shifted
    atraso = atraso.apply_gain(-2) 
    
    sound_robot = sound_shifted.overlay(atraso)
    sound_robot.export(arquivo_temp_robot, format="wav")
    
    # 3. Reproduz o áudio nos alto-falantes
    pygame.mixer.music.load(arquivo_temp_robot)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)
        
    pygame.mixer.music.unload()
    
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

        /* Anel tecnológico externo verde */
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

        /* O Ícone Exato do Cérebro/Circuito Central */
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

        /* Estado ativo (pulsação verde mais intensa quando ativo) */
        .core-container.active .brain-core {
            stroke: #00ff33;
            filter: drop-shadow(0 0 25px rgba(0, 255, 51, 1));
            animation: pulse-brain 0.7s infinite alternate;
        }

        .core-container.active .ring {
            border-color: rgba(0, 255, 102, 0.7);
            animation: spin 5s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes spin-reverse {
            0% { transform: rotate(360deg); }
            100% { transform: rotate(0deg); }
        }

        @keyframes pulse-brain {
            0% { transform: scale(0.96); opacity: 0.85; }
            100% { transform: scale(1.08); opacity: 1; }
        }

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
        <!-- Seu ícone exato injetado perfeitamente no centro -->
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
    
    <div class="status-text" id="status">AGUARDANDO A PALAVRA-CHAVE ("CÍNICO")...</div>

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
    try:
        asyncio.run_coroutine_threadsafe(
            websocket.send_json({"estado": "pronto", "mensagem": "ONLINE. Diga 'Cínico' ou 'Cynic' para falar comigo."}),
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
                    websocket.send_json({"estado": "ouvindo", "mensagem": "MONITORANDO EM ESPERA..."}),
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

            # Transcreve o áudio capturado
            result = model_whisper.transcribe(
                gravacao_float32, 
                language="pt", 
                fp16=False,
                initial_prompt="C.Y.N.I.C., cínico, cynic, assistente, sistema."
            )
            
            texto_reconhecido = result.get("text", "").strip()
            
            if not texto_reconhecido or len(texto_reconhecido) <= 2:
                continue
                
            print(f"Ouvido: {texto_reconhecido}")
            
            # --- FILTRA PELA PALAVRA DE ATIVAÇÃO ---
            texto_minusculo = texto_reconhecido.lower()
            if "cínico" not in texto_minusculo and "cynic" not in texto_minusculo and "cínica" not in texto_minusculo:
                # Se não falou a palavra-chave, ignora e volta a escutar sem gastar API
                continue

            print(f"Palavra de ativação detectada! Acionando cérebro...")
            
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"estado": "processando", "mensagem": "PROCESSANDO SUA ORDEM..."}),
                    loop
                )
            except Exception:
                pass
            
            # Chama o Cérebro (Gemini) apenas quando chamado
            try:
                resposta_ia = model_gemini.generate_content(texto_reconhecido)
                texto_resposta = resposta_ia.text.strip()
            except Exception as gemini_err:
                print(f"ERRO NA API DO GEMINI: {gemini_err}")
                texto_resposta = f"Erro na conexão com o meu cérebro: {gemini_err}"
            
            print(f"C.Y.N.I.C.: {texto_resposta}")
            
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"estado": "respondendo", "mensagem": f"C.Y.N.I.C.: {texto_resposta}"}),
                    loop
                )
            except Exception:
                pass
            
            # FALA A RESPOSTA COM O TIMBRE GRAVE E ROBÓTICO
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