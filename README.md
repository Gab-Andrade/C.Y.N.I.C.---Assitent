# C.Y.N.I.C.

Assistente pessoal experimental para Windows, com interface web, interação por voz, IA, memória local e integrações opcionais.

## Início rápido

Com o ambiente virtual ativado e o terminal aberto na raiz do projeto:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra [http://localhost:8000](http://localhost:8000). Para parar o servidor, pressione `Ctrl+C` no terminal.

## Documentação

- **[Guia completo](docs/guia-completo.md)** — instalação, configuração, execução, uso, integrações, segurança, solução de problemas e limitações.
- **[Arquitetura](docs/arquitetura.md)** — componentes, responsabilidades dos módulos e fluxo de uma conversa.
- **[Relatórios](reports/)** — histórico de alterações e registros do projeto.

## Estrutura

- `app/` — aplicação e código Python
- `app/skills/` — ações locais e integrações
- `app/static/` — interface web
- `app/storage/` — memória, amostras de áudio e dados locais
- `app/credentials/` e `app/tokens/` — credenciais e tokens locais; não publicar
- `docs/` — documentação técnica e guia do projeto
- `reports/` — relatórios de desenvolvimento

O C.Y.N.I.C. está em desenvolvimento. Consulte a documentação para requisitos, chaves necessárias, integrações opcionais e limitações atuais.
