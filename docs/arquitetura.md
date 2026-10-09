# Arquitetura atual

Este documento descreve os limites e as responsabilidades dos módulos presentes. Para instalação, configuração de provedores, OAuth e execução, consulte o [guia completo](guia-completo.md) ou a página inicial do [README](../README.md).

## Visão de componentes

```text
Browser / HUD
  ├── HTTP GET /
  ├── HTTP GET /static/*
  └── WebSocket /ws
        │ mensagens JSON: estado + mensagem
        ▼
FastAPI — app/main.py
  ├── motor de áudio local
  ├── Faster Whisper
  ├── Edge TTS
  └── pygame
        │ texto reconhecido
        ▼
Cérebro — app/cerebro.py
  ├── ChromaDB — memória persistente
  ├── Groq ou Gemini — geração de texto
  └── dispatch por tags
        ├── app/skills/sistema_local.py
        └── app/skills/workspace_google.py
```

## Módulos

### `app/main.py`

Define a aplicação FastAPI, monta os arquivos estáticos e publica `/` e `/ws`. A conexão WebSocket cria uma thread para o ciclo de audição; ao fechar a conexão, o sinal de parada é enviado à thread. O áudio é lido do dispositivo de entrada padrão da máquina que executa o servidor.

O ciclo atual calibra o ruído por cerca de 1,5 segundo, usa blocos de 0,1 segundo a 16 kHz, conserva cerca de 0,3 segundo de pré-áudio, exige aproximadamente 0,3 segundo de fala acima do limiar e encerra a captura após quatro blocos silenciosos (aproximadamente 0,4 segundo). O áudio capturado é transcrito com Faster Whisper (`small`, CPU, `int8`, idioma português).

As respostas são sintetizadas por Edge TTS. Pydub aplica o processamento de áudio; pygame reproduz o resultado. O código inicia os motores e o modelo Whisper durante a importação do módulo, então a inicialização do servidor pode demorar.

### `app/cerebro.py`

Inicializa o cliente ChromaDB e os clientes de IA. A variável `IA_ATIVA` escolhe o provedor; atualmente é `"GROQ"`. O módulo prepara o contexto a partir de até duas conversas relevantes, gera o texto, remove/processa tags de ação e salva a conversa em memória quando a resposta não indica falha de conexão.

As tags reconhecidas atualmente:

| Tag | Ação |
|---|---|
| `[ABRIR: nome]` | Encaminha o nome à lista permitida em `sistema_local.py`. |
| `[TOCAR: busca]` | Encaminha a busca para a integração Spotify de `sistema_local.py`. |
| `[LER_AGENDA]` | Consulta o Google Calendar e anexa o resumo à resposta. |
| `[LER_EMAILS]` | Consulta mensagens não lidas do Gmail e anexa o resumo. |

As tags de agenda/e-mail têm também tratamento para as variantes sem sublinhado `[LERAGENDA]` e `[LEREMAILS]`.

### `app/config.py`

Centraliza caminhos absolutos calculados a partir da localização do pacote. Assim, os módulos não dependem de caminhos relativos ao diretório em que o terminal foi aberto.

### `app/skills/sistema_local.py`

Contém a allowlist de programas locais e a implementação Spotify via Spotipy. A abertura de programas só está configurada para Windows e não usa `shell=True`. Spotify ainda está dentro deste módulo; não há `spotify.py` separado.

### `app/skills/workspace_google.py`

Gerencia o fluxo OAuth e as chamadas Google Calendar e Gmail. Os arquivos esperados são `app/credentials/credentials.json` e `app/tokens/token.json`; ambos são locais e não devem ser versionados.

### `app/static/`

Contém a página HTML, estilos e JavaScript do HUD. O navegador recebe os estados do backend por WebSocket. O microfone acessado pelo botão visual do navegador é usado para animar a interface; não substitui o microfone que o backend abre na máquina servidor.

## Fluxo ponta a ponta

1. O navegador obtém `GET /` e os recursos em `/static/`.
2. O JavaScript estabelece `/ws`.
3. O backend inicia o motor de audição e notifica estados como `pronto` e `ouvindo`.
4. O microfone do servidor é monitorado; fala detectada é transcrita.
5. O texto segue para `consultar_ia()` no cérebro.
6. O cérebro recupera contexto, chama o provedor ativo e processa eventuais tags.
7. A resposta textual é enviada ao frontend e à fila local de síntese/reprodução.
8. Enquanto a voz toca, a captura é ignorada para reduzir eco.

## Dados persistentes

- ChromaDB: `app/storage/memoria_cynic/`
- Áudios de teste/referência: `app/storage/audios/`
- Logs reservados: `app/storage/logs/`
- Credenciais Google: `app/credentials/`
- Token Google: `app/tokens/`

O código ignora esses dados locais relevantes no Git conforme aplicável. A configuração de ignorados não substitui a revisão do `git status` antes de commits.

## Limites atuais

- A resposta do provedor é recebida via streaming, mas `consultar_ia()` agrega as frases antes de retornar; o TTS começa após essa agregação, não a cada frase recebida.
- A aplicação não implementa autenticação de usuário, isolamento multiusuário ou controles para exposição pública.
- Não há configuração de provedor via interface nem suíte automatizada de integração cobrindo serviços externos.
- O Three.js é carregado de CDN; Edge TTS e provedores externos requerem conectividade.
