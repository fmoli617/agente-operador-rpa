"""
Integração real agente-bot <-> agente-operador: o cliente `SessaoOperador`
(agente-bot/src/services/operacao_assistida.py) fala com o host real do
agente-operador (`service.host.start_host`). A resposta do operador humano
(preencher credenciais / digitar código) é simulada chamando diretamente
`WebSocketTaskResponder`, que é a mesma implementação que a UI do operador
usa por trás do popup — não um dublê do protocolo.
"""
import asyncio

import pytest

from service import host as host_module
from service import security

from app.fila import Fila
from services.operacao_assistida import SessaoOperador


def _client(port: int, token: str | None = None) -> SessaoOperador:
    return SessaoOperador("127.0.0.1", token or security.get_auth_token(), port, cafile=None)


async def test_fluxo_completo_uma_tarefa(running_host):
    bridge, port = running_host
    sessao = _client(port)

    await sessao.conectar("analitico")
    await asyncio.sleep(0.2)
    assert bridge.show_notification.received == [("analitico - analitico", "Solicitação de login recebida.", sessao.task_id, "analitico")]

    responder = host_module.WebSocketTaskResponder()
    responder.send_credentials(sessao.task_id, "usuario1", "senha1")
    credenciais = await sessao.solicitar_credenciais(timeout=3)
    assert credenciais == {"user": "usuario1", "password": "senha1"}

    await sessao.enviar_qr("QR-BASE64")
    await asyncio.sleep(0.2)
    assert bridge.show_qr_code.received == [(sessao.task_id, "QR-BASE64")]

    responder.send_code(sessao.task_id, "654321")
    codigo = await sessao.aguardar_codigo(timeout=3)
    assert codigo == "654321"

    await sessao.notificar_execucao_iniciada()
    await asyncio.sleep(0.2)
    assert bridge.execution_started.received == [(sessao.task_id,)]

    await sessao.fechar()


async def test_multiplas_tarefas_simultaneas_nao_se_misturam(running_host):
    """Duas tarefas concorrentes (dois SessaoOperador) devem receber cada uma sua própria credencial."""
    bridge, port = running_host
    sessao_a = _client(port)
    sessao_b = _client(port)

    await sessao_a.conectar("analitico")
    await sessao_b.conectar("outro_sistema")
    await asyncio.sleep(0.2)

    responder = host_module.WebSocketTaskResponder()
    responder.send_credentials(sessao_b.task_id, "user-b", "pass-b")
    responder.send_credentials(sessao_a.task_id, "user-a", "pass-a")

    cred_a, cred_b = await asyncio.gather(
        sessao_a.solicitar_credenciais(timeout=3),
        sessao_b.solicitar_credenciais(timeout=3),
    )
    assert cred_a == {"user": "user-a", "password": "pass-a"}
    assert cred_b == {"user": "user-b", "password": "pass-b"}

    await sessao_a.fechar()
    await sessao_b.fechar()


async def test_multiplas_contas_da_base_db_nao_se_misturam(running_host):
    """
    A fila real do agente-bot (app.fila.Fila) é montada a partir de db/usuarios.db —
    cada conta ativa vira uma tarefa. Aqui abrimos uma sessão por conta ativa da
    fila (simulando N execuções concorrentes do orquestrador) e conferimos que
    nenhuma credencial vaza para o task_id errado.
    """
    bridge, port = running_host
    fila = Fila()
    solicitacoes = []
    while not fila.esta_vazia():
        solicitacoes.append(fila.proximo())
    assert len(solicitacoes) >= 2, "seed de db/usuarios.db precisa de pelo menos 2 contas ativas"

    sessoes = [_client(port) for _ in solicitacoes]
    await asyncio.gather(*(s.conectar(sol.sistema) for s, sol in zip(sessoes, solicitacoes)))
    await asyncio.sleep(0.2)

    responder = host_module.WebSocketTaskResponder()
    for i, sessao in enumerate(sessoes):
        responder.send_credentials(sessao.task_id, f"user-{i}", f"pass-{i}")

    resultados = await asyncio.gather(*(s.solicitar_credenciais(timeout=3) for s in sessoes))
    for i, cred in enumerate(resultados):
        assert cred == {"user": f"user-{i}", "password": f"pass-{i}"}

    await asyncio.gather(*(s.fechar() for s in sessoes))


async def test_token_invalido_e_recusado(running_host):
    _, port = running_host
    sessao = _client(port, token="token-errado")
    await sessao.conectar("analitico")
    with pytest.raises(Exception):
        await sessao.solicitar_credenciais(timeout=2)
    await sessao.fechar()
