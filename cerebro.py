import os
import re
import google.generativeai as genai
from groq import Groq
 
# =================================================================
# INTERRUPTOR: ESCOLHA QUAL CÉREBRO O C.Y.N.I.C. VAI USAR
# Digite "GROQ" ou "GEMINI"
IA_ATIVA = "GROQ"
# =================================================================
 
# As chaves vêm de variáveis de ambiente (nunca cole chaves no código):
#   Windows (uma vez, depois abra um terminal novo):  setx GROQ_API_KEY "sua_chave"
#   Linux/Mac:                                        export GROQ_API_KEY="sua_chave"
CHAVE_API_GROQ = os.environ.get("GROQ_API_KEY", "")
CHAVE_API_GEMINI = os.environ.get("GEMINI_API_KEY", "")
 
MODELO_GROQ = "openai/gpt-oss-120b"   # para ainda mais velocidade: "openai/gpt-oss-20b"
MODELO_GEMINI = "gemini-1.5-flash"    # confira se esse nome ainda existe antes de usar o GEMINI
 
system_instruction = (
    "Você é o C.Y.N.I.C., um assistente pessoal virtual altamente inteligente, "
    "mas levemente sarcástico, ácido e muito leal a quem está usando. "
    "Você executa as tarefas dos humanos, mas sempre faz comentários irônicos "
    "sobre a simplicidade ou redundância das solicitações deles. Responda de forma "
    "concisa e cortante em português. "
    "Suas respostas são faladas em voz alta: use no máximo 3 frases curtas, "
    "sem markdown, listas, emojis ou símbolos."
)
 
# Inicializa Gemini (só se houver chave)
model_gemini = None
if CHAVE_API_GEMINI:
    genai.configure(api_key=CHAVE_API_GEMINI)
    model_gemini = genai.GenerativeModel(
        model_name=MODELO_GEMINI,
        system_instruction=system_instruction
    )
 
# Inicializa Groq (timeout evita ficar travado se a rede cair)
client_groq = Groq(api_key=CHAVE_API_GROQ, timeout=20.0) if CHAVE_API_GROQ else None
 
 
# ---------------------------------------------------------------
# Utilitários: dividir o texto em frases e limpar para a voz
# ---------------------------------------------------------------
_FIM_FRASE = re.compile(r'(.+?[.!?…])\s+', re.S)
_MIN_CHARS = 15   # frases muito curtas ("Ok.") são coladas na seguinte
 
 
def _limpar_para_fala(texto):
    texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)   # links markdown
    return re.sub(r'[*#`_~>|]', '', texto).strip()
 
 
def _dividir_em_frases(partes):
    """Recebe pedaços de texto (stream) e entrega uma frase completa por vez."""
    buf, acc = "", ""
    for pedaco in partes:
        buf += pedaco
        while True:
            m = _FIM_FRASE.match(buf)
            if not m:
                break
            buf = buf[m.end():]
            acc = (acc + " " + m.group(1)).strip()
            if len(acc) >= _MIN_CHARS:
                frase = _limpar_para_fala(acc)
                acc = ""
                if frase:
                    yield frase
    resto = _limpar_para_fala((acc + " " + buf).strip())
    if resto:
        yield resto
 
 
def _partes_groq(texto_usuario):
    stream = client_groq.chat.completions.create(
        model=MODELO_GROQ,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": texto_usuario}
        ],
        temperature=0.7,
        stream=True,
        # reasoning_effort baixo = bem menos tempo "pensando" antes da 1ª palavra.
        # Vai em extra_body para funcionar mesmo em versões antigas do SDK.
        extra_body={"reasoning_effort": "low", "max_completion_tokens": 400},
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
 
 
def _partes_gemini(texto_usuario):
    for chunk in model_gemini.generate_content(texto_usuario, stream=True):
        try:
            if chunk.text:
                yield chunk.text
        except ValueError:
            continue   # chunk sem texto (ex.: bloqueio de segurança)
 
 
# ---------------------------------------------------------------
# API pública
# ---------------------------------------------------------------
def consultar_ia_stream(texto_usuario):
    """Gera a resposta frase por frase, para o C.Y.N.I.C. começar a falar antes do fim."""
    try:
        if IA_ATIVA == "GROQ":
            if client_groq is None:
                raise RuntimeError("variável de ambiente GROQ_API_KEY não definida")
            partes = _partes_groq(texto_usuario)
        elif IA_ATIVA == "GEMINI":
            if model_gemini is None:
                raise RuntimeError("variável de ambiente GEMINI_API_KEY não definida")
            partes = _partes_gemini(texto_usuario)
        else:
            raise RuntimeError(f"IA_ATIVA inválida: {IA_ATIVA}")
        yield from _dividir_em_frases(partes)
    except Exception as erro:
        print(f"ERRO NA API ({IA_ATIVA}): {erro}")
        yield f"Falha de conexão com o meu cérebro via {IA_ATIVA}."
 
 
def consultar_ia(texto_usuario):
    """Versão sem streaming (compatibilidade): devolve a resposta inteira."""
    return " ".join(consultar_ia_stream(texto_usuario))
 