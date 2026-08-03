"""
Cliente WebSocket do agente-bot para o agente-operador — mesmo protocolo de
agente-bot/versao-antiga/docs/PROTOCOLO.md, adaptado para o conceito de
"sistema" (ex.: analitico) usado hoje em src/data/.

Uma SessaoOperador cobre uma tarefa (task_id) do início ao fim:
  conectar -> solicitar_credenciais -> [Selenium loga no sistema] ->
  enviar_qr -> aguardar_codigo -> [Selenium confirma MFA] ->
  notificar_execucao_iniciada -> fechar
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


class SessaoOperador:
    """Uma conexão WebSocket autenticada, escopada a uma única tarefa (task_id)."""

    def __init__(self, machine: str, token: str, port: int = DEFAULT_PORT, cafile: str | None = None):
        self.uri = f"wss://{machine}:{port}"
        self.token = token
        self.task_id = str(uuid.uuid4())
        self._ssl = _build_ssl_context(cafile)
        self._ws = None

    async def conectar(self, sistema: str, message: str = "Solicitação de login recebida.") -> None:
        self._ws = await websockets.connect(self.uri, ssl=self._ssl)
        await self._ws.send(json.dumps({"type": "auth", "token": self.token}))
        await self._ws.send(json.dumps({
            "task_id": self.task_id,
            "host": sistema,
            "process": sistema,
            "message": message,
        }))

    async def _aguardar(self, tipos: set[str], timeout: float) -> dict:
        async def _listen():
            async for raw in self._ws:
                data = json.loads(raw)
                if data.get("task_id") != self.task_id:
                    continue
                if data.get("type") in tipos:
                    return data
        return await asyncio.wait_for(_listen(), timeout=timeout)

    async def solicitar_credenciais(self, timeout: float = 120.0) -> dict:
        """Aguarda o operador preencher e enviar usuário/senha para esta tarefa."""
        data = await self._aguardar({"credentials"}, timeout)
        return {"user": data.get("user", ""), "password": data.get("password", "")}

    async def enviar_qr(self, image_b64: str) -> None:
        await self._ws.send(json.dumps({
            "task_id": self.task_id,
            "type": "qr_code",
            "image": image_b64,
        }))

    async def aguardar_codigo(self, timeout: float = 120.0) -> str:
        data = await self._aguardar({"code"}, timeout)
        return data.get("code", "")

    async def notificar_login_error(self, message: str) -> None:
        await self._ws.send(json.dumps({"task_id": self.task_id, "type": "login_error", "message": message}))

    async def notificar_credenciais_invalidas(self, message: str) -> None:
        await self._ws.send(json.dumps({"task_id": self.task_id, "type": "credentials_error", "message": message}))

    async def notificar_execucao_iniciada(self) -> None:
        await self._ws.send(json.dumps({"task_id": self.task_id, "type": "execution_started"}))

    async def notificar_erro_execucao(self, message: str) -> None:
        await self._ws.send(json.dumps({"task_id": self.task_id, "type": "execution_error", "message": message}))

    async def fechar(self) -> None:
        if self._ws is not None:
            await self._ws.close()
