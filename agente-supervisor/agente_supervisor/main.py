"""
Supervisor — Operação Assistida
Gera status.txt com rastreabilidade de qualquer instancia ativa.
Sessao unica por usuario@maquina.

Uso:
    python agente_supervisor/main.py
    python agente_supervisor/main.py --watch   # atualiza a cada 10s
"""
import argparse
import hashlib
import os
import socket
import subprocess
import sys
import time
from datetime import datetime

HOST_PORT = 8765
STATUS_FILE = os.path.join(os.path.dirname(__file__), "status.txt")


# ── identificadores ──────────────────────────────────────────────────────────

def get_identity() -> dict:
    username = os.getlogin()
    hostname = socket.gethostname()
    raw = f"{username}@{hostname}"
    session_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return {"username": username, "hostname": hostname, "session_id": session_id, "raw": raw}


# ── verificacoes ─────────────────────────────────────────────────────────────

def check_port(port: int) -> tuple[bool, str]:
    """Testa se o WebSocket host esta escutando na porta."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        result = s.connect_ex(("127.0.0.1", port))
    if result == 0:
        return True, "ATIVO"
    return False, f"INATIVO (erro {result})"


def check_processes() -> list[dict]:
    """Retorna processos python que contenham 'main.py' ou 'operacao_assistida'."""
    found = []
    try:
        ps_cmd = (
            "Get-WmiObject Win32_Process -Filter \"name='python.exe' OR name='pythonw.exe'\" | "
            "Select-Object ProcessId, CommandLine | ConvertTo-Csv -NoTypeInformation"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout

        for line in out.splitlines()[1:]:  # pula cabecalho CSV
            lower = line.lower()
            if "operacao_assistida" in lower and "agente_supervisor" not in lower:
                parts = line.strip('"').split('","')
                pid = parts[0].strip('"') if len(parts) > 0 else "?"
                cmd = parts[1].strip('"') if len(parts) > 1 else line.strip()
                # limpa aspas extras e encurta para exibir so o script
                cmd_clean = cmd.strip('"').replace('""', '').strip()
                found.append({"pid": pid, "cmd": cmd_clean})
    except Exception as e:
        found.append({"pid": "?", "cmd": f"[erro ao listar processos: {e}]"})
    return found


def check_network_interfaces() -> list[str]:
    """Lista IPs locais disponiveis para conexao externa."""
    ips = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip.startswith("127.") or ":" in ip: # type: ignore
                continue
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips or ["(nao identificado)"]


# ── geracao do relatorio ─────────────────────────────────────────────────────

def build_report(identity: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    port_ok, port_status = check_port(HOST_PORT)
    processes = check_processes()
    interfaces = check_network_interfaces()

    lines = []
    sep = "=" * 60

    lines += [
        sep,
        "  OPERAÇÃO ASSISTIDA — SUPERVISOR",
        sep,
        f"  Sessão ID  : {identity['session_id']}",
        f"  Identidade : {identity['raw']}",
        f"  Usuário    : {identity['username']}",
        f"  Máquina    : {identity['hostname']}",
        f"  Gerado em  : {now}",
        "",
    ]

    lines += [
        "─" * 60,
        "  STATUS DO SERVIÇO",
        "─" * 60,
        f"  WebSocket host (porta {HOST_PORT}) : {port_status}",
    ]

    if port_ok:
        for ip in interfaces:
            lines.append(f"    Acessível em : ws://{ip}:{HOST_PORT}")
    lines.append("")

    lines += [
        "─" * 60,
        "  PROCESSOS ATIVOS",
        "─" * 60,
    ]
    if processes:
        for p in processes:
            lines.append(f"  PID {p['pid']:>6} | {p['cmd']}")
    else:
        lines.append("  Nenhum processo do app encontrado.")
    lines.append("")

    lines += [
        "─" * 60,
        "  RASTREABILIDADE",
        "─" * 60,
        f"  Endpoint WebSocket : ws://{identity['hostname']}:{HOST_PORT}",
        f"  Sessao unica por   : usuario + maquina (SHA-256 truncado)",
        f"  Chave de sessao    : SHA256({identity['raw']!r})[:16]",
        f"                     = {identity['session_id']}",
        "",
        "  Esta sessao identifica unicamente este host no sistema.",
        "  Use o session_id para correlacionar logs e tarefas remotas.",
        "",
        sep,
        f"  Atualizado em : {now}",
        sep,
    ]

    return "\n".join(lines)


# ── entry point ──────────────────────────────────────────────────────────────

def run_once():
    identity = get_identity()
    report = build_report(identity)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace") # type: ignore
    print(report)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n  >> Salvo em: {STATUS_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Supervisor — Operação Assistida")
    parser.add_argument("--watch", action="store_true", help="Atualiza a cada 10 segundos")
    parser.add_argument("--interval", type=int, default=10, help="Intervalo em segundos (default: 10)")
    args = parser.parse_args()

    if args.watch:
        print(f"Modo watch ativo — atualizando a cada {args.interval}s. Ctrl+C para parar.\n")
        try:
            while True:
                os.system("cls")
                run_once()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nSupervisor encerrado.")
    else:
        run_once()


if __name__ == "__main__":
    main()
