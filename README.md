# C.Y.N.I.C.

C.Y.N.I.C. é um assistente pessoal virtual com interação por voz, memória de longo prazo e ações locais no computador. Ele escuta o usuário pelo microfone, transcreve a fala com Whisper, consulta uma IA (Groq ou Gemini), responde em voz com sintetização de fala e pode abrir programas, tocar músicas e consultar agenda/e-mails do Google.

## Visão geral

O projeto combina:

- reconhecimento de voz em tempo real com Whisper
- processamento de linguagem com Groq ou Gemini
- voz de saída com Edge TTS
- memória persistente em ChromaDB
- controle de programas e Spotify no Windows
- integração com Google Calendar e Gmail
- interface web em FastAPI para conversação por navegador

## Funcionalidades principais

- Conversa por voz e texto
- Respostas curtas e sarcásticas, com tom próprio do assistente
- Memória de conversas para contexto futuro
- Ações locais:
  - abrir programas permitidos
  - tocar música no Spotify
  - consultar agenda do Google
  - consultar e-mails não lidos
- Protocolo de resposta com tags especiais para comandos do sistema, como:
  - `[ABRIR: nome]`
  - `[TOCAR: música e artista]`
  - `[LER_AGENDA]`
  - `[LER_EMAILS]`

## Stack tecnológica

- Python
- FastAPI
- WebSocket
- Whisper (faster-whisper)
- ChromaDB
- Groq
- Google Generative AI
- Edge TTS
- Pygame
- Spotipy
- Google API Client

## Estrutura do projeto

```text
.
├── cerebro.py              # cérebro principal da IA, memória e orquestração
├── main.py                 # servidor FastAPI + pipeline de áudio e WebSocket
├── sistema_local.py        # abertura de apps e controle do Spotify
├── workspace_google.py      # acesso à agenda e e-mails do Google
├── static/                 # frontend web (HTML/CSS/JS)
├── memoria_cynic/          # banco persistente para memória do assistente
├── requirements.txt        # dependências do projeto
├── credentials.json        # credenciais OAuth do Google (se necessário)
├── token.json              # token de acesso do Google (gerado pelo app)
├── README.md               # documentação do projeto
└── ...
```

## Requisitos

- Python 3.10+ recomendado
- Sistema operacional Windows para tarefas locais como abrir programas e controlar Spotify
- Microfone do computador
- Chaves de API configuradas em variáveis de ambiente
- Conta Google com acesso a Agenda e Gmail (opcional, para os comandos de leitura)
- Conta Spotify e credenciais do app (opcional, para tocar músicas)

## Pré-requisitos e instalação

1. Clone o repositório:

```bash
git clone https://github.com/Gab-Andrade/C.Y.N.I.C.---Assitent.git
cd C.Y.N.I.C.---Assitent
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Configuração de ambiente

Defina as variáveis de ambiente antes de iniciar o projeto:

### IA

```bash
set GROQ_API_KEY=sua_chave_groq
```

ou

```bash
set GEMINI_API_KEY=sua_chave_gemini
```

### Spotify

```bash
set SPOTIFY_CLIENT_ID=sua_client_id
set SPOTIFY_CLIENT_SECRET=sua_client_secret
set SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

### Google Workspace

O arquivo `credentials.json` deve existir na raiz do projeto para autenticar Google Calendar e Gmail.

## Como executar

Inicie o servidor FastAPI:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Depois abra no navegador:

```text
http://localhost:8000
```

A interface web usa WebSocket para comunicação em tempo real com o assistente.

## Uso do assistente

Depois de abrir o navegador e ativar o microfone, você pode falar comandos como:

- "Oi, C.Y.N.I.C."
- "Abre o bloco de notas"
- "Toca música de sertanejo"
- "Quais são meus próximos compromissos?"
- "Tem e-mail novo?"

O sistema tenta responder de forma direta e com tom irônico, mantendo a resposta curta e objetiva.

## Observações importantes

- O projeto foi pensado para Windows, especialmente para abrir programas nativos e integrar com Spotify.
- A memória do assistente é persistida em `./memoria_cynic`.
- Caso o ambiente não tenha chaves de API configuradas, o assistente pode falhar ao tentar consultar a IA.
- O arquivo `credentials.json` e o token Google devem ser configurados corretamente para as funções de agenda/e-mail.

## Limitações atuais

- Algumas ações dependem de softwares instalados localmente no Windows.
- O controle do Spotify exige autenticação da conta e disponibilidade do app.
- A IA pode responder de forma mais curta e irônica do que um assistente empresarial mais formal.
- O projeto é experimental e foi desenvolvido como ferramenta pessoal/assistiva.

## Desenvolvimento futuro

Possíveis melhorias incluem:

- interface mais avançada com painel de histórico
- suporte a mais apps e automações locais
- configuração de perfis de personalidade e respostas
- melhor gestão de autorização para integrações externas
- persistência mais refinada de memória contextual

## Autor

Projeto desenvolvido para uso pessoal e de automação em ambiente local, com foco em assistência por voz e integração com serviços digitais.
