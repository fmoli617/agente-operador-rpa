"""
Ponte síncrona entre o pipeline RPA (Selenium, síncrono) e a SessaoOperador
(WebSocket, assíncrona) — cada instância de CredenciaisAcesso é escopada a
uma única tarefa/sistema.

A conexão WebSocket vive presa a um único event loop, então essa ponte roda
um loop dedicado em background (mesmo padrão usado em
agente-operador/service/host.py) em vez de asyncio.run() por chamada — um
novo loop a cada chamada quebraria o websocket criado no loop anterior.

"""
import asyncio
import threading

from services.operacao_assistida import SessaoOperador


class CredenciaisAcesso:

    def __init__(self, sessao: SessaoOperador, sistema: str):
        self._sessao = sessao
        self._sistema = sistema
        self._credenciais: dict | None = None
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def _run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def iniciar(self) -> None:
        self._run(self._sessao.conectar(self._sistema))

    def _garantir_credenciais(self) -> dict:
        if self._credenciais is None:
            self._credenciais = self._run(self._sessao.solicitar_credenciais())
        return self._credenciais

    def solicitar_usuario_assistido(self) -> str:
        return self._garantir_credenciais()["user"]

    def solicitar_senha_assistido(self) -> str:
        return self._garantir_credenciais()["password"]

    def solicitar_resolucao_mfa(self, qrcode_64bits: str) -> str:
        """Envia o QR Code capturado do site ao operador e aguarda o código digitado."""
        self._run(self._sessao.enviar_qr(qrcode_64bits))
        return self._run(self._sessao.aguardar_codigo())

    def notificar_credenciais_invalidas(self, mensagem: str = "Usuário ou senha incorretos.") -> None:
        self._credenciais = None
        self._run(self._sessao.notificar_credenciais_invalidas(mensagem))

    def notificar_execucao_iniciada(self) -> None:
        self._run(self._sessao.notificar_execucao_iniciada())

    def notificar_erro_execucao(self, mensagem: str) -> None:
        self._run(self._sessao.notificar_erro_execucao(mensagem))

    def finalizar(self) -> None:
        self._run(self._sessao.fechar())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
        self._loop.close()
