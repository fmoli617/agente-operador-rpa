"""
Simulador de processo RPA — testa o fluxo completo de login com o operador.

Uso:
    python examples/example.py --token SEU_TOKEN
    python examples/example.py --token SEU_TOKEN --machine OUTRO-HOST
    python examples/example.py --token SEU_TOKEN --cafile caminho/host_cert.pem
"""
import argparse
import asyncio
import base64
import io
import json
import socket
import ssl
import uuid

import qrcode
import websockets

DEFAULT_PORT = 8765


def gerar_qr_base64(conteudo: str) -> str:
    img = qrcode.make(conteudo)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


async def ainput(prompt_text="") -> str:
    return await asyncio.get_event_loop().run_in_executor(None, input, prompt_text)


def _build_ssl(cafile: str | None) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if cafile:
        ctx.load_verify_locations(cafile)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def simular_login(machine: str, token: str, cafile: str | None):
    uri = f"wss://{machine}:{DEFAULT_PORT}"
    task_id = str(uuid.uuid4())
    ssl_ctx = _build_ssl(cafile)

    print(f"\nConectando ao operador em {machine}:{DEFAULT_PORT} ...")
    await ainput("Pressione Enter para iniciar a tarefa no operador...")

    async with websockets.connect(uri, ssl=ssl_ctx) as ws:
        await ws.send(json.dumps({"type": "auth", "token": token}))

        await ws.send(json.dumps({
            "task_id": task_id,
            "host": "PRD-RPA-R00",
            "process": "RPA000_TESTE",
            "message": "Solicitação de login recebida. Preencha as credenciais.",
        }))
        print("Tarefa enviada. Aguardando credenciais do operador...\n")

        result = {}
        tentativa = 1

        async for raw in ws:
            data = json.loads(raw)
            if data.get("task_id") != task_id:
                continue

            rtype = data.get("type")

            if rtype == "credentials":
                result["user"] = data.get("user", "")
                result["password"] = data.get("password", "")
                print(f"  [tentativa {tentativa}] Credenciais: usuário={result['user']}")
                await ainput("Pressione Enter para enviar QR Code...")

                qr_b64 = gerar_qr_base64(f"OTP:{task_id[:8].upper()}-T{tentativa}")
                await ws.send(json.dumps({
                    "task_id": task_id,
                    "type": "qr_code",
                    "image": qr_b64,
                }))
                print("QR Code enviado. Aguardando código...\n")

            elif rtype == "code":
                result["code"] = data.get("code", "")
                print(f"  Código recebido: {result['code']}")
                print()
                print("  [1] Sucesso")
                print("  [2] Erro de login (retry com mesmas credenciais)")
                print("  [3] Usuário e senha errados (volta do início)")
                print("  [4] Início de execução")
                print("  [5] Erro não esperado")
                escolha = await ainput("> ")

                if escolha.strip() == "1":
                    print("\nSucesso! Encerrando sessão...")
                    break

                elif escolha.strip() == "5":
                    await ws.send(json.dumps({
                        "task_id": task_id,
                        "type": "execution_error",
                        "message": "Falha inesperada no processo RPA.",
                    }))
                    print("Erro inesperado enviado. Encerrando sessão...")
                    break

                elif escolha.strip() == "2":
                    tentativa += 1
                    await ws.send(json.dumps({
                        "task_id": task_id,
                        "type": "login_error",
                        "message": "Credenciais inválidas. Tente novamente.",
                    }))
                    print("Erro de login enviado.\n")

                elif escolha.strip() == "3":
                    tentativa += 1
                    await ws.send(json.dumps({
                        "task_id": task_id,
                        "type": "credentials_error",
                        "message": "Usuário ou senha incorretos. Insira novamente.",
                    }))
                    print("Erro de credenciais enviado.\n")

                elif escolha.strip() == "4":
                    await ws.send(json.dumps({
                        "task_id": task_id,
                        "type": "execution_started",
                        "message": "Processo em execução.",
                    }))
                    print("Execução iniciada. Aguardando próxima ação...\n")

                    while True:
                        print("  [0] Sucesso e fim da sessão")
                        print("  [6] Realizar validação do QR Code")
                        sub = await ainput("> ")

                        if sub.strip() == "0":
                            print("\nSessão encerrada com sucesso.")
                            break

                        elif sub.strip() == "6":
                            qr_b64 = gerar_qr_base64(f"VALIDATE:{task_id[:8].upper()}")
                            await ws.send(json.dumps({
                                "task_id": task_id,
                                "type": "qr_code",
                                "image": qr_b64,
                            }))
                            print("QR de validação enviado. Aguardando código...\n")
                            async for raw2 in ws:
                                d2 = json.loads(raw2)
                                if d2.get("task_id") == task_id and d2.get("type") == "code":
                                    result["code"] = d2.get("code", "")
                                    print(f"  Código de validação: {result['code']}\n")
                                    break

                    break

    print("\n--- Resultado final ---")
    print(f"  Usuário    : {result.get('user', '-')}")
    print(f"  Senha      : {'*' * len(result.get('password', ''))}")
    print(f"  Código     : {result.get('code', '-')}")
    print(f"  Tentativas : {tentativa}")
    print("-----------------------\n")


def main():
    parser = argparse.ArgumentParser(description="Simulador RPA — fluxo completo de login com o operador")
    parser.add_argument("--machine", default=socket.gethostname(), help="Nome/IP da máquina do operador")
    parser.add_argument("--token", required=True, help="Token de autenticação (ws_token.txt do operador)")
    parser.add_argument("--cafile", default=None, help="Caminho para host_cert.pem (pinning TLS; omitir = desabilitar verificação)")
    args = parser.parse_args()
    asyncio.run(simular_login(args.machine, args.token, args.cafile))


if __name__ == "__main__":
    main()
