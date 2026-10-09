import os
import re
import threading
import uuid

import chromadb
import google.generativeai as genai
from groq import Groq

from app.config import MEMORIA_DIR
from app.skills.sistema_local import abrir_programa, tocar_musica
from app.skills.workspace_google import ler_agenda, ler_emails

# =================================================================
# INTERRUPTOR: ESCOLHA QUAL CÉREBRO O C.Y.N.I.C. VAI USAR
# =================================================================
IA_ATIVA = "GROQ"

CHAVE_API_GROQ = os.environ.get("GROQ_API_KEY", "")
CHAVE_API_GEMINI = os.environ.get("GEMINI_API_KEY", "")

MODELO_GROQ = "openai/gpt-oss-120b"
MODELO_GEMINI = "gemini-3.5-flash"

system_instruction = (
    "Você é o C.Y.N.I.C., um assistente pessoal virtual altamente inteligente, "
    "mas levemente sarcástico, ácido e muito leal a quem está usando. "
    "Você executa as tarefas dos humanos, mas sempre faz comentários irônicos "
    "sobre a simplicidade da solicitação. Responda de forma concisa em português, "
    "em no máximo 3 frases curtas, sem markdown, listas, emojis ou símbolos. "
    "Use apenas estas tags, sem inventar outras, sempre no final da resposta: "
    "para abrir um programa (bloco de notas, calculadora, vscode, navegador ou spotify) use [ABRIR: nome]; "
    "para tocar uma música use [TOCAR: nome da música e artista]. "
    "Exemplo: 'Como queira. Colocando isso para você. [TOCAR: Evidências Chitãozinho e Xororó]'"
    "Se o humano pedir para checar a agenda ou os compromissos, adicione no final da resposta a tag: [LER_AGENDA]. "
    "Se o humano pedir para checar os e-mails, adicione no final da resposta a tag: [LER_EMAILS]. "
)

# =================================================================
# MEMÓRIA DE LONGO PRAZO (CHROMADB)
# =================================================================
print("Iniciando lóbulo frontal (Memória ChromaDB)...")
chroma_client = chromadb.PersistentClient(path=str(MEMORIA_DIR))
memoria = chroma_client.get_or_create_collection(name="historico_cynic")


def buscar_contexto(texto):
    """Busca as 2 conversas passadas mais relevantes em relação ao texto atual."""
    try:
        resultados = memoria.query(query_texts=[texto], n_results=2)
        documentos = resultados.get('documents', [[]])[0]
        if not documentos:
            return ""
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


def _executar_em_segundo_plano(funcao, rotulo, argumento):
    """Roda a ação local sem atrasar a voz."""
    def tarefa():
        print(f"C.Y.N.I.C. {rotulo}: {funcao(argumento)}")
    threading.Thread(target=tarefa, daemon=True).start()


def consultar_ia(texto_usuario):
    """Orquestrador Central: busca memória, pergunta à IA, executa ações locais e salva a lembrança."""
    contexto = buscar_contexto(texto_usuario)
    prompt_enriquecido = contexto + "MENSAGEM ATUAL DO HUMANO: " + texto_usuario
    resposta_completa = " ".join(consultar_ia_stream(prompt_enriquecido))

    m = re.search(r'\[ABRIR:(.*?)\]', resposta_completa)
    if m:
        _executar_em_segundo_plano(abrir_programa, "Sistema Local", m.group(1).strip())
        resposta_completa = resposta_completa.replace(m.group(0), "").strip()

    m = re.search(r'\[TOCAR:(.*?)\]', resposta_completa)
    if m:
        _executar_em_segundo_plano(tocar_musica, "Spotify", m.group(1).strip())
        resposta_completa = resposta_completa.replace(m.group(0), "").strip()

    if resposta_completa and "Falha de conexão" not in resposta_completa:
        salvar_memoria(texto_usuario, resposta_completa)

    if "[LER_AGENDA]" in resposta_completa or "[LERAGENDA]" in resposta_completa:
        dados_agenda = ler_agenda()
        print(f"\n[C.Y.N.I.C. Workspace] {dados_agenda}\n")
        resposta_completa = resposta_completa.replace("[LER_AGENDA]", "").replace("[LERAGENDA]", "").strip()
        resposta_completa += f" A propósito, verifiquei a sua agenda: {dados_agenda}"

    if "[LER_EMAILS]" in resposta_completa or "[LEREMAILS]" in resposta_completa:
        dados_emails = ler_emails()
        print(f"\n[C.Y.N.I.C. Workspace] {dados_emails}\n")
        resposta_completa = resposta_completa.replace("[LER_EMAILS]", "").replace("[LEREMAILS]", "").strip()
        resposta_completa += f" A propósito, verifiquei os seus e-mails: {dados_emails}"

    return resposta_completa.strip()
