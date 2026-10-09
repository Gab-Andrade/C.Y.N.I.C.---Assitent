# C.Y.N.I.C.

**C.Y.N.I.C.** é um assistente pessoal experimental para Windows, com interface web, escuta de voz pelo microfone do computador que executa o servidor, transcrição local, respostas geradas por IA, fala sintetizada e algumas ações locais e integrações externas.

O projeto está em evolução. Este documento descreve o comportamento e a estrutura existentes hoje; propostas e funcionalidades futuras não devem ser entendidas como já implementadas.

> Para uma apresentação curta e o início rápido, consulte o [README principal](../README.md). Para o desenho dos componentes, consulte [Arquitetura](arquitetura.md).

## Índice

- [Estado atual](#estado-atual)
- [Funcionalidades](#funcionalidades)
- [Arquitetura e fluxo de uma conversa](#arquitetura-e-fluxo-de-uma-conversa)
- [Estrutura de diretórios](#estrutura-de-diretórios)
- [Requisitos](#requisitos)
- [Instalação no Windows](#instalação-no-windows)
- [Configuração](#configuração)
- [Execução](#execução)
- [Uso da interface](#uso-da-interface)
- [Configuração das integrações](#configuração-das-integrações)
- [Caminhos e dados locais](#caminhos-e-dados-locais)
- [Segurança e privacidade](#segurança-e-privacidade)
- [Problemas comuns](#problemas-comuns)
- [Limitações conhecidas](#limitações-conhecidas)
- [Desenvolvimento e manutenção](#desenvolvimento-e-manutenção)
- [Histórico e documentação complementar](#histórico-e-documentação-complementar)

## Estado atual

O projeto já tem:

- aplicação FastAPI servida localmente
- interface web estática com HUD, animações e conexão WebSocket
- captura de áudio pelo microfone padrão do computador servidor
- detecção simples de fala, transcrição em português com Faster Whisper
- integração de geração de texto com Groq ou Gemini, selecionada no código
- memória vetorial persistida localmente com ChromaDB
- síntese de voz via Edge TTS e reprodução local
- ações locais permitidas (abrir alguns programas e controlar Spotify)
- leitura dos próximos compromissos do Google Calendar e de e-mails não lidos do Gmail

O servidor e a interface foram iniciados no ambiente de desenvolvimento. Isso não significa que todas as combinações de microfone, APIs, Google OAuth e Spotify tenham sido validadas de ponta a ponta.

## Funcionalidades

### Voz

1. O backend abre o microfone padrão do computador em que o servidor está rodando.
2. Faz uma calibração inicial do ruído ambiente.
3. Detecta trechos de fala e os transcreve com `faster-whisper`, usando o modelo `small`, CPU e `int8`.
4. Envia o texto reconhecido ao módulo do cérebro.
5. Envia a resposta textual à interface e solicita sua síntese por Edge TTS.
6. Reproduz o áudio nos dispositivos de saída do computador servidor.

O áudio de fala capturado em tempo de execução é mantido em memória durante o processamento. Os arquivos em `app/storage/audios/` são arquivos locais de teste ou referência; o fluxo atual não grava automaticamente cada conversa nessa pasta.

### IA e memória

- O provedor selecionado atualmente é Groq.
- Existe caminho alternativo para Gemini; a troca é manual no código.
- As chaves são lidas de variáveis de ambiente.
- O ChromaDB mantém interações em `app/storage/memoria_cynic/`.
- Antes de consultar a IA, o cérebro tenta recuperar até duas interações relacionadas para acrescentar contexto.
- A resposta pede ao modelo um estilo conciso, em português, com personalidade sarcástica.

### Ações e integrações

- Abrir os aplicativos explicitamente listados em `app/skills/sistema_local.py`.
- Pesquisar e iniciar uma faixa no Spotify, com autenticação OAuth.
- Consultar até cinco próximos eventos do Google Calendar.
- Consultar até cinco mensagens não lidas da caixa de entrada do Gmail.

As integrações Google e Spotify são opcionais. Dependem de configuração externa e não são necessárias para iniciar a interface.

### Programas que podem ser abertos

A lista fica em `APPS_PERMITIDOS`, em `app/skills/sistema_local.py`. Os nomes atualmente reconhecidos são:

| Nome pedido | Programa/ação |
|---|---|
| `bloco de notas` | Notepad do Windows |
| `calculadora` | Calculadora do Windows |
| `vscode` | Visual Studio Code, se o comando `code` estiver disponível |
| `navegador` | Abre Google no navegador padrão |
| `spotify` | Tenta abrir o aplicativo Spotify |

Exemplos de pedidos por voz: “abre a calculadora”, “abre o VS Code” ou “toca Evidências do Chitãozinho e Xororó”. A execução depende de a IA devolver a tag correspondente e o nome ser compatível com a lista. Para adicionar outro programa, altere essa lista de forma explícita; não transforme texto livre em comando de shell.

## Arquitetura e fluxo de uma conversa

```text
Navegador
  ├── GET /             → app/static/index.html
  ├── GET /static/...   → HTML, CSS e JavaScript
  └── WebSocket /ws     ← estados e mensagens do servidor
                            │
                            ▼
                     app/main.py
                      ├── captura de áudio (sounddevice)
                      ├── detecção de fala
                      ├── transcrição (Faster Whisper)
                      ├── reprodução (pygame)
                      └── síntese (Edge TTS)
                            │
                            ▼
                     app/cerebro.py
                      ├── contexto persistido (ChromaDB)
                      ├── provedor de IA (Groq ou Gemini)
                      └── execução de comandos/tags
                           ├── app/skills/sistema_local.py
                           └── app/skills/workspace_google.py
```

### Responsabilidade dos módulos

- **`app/main.py`**: cria a aplicação FastAPI, serve o frontend, mantém o WebSocket e executa o ciclo de áudio, transcrição e voz.
- **`app/cerebro.py`**: define personalidade/modelos, consulta os provedores, busca e grava memória e encaminha ações.
- **`app/config.py`**: define caminhos absolutos para os diretórios de dados, credenciais e frontend. Os caminhos são derivados da localização do próprio arquivo, não do diretório atual do terminal.
- **`app/skills/sistema_local.py`**: lista permitida de programas e integração atual com Spotify.
- **`app/skills/workspace_google.py`**: OAuth e chamadas de leitura para Google Calendar e Gmail.
- **`app/static/`**: interface web e seus recursos.

### Estados enviados ao navegador

O WebSocket em `/ws` envia objetos JSON com os campos `estado` e `mensagem`. Os estados usados pelo frontend incluem:

- `pronto`: calibração ou assistente disponível
- `ouvindo`: monitorando o microfone
- `processando`: transcrevendo ou consultando a IA
- `respondendo`: resposta textual/voz em andamento

O navegador reconecta automaticamente quando o WebSocket cai. A interface exibe o estado; a captura e o processamento da fala ocorrem no backend.

## Estrutura de diretórios

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── cerebro.py
│   ├── config.py
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── sistema_local.py
│   │   └── workspace_google.py
│   ├── credentials/
│   │   └── credentials.json       # criado/configurado localmente; não versionar
│   ├── tokens/
│   │   └── token.json             # criado no OAuth; não versionar
│   ├── storage/
│   │   ├── memoria_cynic/         # banco ChromaDB local
│   │   ├── audios/                # amostras/arquivos de áudio locais
│   │   └── logs/                  # reservado para logs locais
│   └── static/
│       ├── index.html
│       ├── script.js
│       └── style.css
├── docs/
│   └── arquitetura.md
├── reports/
│   ├── relatorio-geral.txt
│   └── relatorio-08-10.txt
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

Os arquivos locais de credenciais, tokens e banco de memória podem não aparecer em um clone novo: alguns são ignorados pelo Git de propósito e devem ser configurados ou criados no computador de execução.

## Requisitos

- Windows recomendado e usado para as ações locais atualmente implementadas.
- Python compatível com as dependências listadas em `requirements.txt`.
- Microfone e saída de áudio funcionando no computador servidor.
- Acesso à internet para os provedores de IA, Edge TTS, autenticação/serviços Google e Spotify e, na primeira execução, obtenção de recursos que ainda não estejam em cache.
- `ffmpeg` instalado e disponível no `PATH` para o processamento MP3 feito pelo Pydub.
- Chaves/credenciais somente para as integrações que forem utilizadas.

O modelo Faster Whisper usado é `small` em CPU com `int8`. A primeira inicialização pode demorar e baixar o modelo se ele ainda não estiver em cache.

## Instalação no Windows

Abra o PowerShell na raiz do projeto — a pasta que contém `requirements.txt`.

### 1. Criar e ativar o ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se a política do PowerShell impedir a ativação, pode-se chamar diretamente o Python do ambiente sem ativá-lo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Instalar dependências Python

Com `.venv` ativo:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Instalar FFmpeg

Instale uma distribuição de FFmpeg para Windows e inclua a pasta `bin` no `PATH`. Feche e reabra o terminal depois de alterar o `PATH`. Confirme com:

```powershell
ffmpeg -version
```

O Pydub usa FFmpeg para decodificar o áudio MP3 retornado pelo serviço de voz.

## Configuração

### Chaves de IA

O código lê `GROQ_API_KEY` e `GEMINI_API_KEY` do ambiente do processo. No PowerShell, defina a chave para a sessão atual antes de iniciar o servidor:

```powershell
$env:GROQ_API_KEY = "sua-chave-groq"
```

Para selecionar Gemini em vez de Groq, configure a chave correspondente:

```powershell
$env:GEMINI_API_KEY = "sua-chave-gemini"
```

No estado atual, `IA_ATIVA` está definido como `"GROQ"` em `app/cerebro.py`. Para selecionar Gemini é preciso mudar esse valor para `"GEMINI"` no código e iniciar novamente o servidor. Definir a chave Gemini, por si só, não troca o provedor ativo.

`.env.example` é apenas uma lista-modelo de nomes de variáveis: a aplicação não carrega automaticamente arquivos `.env`.

### Google Calendar e Gmail

1. Crie um projeto no Google Cloud.
2. Ative as APIs Google Calendar e Gmail.
3. Configure a tela de consentimento OAuth conforme o uso da conta.
4. Crie credenciais OAuth do tipo **aplicativo para computador**.
5. Coloque o arquivo baixado em `app/credentials/credentials.json`.
6. Na primeira consulta à agenda ou aos e-mails, autorize o acesso no navegador. O token será gravado em `app/tokens/token.json`.

Os escopos usados são somente leitura: calendário e Gmail. Se as permissões mudarem no futuro, pode ser necessário remover o token local e autorizar novamente.

### Spotify

Para habilitar controle de reprodução:

1. Crie/configure um aplicativo no Spotify for Developers.
2. Cadastre a Redirect URI `http://127.0.0.1:8888/callback` no painel do Spotify.
3. Defina as variáveis no PowerShell:

```powershell
$env:SPOTIFY_CLIENT_ID = "seu-client-id"
$env:SPOTIFY_CLIENT_SECRET = "seu-client-secret"
$env:SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
```

4. Opcionalmente, autorize a conta antes de iniciar a aplicação:

```powershell
python -m app.skills.sistema_local
```

O Spotipy mantém seu cache OAuth local. O controle de reprodução depende de um dispositivo Spotify disponível; a implementação informa que reprodução por API requer conta Premium.

## Execução

Com o terminal na raiz do repositório e `(.venv)` ativo, inicie o servidor local:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra no mesmo computador:

```text
http://localhost:8000
```

O endereço `http://127.0.0.1:8000` é equivalente. O processo fica ativo no terminal; use `Ctrl+C` para encerrá-lo. Se já houver outra instância usando a porta 8000, encerre-a ou escolha outra porta, por exemplo `--port 8001`.

### Modo de desenvolvimento

Para reiniciar o servidor automaticamente após alterações nos arquivos:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

`--reload` é uma conveniência de desenvolvimento, não um requisito para executar o assistente. Evite `--host 0.0.0.0` para uso exclusivamente local: esse endereço faz o servidor escutar em interfaces de rede além do loopback.

## Uso da interface

- A página é servida em `/`; os arquivos estáticos são servidos em `/static/`.
- O backend começa a escutar pelo microfone padrão do computador servidor quando um cliente WebSocket se conecta.
- No primeiro ciclo, o servidor pede silêncio por aproximadamente 1,5 segundo para calibrar o ruído.
- Fale depois que o estado indicar que está monitorando/ouvindo.
- O limiar de fala é calculado a partir do ruído ambiente, com um valor mínimo de segurança.
- O servidor ignora a entrada de microfone enquanto há áudio sendo sintetizado ou reproduzido, reduzindo eco.
- A resposta textual aparece na interface e também é enviada para síntese/reprodução local.

### Controles visuais

- **Q**: alterna a qualidade visual do HUD; a escolha é salva no armazenamento local do navegador.
- **M**: solicita acesso ao microfone do navegador para analisar o nível de áudio e animar a visualização.
- **F**: alterna tela cheia.

Importante: o botão **M** controla o microfone usado pela animação visual no navegador. Ele não liga nem desliga a captura de áudio do backend. A fala reconhecida pelo assistente vem do microfone padrão do computador onde o servidor está rodando.

## Caminhos e dados locais

`app/config.py` centraliza os caminhos como objetos `Path` absolutos:

- `STATIC_DIR`: frontend
- `CREDENTIALS_FILE` e `TOKEN_FILE`: OAuth Google
- `MEMORIA_DIR`: banco vetorial
- `AUDIOS_DIR`: arquivos de áudio locais
- `LOGS_DIR`: diretório reservado para logs

Os caminhos são calculados a partir da localização do pacote, por isso a execução deve ser feita a partir da raiz do projeto e o comando recomendado usa `app.main:app`. A memória e os tokens ficam no computador local e persistem entre execuções.

## Segurança e privacidade

- Nunca publique nem envie ao GitHub chaves de API, `credentials.json`, `token.json` ou caches OAuth.
- Não cole segredos em issues, relatórios ou capturas de tela.
- `.gitignore` ignora os arquivos locais de credenciais, token e banco de memória. Verifique o status do Git antes de qualquer commit para garantir que nenhum segredo foi adicionado.
- As chaves definidas com `$env:...` ficam disponíveis aos processos iniciados a partir daquele terminal. Fechar o terminal encerra esse escopo de ambiente.
- O backend abre o microfone do computador servidor e envia o texto transcrito aos provedores de IA. O áudio de entrada não é enviado diretamente ao modelo de linguagem pelo código atual, mas o texto reconhecido é.
- As consultas Google leem dados da agenda/Gmail de acordo com os escopos autorizados.
- Não exponha o servidor à rede pública. `0.0.0.0` amplia a interface de escuta e exige medidas adicionais de rede e segurança que esta aplicação ainda não documenta nem implementa.
- As ações disponíveis para abertura de programas são limitadas por uma lista no código; não acrescente execução arbitrária de comandos recebidos da IA.

## Problemas comuns

### `Could not import module "app.main"`

Confirme que o terminal está na raiz do repositório, que `app/main.py` existe e que o ambiente virtual está ativo. Rode novamente:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Porta 8000 já está em uso

Pare a instância anterior com `Ctrl+C` no terminal em que ela está rodando. Alternativamente, use outra porta e acesse a mesma porta no navegador:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Falta de `GROQ_API_KEY` ou falha de IA

Defina a variável no mesmo terminal antes de iniciar o Uvicorn. Confira também se `IA_ATIVA` está selecionando o provedor cuja chave foi configurada e se há conexão com a internet.

### Falha ao abrir ou calibrar o microfone

Verifique se o Windows reconhece um dispositivo de entrada padrão, feche outros programas que possam estar ocupando-o e confira as permissões de microfone do sistema. A captura é feita no computador servidor, não pelo transporte WebSocket do navegador.

### Falha em áudio/FFmpeg

Confirme que `ffmpeg -version` funciona no mesmo terminal e que a instalação Python incluiu `pydub`, `pygame` e `edge-tts`.

### Modelo Whisper demora para iniciar

O modelo configurado é `small`; a primeira inicialização pode baixar os arquivos e ocupar CPU/memória. Aguarde a mensagem de carregamento no terminal.

### Integração Google pede autenticação repetidamente

Confirme que o arquivo OAuth está no caminho correto, que as APIs estão habilitadas e que o token pode ser gravado. Se os escopos forem alterados, remova o token antigo e repita o consentimento.

## Limitações conhecidas

- O provedor ativo e os nomes de modelo são selecionados no código, não por uma tela de configuração.
- A aplicação utiliza o microfone e os dispositivos de áudio locais do processo servidor; não é um serviço multiusuário.
- O fluxo coleta a resposta da IA antes de enviá-la à fila de voz; apesar da resposta do provedor ser recebida em streaming, a fala não é sintetizada incrementalmente frase a frase neste caminho atual.
- O controle de ações depende de tags presentes na resposta do modelo e de integrações configuradas.
- O frontend carrega Three.js de um CDN; sem acesso ao CDN, a interface pode perder os elementos 3D.
- O Edge TTS depende de serviço e conectividade externos.
- `app/storage/logs/` existe como destino futuro; o código atual imprime diagnósticos e erros no terminal.
- Ainda não há suíte de testes automatizados documentada para validar microfone, APIs reais ou reprodução em todos os ambientes.

## Desenvolvimento e manutenção

- Execute os comandos a partir da raiz do repositório para que o pacote `app` seja importado corretamente.
- Mantenha código em `app/`, dados locais em `app/storage/`, integrações em `app/skills/` e documentação em `docs/`/`reports/`.
- Atualize este guia quando comandos, variáveis, diretórios ou comportamento externo mudarem.
- Atualize `arquitetura.md` quando mudar o fluxo ou as responsabilidades dos módulos.
- Não adicione credenciais reais ao `.env.example`; mantenha apenas nomes de variáveis e valores fictícios.
- A integração Spotify ainda faz parte de `sistema_local.py`; não existe um módulo `spotify.py` nesta versão.

## Histórico e documentação complementar

- [Arquitetura](arquitetura.md): visão resumida da organização dos módulos.
- [Relatório geral](../reports/relatorio-geral.txt): registro da reorganização do projeto.
- [Relatório de 08-10](../reports/relatorio-08-10.txt): relatório histórico de alterações do HUD e do pipeline de áudio. Por ser um registro de uma etapa anterior, algumas descrições podem não refletir os valores atuais do código.
