import os
import re
import uuid
import chromadb
import google.generativeai as genai
from groq import Groq

# =================================================================
# INTERRUPTOR: ESCOLHA QUAL CÉREBRO O C.Y.N.I.C. VAI USAR
# =================================================================
IA_ATIVA = "GROQ"

CHAVE_API_GROQ = os.environ.get("GROQ_API_KEY", "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")
CHAVE_API_GEMINI = os.environ.get("GEMINI_API_KEY", "")

MODELO_GROQ = "openai/gpt-oss-120b"  # Modelo rápido e estável no plano gratuito
MODELO_GEMINI = "gemini-1.5-flash"

system_instruction = (
    "Você é o C.Y.N.I.C., um assistente pessoal virtual altamente inteligente, "
    "mas levemente sarcástico, ácido e muito leal a quem está usando. "
    "Você executa as tarefas dos humanos, mas sempre faz comentários irônicos "
    "sobre a simplicidade ou redundância das solicitações deles. Responda de forma "
    "concisa e cortante em português. "
    "Suas respostas são faladas em voz alta: use no máximo 3 frases curtas, "
    "sem markdown, listas, emojis ou símbolos."
)

# =================================================================
# MEMÓRIA DE LONGO PRAZO (CHROMADB)
# =================================================================
print("Iniciando lóbulo frontal (Memória ChromaDB)...")
# Cria uma pasta local para persistir as memórias no seu PC
chroma_client = chromadb.PersistentClient(path="./memoria_cynic")
memoria = chroma_client.get_or_create_collection(name="historico_cynic")

def buscar_contexto(texto):
    """Busca as 2 conversas passadas mais relevantes em relação ao texto atual."""
    # O try/except evita falhas caso o banco esteja vazio na primeira vez
    try:
        resultados = memoria.query(query_texts=[texto], n_results=2)
        documentos = resultados.get('documents', [[]])[0]
        if not documentos:
            return ""
        # Informa à IA que isso é uma lembrança para ela usar de contexto
        return " [LEMBRANÇAS DO PASSADO: " + " | ".join(documentos) + "] "
    except Exception:
        return ""

def salvar_memoria(texto_usuario, texto_resposta):
    """Salva a interação atual no banco de dados vetorial para o futuro."""
    id_unico = str(uuid.uuid4())
    documento = f"Humano disse: '{texto_usuario}'. C.Y.N.I.C respondeu: '{texto_resposta}'."
    memoria.add(documents=[documento], ids=[id_unico])


# =================================================================
# INICIALIZAÇÃO DAS IAS
# =================================================================
model_gemini = None
if CHAVE_API_GEMINI:
    genai.configure(api_key=CHAVE_API_GEMINI)
    model_gemini = genai.GenerativeModel(
        model_name=MODELO_GEMINI,
        system_instruction=system_instruction
    )

client_groq = Groq(api_key=CHAVE_API_GROQ, timeout=20.0) if CHAVE_API_GROQ else None

# ---------------------------------------------------------------
# Utilitários: dividir o texto em frases e limpar para a voz
# ---------------------------------------------------------------
_FIM_FRASE = re.compile(r'(.+?[.!?…])\s+', re.S)
_MIN_CHARS = 15

def _limpar_para_fala(texto):
    texto = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', texto)
    return re.sub(r'[*#`_~>|]', '', texto).strip()

def _dividir_em_frases(partes):
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

def _partes_groq(texto_enriquecido):
    stream = client_groq.chat.completions.create(
        model=MODELO_GROQ,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": texto_enriquecido}
        ],
        temperature=0.7,
        stream=True,
        extra_body={"reasoning_effort": "low", "max_completion_tokens": 400},
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def _partes_gemini(texto_enriquecido):
    for chunk in model_gemini.generate_content(texto_enriquecido, stream=True):
        try:
            if chunk.text:
                yield chunk.text
        except ValueError:
            continue

def consultar_ia_stream(texto_enriquecido):
    """Gera a resposta frase por frase com base no prompt enriquecido com a memória."""
    try:
        if IA_ATIVA == "GROQ":
            if client_groq is None:
                raise RuntimeError("variável de ambiente GROQ_API_KEY não definida")
            partes = _partes_groq(texto_enriquecido)
        elif IA_ATIVA == "GEMINI":
            if model_gemini is None:
                raise RuntimeError("variável de ambiente GEMINI_API_KEY não definida")
            partes = _partes_gemini(texto_enriquecido)
        else:
            raise RuntimeError(f"IA_ATIVA inválida: {IA_ATIVA}")
        yield from _dividir_em_frases(partes)
    except Exception as erro:
        print(f"ERRO NA API ({IA_ATIVA}): {erro}")
        yield f"Falha de conexão com o meu cérebro via {IA_ATIVA}."

def consultar_ia(texto_usuario):
    """Orquestrador Central: Busca memória, pergunta à IA e salva a nova lembrança."""
    # 1. Puxa lembranças relacionadas (se existirem)
    contexto = buscar_contexto(texto_usuario)
    
    # 2. Une a lembrança com o que você acabou de falar
    prompt_enriquecido = contexto + "MENSAGEM ATUAL DO HUMANO: " + texto_usuario
    
    # 3. Consulta a Groq/Gemini com esse pacotão de contexto
    resposta_completa = " ".join(consultar_ia_stream(prompt_enriquecido))
    
    # 4. Salva o que aconteceu no ChromaDB para o C.Y.N.I.C. lembrar amanhã
    if resposta_completa and "Falha de conexão" not in resposta_completa:
        salvar_memoria(texto_usuario, resposta_completa)
        
    return resposta_completa