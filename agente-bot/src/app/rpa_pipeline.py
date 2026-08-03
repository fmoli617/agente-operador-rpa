"""
Executa uma SolicitacaoRelatorio de ponta a ponta: login (usuário/senha + QR/MFA
assistidos pelo agente-operador) via services/multi_sessao.py, depois dispara o
download do relatório.

Alvo de teste local do MFA: https://authenticationtest.com/totpChallenge/
(QR + campo de código — substitui o site real da automação, que roda em
outra máquina, enquanto validamos o fluxo bot<->operador aqui). Seletores e
lógica de login validados contra a página real em services/multi_sessao.py —
não duplicados aqui de propósito.
"""
from data.analitico import SolicitacaoRelatorio
from data.credenciais import CredenciaisAcesso
from services.multi_sessao import abrir_sessao_pai
from services.operacao_assistida import SessaoOperador


def executar_pipeline(
    solicitacao: SolicitacaoRelatorio,
    machine: str,
    token: str,
    port: int,
    cafile: str | None = None,
) -> None:
    sessao = SessaoOperador(machine, token, port, cafile)
    credenciais = CredenciaisAcesso(sessao, solicitacao.sistema)
    credenciais.iniciar()
    driver = None
    try:
        driver, _cookies = abrir_sessao_pai(credenciais)
        _baixar_relatorio(driver, solicitacao)
    except Exception as exc:
        credenciais.notificar_erro_execucao(str(exc))
        raise
    finally:
        if driver is not None:
            driver.quit()
        credenciais.finalizar()


def _baixar_relatorio(driver, solicitacao: SolicitacaoRelatorio) -> None:
    """TODO: implementar a navegação/download real do relatório por sistema."""
    raise NotImplementedError(f"download de '{solicitacao.relatorio}' ainda não implementado")
