"""
SDK do Consumidor — localiza e interage com o host do operador via WebSocket.

Descoberta: resolve wss://MAQUINA:8765 pelo nome do host, sem IP fixo.
Protocolo:
  Handshake: { "type": "auth", "token": "..." }  <- primeira mensagem obrigatória
  Envio:     { "task_id": "...", "host": "...", "process": "...", "message": "..." }
  Retorno:   { "task_id": "...", "type": "credentials", "user": "...", "password": "..." }
             { "task_id": "...", "type": "code", "code": "..." }
"""
import asyncio
import json
import ssl
import uuid

import websockets


DEFAULT_PORT = 8765


def _build_ssl_context(cafile: str | None) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if cafile:
        ctx.load_verify_locations(cafile)
    else:
        # certificado autoassinado do operador — desabilita verificação de CA em dev
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


class OperadorSDK:
    def __init__(self, machine: str, token: str, port: int = DEFAULT_PORT, cafile: str | None = None):
        """
        machine : nome ou IP da máquina do operador
        token   : token de autenticação (ws_token.txt do operador ou env OPERADOR_WS_TOKEN)
        port    : porta WebSocket (padrão 8765)
        cafile  : caminho para o .pem do host (pinning); None desabilita verificação de CA (dev)
        """
        self.uri = f"wss://{machine}:{port}"
        self.token = token
        self._ssl = _build_ssl_context(cafile)

    async def solicitar_login(
        self,
        host: str,
        process: str,
        message: str = "Solicitação de login",
        timeout: float = 120.0,
    ) -> dict:
        """
        Envia uma solicitação de login e aguarda as respostas do operador.
        Retorna dict com 'user', 'password' e opcionalmente 'code'.
        """
        task_id = str(uuid.uuid4())
        result = {}

        async with websockets.connect(self.uri, ssl=self._ssl) as ws:
            await ws.send(json.dumps({"type": "auth", "token": self.token}))

            await ws.send(json.dumps({
                "task_id": task_id,
                "host": host,
                "process": process,
                "message": message,
            }))

            async def _listen():
                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("task_id") != task_id:
                        continue
                    rtype = data.get("type")
                    if rtype == "credentials":
                        result["user"] = data.get("user", "")
                        result["password"] = data.get("password", "")
                    elif rtype == "code":
                        result["code"] = data.get("code", "")
                        return

            await asyncio.wait_for(_listen(), timeout=timeout)

        return result

    def solicitar_login_sync(
        self,
        host: str,
        process: str,
        message: str = "Solicitação de login",
        timeout: float = 120.0,
    ) -> dict:
        """Versão síncrona para uso em scripts/RPA sem async."""
        return asyncio.run(self.solicitar_login(host, process, message, timeout))
