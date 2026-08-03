"""
Sessão pai + N sessões filhas para https://authenticationtest.com/totpChallenge/.

A sessão pai roda em background (headless), faz login completo (usuário/senha
assistidos + QR/MFA via agente-operador — nunca reaproveitado, sempre pedido
de novo) e, uma vez autenticada, expõe os cookies de sessão. As sessões
filhas abrem navegadores visíveis, aplicam esses cookies (sem repetir
login/MFA) e são posicionadas lado a lado, divididas em partes iguais no
monitor principal.

Seletores validados contra a página real em 03/08/2026 (curl direto, sem JS):
- #email, #password, #totpmfa, img[alt="TOTP Seed QR Code"],
  input[value="Log In"] — a "Success!" (div.alert-success) só existe na
  resposta do POST do formulário (servidor), não aparece na página inicial.

IMPORTANTE — limite conhecido deste site de demo (não do código): authenticationtest.com
não implementa sessão autenticada real por cookie nessas rotas. Confirmado em teste:
/loginSuccess/ mostra "Success!" mesmo sem cookie nenhum; /totpChallenge/ sempre volta a
mostrar o formulário em branco mesmo com cookie válido pós-login; o PHPSESSID é emitido
só de visitar a página, antes de qualquer login, e não muda com autenticação. Ou seja: o
transplante de cookie para as sessões filhas (abrir_sessoes_filhas) é tecnicamente
correto — o valor do cookie é replicado fielmente — mas este site não tem como confirmar
que isso representa uma sessão autenticada de verdade, porque ele nunca checa isso. Serve
como prova do mecanismo (cópia de cookies + tiling), não como prova de reuso de sessão
autenticada — isso só será validável contra um sistema real com sessão de fato gated por
cookie (ver doc_version.md).
"""
import base64
import ctypes

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from data.credenciais import CredenciaisAcesso
from services.chrome import criar_driver

URL = "https://authenticationtest.com/totpChallenge/"
# Depois do login, o site navega pra cá — é a única URL que checa a sessão;
# /totpChallenge/ sempre renderiza o formulário do zero, mesmo com cookie
# válido (confirmado em teste: reload em /totpChallenge/ nunca reflete
# sessão autenticada). Ver doc_version.md, seção sobre multi_sessao.py.
URL_LOGADO = "https://authenticationtest.com/loginSuccess/"

EMAIL_INPUT = "#email"
SENHA_INPUT = "#password"
MFA_INPUT = "#totpmfa"
QR_IMG = "img[alt='TOTP Seed QR Code']"
LOGIN_BTN = "input[value='Log In']"
SUCESSO = "div.alert-success"

COOKIE_CAMPOS_VALIDOS = {"name", "value", "domain", "path", "secure", "expiry"}


def _esperar(driver, selector: str, timeout: float):
    """find_element direto falhou de forma intermitente em teste real (possível hiccup de
    render/rede da página remota) — todo acesso a elemento passa a esperar explicitamente."""
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))


def _capturar_qr_base64(driver, timeout: float, tentativas: int = 3) -> str:
    """
    Captura do QR se mostrou instável em teste real contra o site (elemento 'stale' entre
    localizar e tirar o screenshot; em outra rodada, timeout puro sem o elemento aparecer —
    não reproduzido de forma isolada com a mesma sequência, indício de instabilidade externa
    do site/CDN sob requisições repetidas, não um bug determinístico daqui). Tenta de novo
    relocalizando o elemento do zero. Não recarrega a página aqui de propósito — um refresh
    apagaria usuário/senha já preenchidos pelo chamador.
    """
    ultimo_erro = None
    for _ in range(tentativas):
        try:
            qr_element = _esperar(driver, QR_IMG, timeout)
            return base64.b64encode(qr_element.screenshot_as_png).decode("ascii")
        except (StaleElementReferenceException, TimeoutException) as exc:
            ultimo_erro = exc
    raise ultimo_erro


def _tamanho_tela() -> tuple[int, int]:
    """Resolução do monitor principal — usada só pra tilear as janelas filhas."""
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


def abrir_sessao_pai(credenciais: CredenciaisAcesso, timeout: float = 20.0):
    """
    Login completo em background: usuário/senha assistidos pelo operador,
    QR capturado da página e enviado ao operador, código de volta preenchido.
    Retorna (driver, cookies) já autenticados — driver fica aberto (headless).
    """
    driver = criar_driver(headless=True)
    driver.get(URL)

    usuario = credenciais.solicitar_usuario_assistido()
    senha = credenciais.solicitar_senha_assistido()
    _esperar(driver, EMAIL_INPUT, timeout).send_keys(usuario)
    _esperar(driver, SENHA_INPUT, timeout).send_keys(senha)

    qr_b64 = _capturar_qr_base64(driver, timeout)
    codigo = credenciais.solicitar_resolucao_mfa(qr_b64)
    _esperar(driver, MFA_INPUT, timeout).send_keys(codigo)

    _esperar(driver, LOGIN_BTN, timeout).click()
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, SUCESSO)))
    credenciais.notificar_execucao_iniciada()

    return driver, driver.get_cookies()


def abrir_sessoes_filhas(cookies: list[dict], quantidade: int = 4) -> list:
    """
    Abre `quantidade` navegadores visíveis reaproveitando os cookies da
    sessão pai (sem login/MFA de novo), tileados em partes iguais no monitor
    principal (grade 2 colunas x N linhas).

    Nota: contra authenticationtest.com, checar `div.alert-success` na página resultante
    NÃO prova reuso de sessão — essa página mostra "Success!" mesmo sem cookie nenhum (ver
    docstring do módulo). O que é verificável aqui é só a cópia do cookie em si.
    """
    largura_tela, altura_tela = _tamanho_tela()
    colunas = 2
    linhas = (quantidade + colunas - 1) // colunas
    largura_janela = largura_tela // colunas
    altura_janela = altura_tela // linhas

    sessoes = []
    for i in range(quantidade):
        driver = criar_driver(headless=False, maximizado=False)
        driver.get(URL)  # precisa estar no domínio antes de aplicar os cookies
        for cookie in cookies:
            limpo = {k: v for k, v in cookie.items() if k in COOKIE_CAMPOS_VALIDOS}
            try:
                driver.add_cookie(limpo)
            except Exception:
                continue
        driver.get(URL_LOGADO)  # única URL que reflete a sessão autenticada

        col, lin = i % colunas, i // colunas
        driver.set_window_rect(col * largura_janela, lin * altura_janela, largura_janela, altura_janela)
        sessoes.append(driver)

    return sessoes


def encerrar_todas(sessoes: list) -> None:
    for driver in sessoes:
        try:
            driver.quit()
        except Exception:
            pass


def executar_fluxo_pai_filhas(credenciais: CredenciaisAcesso, quantidade_filhas: int = 4) -> tuple:
    """Orquestra o fluxo completo: sessão pai (login+MFA) -> N sessões filhas tileadas."""
    driver_pai, cookies = abrir_sessao_pai(credenciais)
    filhas = abrir_sessoes_filhas(cookies, quantidade_filhas)
    return driver_pai, filhas
