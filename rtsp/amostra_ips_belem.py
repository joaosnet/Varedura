import sys
import requests
import ipaddress
import random
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Exemplo de ASNs (Sistemas Autônomos) fortemente ligados a Belém/Pará
# AS53016: PRODEPA (Empresa de Tecnologia da Informação e Comunicação do Pará)
# AS28328: UFPA (Universidade Federal do Pará)
# AS262615: Exemplo de provedor regional do Norte
# AS265175: AS SISTEMAS LTDA (Operadora do Usuário)
ASNS_BELEM = [53016, 28328, 262615, 265175]

# Dados de fallback offline (blocos reais) caso a API esteja bloqueada na sua rede
FALLBACK_DATA = {
    53016: ["177.74.0.0/19", "177.105.0.0/19", "200.241.128.0/19"],
    28328: ["200.239.64.0/20", "200.17.110.0/24"],
    262615: ["45.174.216.0/22", "170.245.24.0/22"],
    265175: ["167.249.208.0/22", "206.84.32.0/19"] # <- Adicionado os blocos da sua operadora!
}

def buscar_prefixos_por_asn(asn):
    """
    Consulta a API pública do BGPView para descobrir quais blocos de IP
    (prefixos) um determinado ASN está anunciando na internet.
    """
    url = f"https://api.bgpview.io/asn/{asn}/prefixes"
    headers = {'User-Agent': 'Mozilla/5.0 (Python IP Sampler)'}

    try:
        # Adicionado timeout de 5 segundos para não ficar travado
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # Retorna apenas os prefixos IPv4
            return [prefixo['prefix'] for prefixo in data['data']['ipv4_prefixes']]
        else:
            console.print(f"[yellow]Aviso: API retornou status {response.status_code}. Usando dados locais (fallback).[/yellow]")
    except Exception as e:
        # Pega o erro de DNS/Conexão de forma amigável
        console.print(f"[yellow]Aviso: Falha na rede ao consultar ASN {asn} ({type(e).__name__}). Usando dados locais (fallback)...[/yellow]")

    # Retorna os blocos salvos no código caso a internet/API falhe
    return FALLBACK_DATA.get(asn, [])

def obter_blocos_rede(asns=None):
    """Coleta e retorna uma lista com os blocos de rede (IPv4Network)."""
    if asns is None:
        asns = ASNS_BELEM

    blocos = []
    for asn in asns:
        prefixos = buscar_prefixos_por_asn(asn)
        for prefixo in prefixos:
            blocos.append(ipaddress.IPv4Network(prefixo, strict=False))
    return blocos

def obter_espaco_amostral_completo(blocos=None):
    """
    Retorna uma lista contendo TODOS os endereços de IP utilizáveis
    dentro dos blocos fornecidos. Ideal para ser importado por outros scripts.
    """
    if blocos is None:
        blocos = obter_blocos_rede()

    todos_ips = []
    for bloco in blocos:
        # .hosts() ignora o IP de rede e o de broadcast (apenas IPs utilizáveis)
        for ip in bloco.hosts():
            todos_ips.append(str(ip))
    return todos_ips

def obter_amostra_aleatoria(tamanho_amostra=5, blocos=None):
    """
    Retorna uma quantidade específica de IPs sorteados aleatoriamente.
    """
    if blocos is None:
        blocos = obter_blocos_rede()

    ips_sorteados = []
    if blocos:
        blocos_aleatorios = random.choices(blocos, k=tamanho_amostra)
        for bloco in blocos_aleatorios:
            lista_ips = list(bloco.hosts())
            if lista_ips:
                ip_escolhido = random.choice(lista_ips)
                ips_sorteados.append(str(ip_escolhido))
    return ips_sorteados

if __name__ == "__main__":
    # Corrige problemas de codificação (como emojis) no Windows ao redirecionar para arquivos (>)
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    console.print(Panel.fit("[bold blue]📡 Gerador de Espaço Amostral de IPs - Belém/PA[/bold blue]"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:

        task1 = progress.add_task("[cyan]Coletando os blocos de rede (via API ou fallback)...[/cyan]", total=None)
        blocos_encontrados = obter_blocos_rede()
        progress.remove_task(task1)

        task2 = progress.add_task("[green]Expandindo os blocos para gerar todos os IPs...[/green]", total=None)
        espaco_amostral = obter_espaco_amostral_completo(blocos_encontrados)

    # Cria uma tabela bonita para mostrar os blocos
    tabela = Table(title="Subconjuntos (Blocos CIDR) Encontrados", show_header=True, header_style="bold magenta")
    tabela.add_column("Bloco de Rede", style="cyan", justify="center")
    tabela.add_column("Total de IPs", style="green", justify="right")

    for bloco in blocos_encontrados:
        tabela.add_row(str(bloco), f"{bloco.num_addresses:,}".replace(',', '.'))

    console.print(tabela)

    # Mostra o painel de resumo
    resumo_texto = (
        f"Total de blocos: [bold]{len(blocos_encontrados)}[/bold]\n"
        f"Tamanho do Espaço Amostral: [bold green]{len(espaco_amostral):,}[/bold green] IPs utilizáveis"
    ).replace(',', '.')

    console.print(Panel(resumo_texto, title="[bold yellow]Resumo do Espaço Amostral[/bold yellow]", border_style="yellow"))

    console.print("\n[bold dim]Imprimindo o espaço amostral completo abaixo...[/bold dim]")
    console.print("-" * 50)

    # Imprime o espaço amostral completo (usando print padrão por ser mais rápido para 30k+ linhas)
    for ip in espaco_amostral:
        print(ip)

    console.print("-" * 50)
    console.print("[bold green]✔ Processo concluído![/bold green]")
    console.print("[dim]Dica: Para salvar a lista em um arquivo de texto para análise, execute no terminal:[/dim]")
    console.print("[bold cyan]uv run amostra_ips_belem.py > todos_ips_belem.txt[/bold cyan]\n")
