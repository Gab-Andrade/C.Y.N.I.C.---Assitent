import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import CREDENTIALS_FILE, TOKEN_FILE

# Escopos de permissão (Leitura de E-mails e Agenda)
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'
]


def autenticar_google():
    """Gerencia a autenticação e salva o token de acesso."""
    creds = None
    token_path = TOKEN_FILE
    credentials_path = CREDENTIALS_FILE

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with token_path.open('w', encoding='utf-8') as token:
            token.write(creds.to_json())
    return creds


def ler_agenda():
    """Puxa os próximos 5 compromissos do Google Calendar."""
    try:
        creds = autenticar_google()
        service = build('calendar', 'v3', credentials=creds)

        agora = datetime.datetime.utcnow().isoformat() + 'Z'
        eventos_result = service.events().list(
            calendarId='primary', timeMin=agora,
            maxResults=5, singleEvents=True,
            orderBy='startTime').execute()

        eventos = eventos_result.get('items', [])
        if not eventos:
            return "A agenda está livre. Nenhum compromisso iminente."

        resumo = "Próximos compromissos na agenda:\n"
        for evento in eventos:
            inicio = evento['start'].get('dateTime', evento['start'].get('date'))
            resumo += f"- {evento['summary']} em {inicio}\n"
        return resumo
    except Exception as e:
        return f"Erro ao aceder à agenda: {e}"


def ler_emails():
    """Puxa os últimos 5 e-mails não lidos do Gmail."""
    try:
        creds = autenticar_google()
        service = build('gmail', 'v1', credentials=creds)

        resultados = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=5).execute()
        mensagens = resultados.get('messages', [])
        if not mensagens:
            return "Caixa de entrada limpa. Nenhum e-mail não lido."

        resumo = "Últimos e-mails não lidos:\n"
        for msg in mensagens:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_data['payload']['headers']

            assunto = next((h['value'] for h in headers if h['name'] == 'Subject'), "Sem assunto")
            remetente = next((h['value'] for h in headers if h['name'] == 'From'), "Desconhecido")

            resumo += f"- De: {remetente} | Assunto: {assunto}\n"
        return resumo
    except Exception as e:
        return f"Erro ao aceder aos e-mails: {e}"
