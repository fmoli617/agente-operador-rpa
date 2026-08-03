"""
Simulador interativo — dirige manualmente todos os retornos do protocolo
(login_error, credentials_error, execution_error, execution_started, QR de
validação) contra um agente-operador real, sem precisar escrever uma
automação de verdade. Portado de agente-bot/versao-antiga/examples/example.py
para a SessaoOperador atual (services/operacao_assistida.py) e o vocabulário
de "sistema" usado hoje.

Uso:
    python scripts/simulador_manual.py --token SEU_TOKEN
    python scripts/simulador_manual.py --token SEU_TOKEN --machine OUTRO-HOST
    python scripts/simulador_manual.py --token SEU_TOKEN --cafile host_cert.pem
"""
import argparse
import asyncio
import base64
import io
import socket
import sys
from pathlib import Path

import qrcode

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.operacao_assistida import SessaoOperador


def gerar_qr_base64(conteudo: str) -> str:
    img = qrcode.make(conteudo)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


async def ainput(prompt_text: str = "") -> str:
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt_text)


async def simular(machine: str, token: str, cafile: str | None, sistema: str):
    sessao = SessaoOperador(machine, token, cafile=cafile)

    print(f"\nConectando ao operador em {machine} ...")
    await ainput("Pressione Enter para iniciar a tarefa no operador...")

    await sessao.conectar(sistema, "Solicitação de login recebida. Preencha as credenciais.")
    print(f"Tarefa enviada (sistema={sistema}, task_id={sessao.task_id}). Aguardando credenciais...\n")

    tentativa = 1
    resultado = await sessao.solicitar_credenciais()
    print(f"  [tentativa {tentativa}] Credenciais: usuário={resultado['user']}")

    while True:
        await ainput("Pressione Enter para enviar QR Code...")
        qr_b64 = gerar_qr_base64(f"OTP:{sessao.task_id[:8].upper()}-T{tentativa}")
        await sessao.enviar_qr(qr_b64)
        print("QR Code enviado. Aguardando código...\n")

        codigo = await sessao.aguardar_codigo()
        print(f"  Código recebido: {codigo}\n")
        print("  [1] Sucesso")
        print("  [2] Erro de login (retry com mesmas credenciais)")
        print("  [3] Usuário e senha errados (volta do início)")
        print("  [4] Início de execução")
        print("  [5] Erro não esperado")
        escolha = (await ainput("> ")).strip()

        if escolha == "1":
            print("\nSucesso! Encerrando sessão...")
            break
        if escolha == "5":
            await sessao.notificar_erro_execucao("Falha inesperada no processo RPA.")
            print("Erro inesperado enviado. Encerrando sessão...")
            break
        if escolha == "2":
            tentativa += 1
            await sessao.notificar_login_error("Credenciais inválidas. Tente novamente.")
            print("Erro de login enviado.\n")
            continue
        if escolha == "3":
            tentativa += 1
            await sessao.notificar_credenciais_invalidas("Usuário ou senha incorretos. Insira novamente.")
            print("Erro de credenciais enviado. Aguardando novas credenciais...\n")
            resultado = await sessao.solicitar_credenciais()
            print(f"  [tentativa {tentativa}] Credenciais: usuário={resultado['user']}")
            continue
        if escolha == "4":
            await sessao.notificar_execucao_iniciada()
            print("Execução iniciada. Aguardando próxima ação...\n")
            while True:
                print("  [0] Sucesso e fim da sessão")
                print("  [6] Realizar validação do QR Code")
                sub = (await ainput("> ")).strip()
                if sub == "0":
                    print("\nSessão encerrada com sucesso.")
                    break
                if sub == "6":
                    qr_b64 = gerar_qr_base64(f"VALIDATE:{sessao.task_id[:8].upper()}")
                    await sessao.enviar_qr(qr_b64)
                    print("QR de validação enviado. Aguardando código...\n")
                    codigo = await sessao.aguardar_codigo()
                    print(f"  Código de validação: {codigo}\n")
            break

    await sessao.fechar()
    print("\n--- Resultado final ---")
    print(f"  Usuário    : {resultado.get('user', '-')}")
    print(f"  Senha      : {'*' * len(resultado.get('password', ''))}")
    print(f"  Tentativas : {tentativa}")
    print("-----------------------\n")


def main():
    parser = argparse.ArgumentParser(description="Simulador manual — dirige o protocolo do agente-bot contra um agente-operador real")
    parser.add_argument("--machine", default=socket.gethostname(), help="Nome/IP da máquina do operador")
    parser.add_argument("--token", required=True, help="Token de autenticação (ws_token.txt do operador)")
    parser.add_argument("--cafile", default=None, help="Caminho para host_cert.pem (pinning TLS; omitir = desabilitar verificação)")
    parser.add_argument("--sistema", default="analitico", help="Nome do sistema alvo (ex.: analitico)")
    args = parser.parse_args()
    asyncio.run(simular(args.machine, args.token, args.cafile, args.sistema))


if __name__ == "__main__":
    main()
