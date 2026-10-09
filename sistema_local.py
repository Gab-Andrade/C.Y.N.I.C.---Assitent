import os
import platform
import subprocess
import time

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    spotipy = None


# =================================================================
# APPS: só o que estiver nesta lista pode ser aberto pela voz.
# A IA escolhe um NOME; o comando real é definido aqui, no código.
# Para liberar outro app, adicione uma linha (não use shell nem texto vindo da fala).
# =================================================================
APPS_PERMITIDOS = {
    "bloco de notas": ["notepad.exe"],
    "calculadora": ["calc.exe"],
    "vscode": ["cmd", "/c", "code"],
    "navegador": ["cmd", "/c", "start", "", "https://www.google.com"],
    "spotify": ["cmd", "/c", "start", "", "spotify:"],
}


def abrir_programa(nome):
    """Abre um programa da lista APPS_PERMITIDOS (Windows). Sem shell=True."""
    if platform.system() != "Windows":
        return "Abrir programas só está configurado para Windows."

    chave = nome.lower().strip().strip(".")
    cmd = APPS_PERMITIDOS.get(chave)
    if cmd is None:
        return f"'{nome}' não está na lista de apps permitidos."

    try:
        subprocess.Popen(cmd)
        return f"{chave} aberto."
    except Exception as e:
        return f"Erro ao abrir {chave}: {e}"


# =================================================================
# SPOTIFY
# Variáveis de ambiente: SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET
# Redirect URI cadastrada no dashboard (igual, sem diferença nenhuma):
#   http://127.0.0.1:8888/callback
# =================================================================
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
ESCOPO = "user-modify-playback-state user-read-playback-state"

_sp = None


def _spotify():
    """Cria o cliente do Spotify uma vez e reaproveita (o token fica salvo no arquivo .cache)."""
    global _sp
    if _sp is None:
        if spotipy is None:
            raise RuntimeError("biblioteca spotipy não instalada (pip install spotipy)")
        client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET não definidos")
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=REDIRECT_URI,
            scope=ESCOPO,
            open_browser=True,
        ))
    return _sp


def _dispositivo(sp):
    """Devolve o id de um dispositivo Spotify; se não houver, tenta abrir o app e esperar."""
    def listar():
        return sp.devices().get("devices", [])

    devs = listar()
    if not devs:
        abrir_programa("spotify")
        for _ in range(8):
            time.sleep(1)
            devs = listar()
            if devs:
                break
    if not devs:
        return None
    ativos = [d for d in devs if d.get("is_active")]
    return (ativos or devs)[0]["id"]


def tocar_musica(busca):
    """Pesquisa a faixa no Spotify e toca no dispositivo ativo."""
    busca = (busca or "").strip()
    if not busca:
        return "Nenhuma música informada."
    if spotipy is None:
        return "Biblioteca spotipy não instalada (pip install spotipy)."

    try:
        sp = _spotify()
        itens = sp.search(q=busca, type="track", limit=1)["tracks"]["items"]
        if not itens:
            return f"Não encontrei '{busca}' no Spotify."
        faixa = itens[0]

        device_id = _dispositivo(sp)
        if device_id is None:
            return "Nenhum dispositivo Spotify disponível. Abra o Spotify no PC e tente de novo."

        sp.start_playback(device_id=device_id, uris=[faixa["uri"]])
        return f"Tocando {faixa['name']} de {faixa['artists'][0]['name']}."
    except spotipy.SpotifyException as e:
        if e.http_status == 403:
            return "O Spotify recusou o comando: a conta precisa ser Premium para controlar a reprodução."
        return f"Erro do Spotify: {e}"
    except Exception as e:
        return f"Não consegui tocar: {e}"


# Rode "python sistema_local.py" UMA vez para autorizar a conta no navegador.
# Depois disso o token fica salvo e o C.Y.N.I.C. toca sem pedir nada.
if __name__ == "__main__":
    sp = _spotify()
    nomes = [d["name"] for d in sp.devices().get("devices", [])]
    print("Spotify autorizado. Dispositivos encontrados:", nomes or "nenhum (abra o Spotify)")