import os
import subprocess
import platform

def abrir_programa(nome_programa):
    """Abre programas instalados no Windows."""
    sistema = platform.system()
    
    # Mapeamento de atalhos comuns para executáveis do Windows
    programas = {
        "bloco de notas": "notepad.exe",
        "calculadora": "calc.exe",
        "vscode": "code",
        "spotify": "spotify",
        "navegador": "start https://google.com",
        "cmd": "cmd.exe"
    }
    
    comando = programas.get(nome_programa.lower().strip(), nome_programa)
    
    try:
        # Popen roda o processo em segundo plano sem travar o servidor
        subprocess.Popen(comando, shell=True)
        return f"Sucesso: {nome_programa} iniciado."
    except Exception as e:
        return f"Erro ao tentar abrir {nome_programa}: {e}"

def ler_arquivo(caminho):
    """Lê o conteúdo de um arquivo local e retorna para a IA."""
    try:
        if not os.path.exists(caminho):
            return "Erro: Arquivo não encontrado."
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Erro de leitura: {e}"

def escrever_arquivo(caminho, conteudo):
    """Cria ou substitui o conteúdo de um arquivo de código/texto."""
    try:
        with open(caminho, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        return f"Sucesso: Arquivo {caminho} modificado."
    except Exception as e:
        return f"Erro ao escrever: {e}"