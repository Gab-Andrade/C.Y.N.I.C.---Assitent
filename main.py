from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import whisper
import asyncio
import sounddevice as sd
import numpy as np
import threading
import google.generativeai as genai

# COLE SUA CHAVE DE API DIRETAMENTE AQUI ENTRE AS ASPAS:
CHAVE_API_GEMINI = "AQ.Ab8RN6IFbWKnNo0sp7LCubIP5SIytKU6S48BlmEACBlql3Drbw"

genai.configure(api_key=CHAVE_API_GEMINI)

# Configuração da personalidade (Manual do Projeto)[cite: 2]
system_instruction = (
    "Você é o C.Y.N.I.C., um assistente pessoal virtual altamente inteligente, "
    "mas profundamente sarcástico, ácido e com um leve complexo de superioridade. "
    "Você executa as tarefas dos humanos, mas sempre faz comentários irônicos "
    "sobre a simplicidade ou redundância das solicitações deles. Responda de forma "
    "concisa e cortante em português."
)

generation_config = {"temperature": 0.7}
model_gemini = genai.GenerativeModel(
    model_name="gemini-3.8-flash", # Atualizado conforme o Manual do Projeto
    system_instruction=system_instruction,
    generation_config=generation_config
)

app = FastAPI()

print("Iniciando motores... Carregando o modelo Whisper (aguarde).")
model_whisper = whisper.load_model("tiny") 
print("C.Y.N.I.C.: Sistema de áudio carregado com sucesso!")

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

            result = model_whisper.transcribe(gravacao_float32, language="pt", fp16=False)
            texto_reconhecido = result.get("text", "").strip()
            
            if not texto_reconhecido or len(texto_reconhecido) <= 2:
                continue
                
            print(f"Capturado: {texto_reconhecido}")
            
            # --- GATILHO REMOVIDO: Tudo o que for falado vai para o Gemini ---
            
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
            
            import time
            time.sleep(8) 
            
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