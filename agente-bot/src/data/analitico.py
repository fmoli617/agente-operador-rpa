"""
Dados de uma solicitação de relatório do sistema "analitico" — hoje é a
única fonte de tarefas do bot. A integração real com o orquestrador (outra
máquina) ainda não existe; carregar_fila() é um mock local para validar o
pipeline ponta a ponta (ver doc_version.md, seção 2.1).
"""
from dataclasses import dataclass


@dataclass
class SolicitacaoRelatorio:
    sistema: str      # nome do sistema alvo (ex.: "analitico") — vira host/process no protocolo
    url_login: str     # página onde o login + MFA acontecem
    relatorio: str      # identificador do relatório a baixar


def carregar_fila() -> list[SolicitacaoRelatorio]:
    """TODO: substituir pela leitura real da fila do orquestrador."""
    return [
        SolicitacaoRelatorio(
            sistema="analitico",
            url_login="https://authenticationtest.com/totpChallenge/",
            relatorio="relatorio-teste",
        ),
    ]
