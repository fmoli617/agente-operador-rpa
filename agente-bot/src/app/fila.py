"""
Fila de solicitações a processar nesta execução do bot.

Fonte de dados: db/usuarios.db (base de contas de automação vinculadas ao
orquestrador — ver db/schema.sql) quando existir; senão cai no mock local de
data/analitico.py. Isso é o que permite que múltiplas contas do mesmo
sistema (analitico) — ou de sistemas diferentes — virem tarefas distintas
nesta fila, em vez de um único item fixo.
"""
from collections import deque

from data.analitico import SolicitacaoRelatorio, carregar_fila
from data.usuarios import UsuarioAutomacao, carregar_usuarios_ativos

URL_LOGIN_POR_SISTEMA = {
    "analitico": "https://authenticationtest.com/totpChallenge/",
}


def _fila_a_partir_da_base(usuarios: list[UsuarioAutomacao]) -> list[SolicitacaoRelatorio]:
    return [
        SolicitacaoRelatorio(
            sistema=usuario.sistema,
            url_login=URL_LOGIN_POR_SISTEMA.get(usuario.sistema, "https://authenticationtest.com/totpChallenge/"),
            relatorio=f"relatorio-{usuario.nome}",
        )
        for usuario in usuarios
    ]


class Fila:
    def __init__(self):
        usuarios = carregar_usuarios_ativos()
        itens = _fila_a_partir_da_base(usuarios) if usuarios else carregar_fila()
        self._itens: deque[SolicitacaoRelatorio] = deque(itens)

    def esta_vazia(self) -> bool:
        return not self._itens

    def proximo(self) -> SolicitacaoRelatorio:
        return self._itens.popleft()
