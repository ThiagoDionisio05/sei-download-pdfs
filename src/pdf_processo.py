"""Baixa o PDF completo de um processo SEI que já está aberto na tela."""

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from . import config
from .sei_page import clicar_por_texto, clicar_por_titulo, screenshot
from .status_pdf import registrar_falha, registrar_pdf_baixado, verificar_pdf_valido


class BotaoNaoEncontrado(Exception):
    pass


def baixar_pdf_processo(page: Page, numero_processo: str) -> bool:
    """Assume que o processo `numero_processo` já está aberto na tela.

    Clica em "Gerar Arquivo PDF do Processo" -> confirma "Todos os
    documentos disponíveis" -> "Gerar", captura o download, valida o
    arquivo e registra o resultado (sucesso ou falha).

    Retorna True se confirmou um PDF válido baixado.
    """
    config.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    nome_arquivo = numero_processo.replace("/", "-") + ".pdf"
    caminho_pdf = config.DOWNLOADS_DIR / nome_arquivo

    # 1. Clica no ícone — só abre o painel de opções, ainda não baixa nada.
    if not clicar_por_titulo(page, "Gerar Arquivo PDF do Processo"):
        registrar_falha(
            numero_processo, "botão 'Gerar Arquivo PDF do Processo' não encontrado"
        )
        return False

    page.wait_for_timeout(1000)

    # 2. Garante "Todos os documentos disponíveis" e clica em "Gerar" —
    # esse clique é que dispara o download de fato.
    try:
        with page.expect_download(timeout=config.TIMEOUT_PADRAO_MS) as download_info:
            clicar_por_texto(page, "Todos os documentos disponíveis", exact=False)
            if not clicar_por_texto(page, "Gerar", exact=True):
                raise BotaoNaoEncontrado()
        download = download_info.value
    except BotaoNaoEncontrado:
        registrar_falha(numero_processo, "botão 'Gerar' não encontrado no painel de PDF")
        return False
    except PlaywrightTimeoutError:
        screenshot(page, f"sem_download_{numero_processo.replace('/', '-')}")
        registrar_falha(numero_processo, "download não iniciou dentro do tempo esperado")
        return False

    download.save_as(str(caminho_pdf))

    if verificar_pdf_valido(caminho_pdf):
        registrar_pdf_baixado(numero_processo, caminho_pdf)
        return True

    registrar_falha(numero_processo, "arquivo baixado não é um PDF válido")
    return False
