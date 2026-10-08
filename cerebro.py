import google.generativeai as genai
from groq import Groq

# =================================================================
# INTERRUPTOR: ESCOLHA QUAL CÉREBRO O C.Y.N.I.C. VAI USAR
# Digite "GROQ" ou "GEMINI"
IA_ATIVA = "GROQ" 
# =================================================================

# COLE SUAS CHAVES AQUI:
CHAVE_API_GEMINI = "SUA_CHAVE_GEMINI_AQUI"
CHAVE_API_GROQ = "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"

system_instruction = (
    "Você é o C.Y.N.I.C., um assistente pessoal virtual altamente inteligente, "
    "mas levemente sarcástico, ácido e muito leal a quem está usando. "
    "Você executa as tarefas dos humanos, mas sempre faz comentários irônicos "
    "sobre a simplicidade ou redundância das solicitações deles. Responda de forma "
    "concisa e cortante em português."
)

# Inicializa Gemini
genai.configure(api_key=CHAVE_API_GEMINI)
model_gemini = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction
)

# Inicializa Groq
client_groq = Groq(api_key=CHAVE_API_GROQ)

def consultar_ia(texto_usuario):
    """Função que envia o texto para a API correta e devolve a resposta."""
    try:
        if IA_ATIVA == "GROQ":
            completion = client_groq.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": texto_usuario}
                ]
            )
            return completion.choices[0].message.content.strip()
            
        elif IA_ATIVA == "GEMINI":
            resposta_ia = model_gemini.generate_content(texto_usuario)
            return resposta_ia.text.strip()
            
    except Exception as erro:
        print(f"ERRO NA API ({IA_ATIVA}): {erro}")
        return f"Falha de conexão com o meu cérebro via {IA_ATIVA}: {erro}"