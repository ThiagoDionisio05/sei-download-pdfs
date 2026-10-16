"""Helpers para localizar elementos na estrutura de frames do SEI."""

import re
from pathlib import Path

from playwright.sync_api import Page

from . import config

NUMERO_PROCESSO_RE = re.compile(r"\d{5}\.\d{6}/\d{4}-\d{2}")


def localizar_campo_pesquisa(page: Page, timeout_ms: int = 5000):
    """Procura o campo de pesquisa (placeholder "Pesquisar...") em todos os
    frames da página — o SEI costuma colocar a barra de topo num frame
    separado do conteúdo principal, então não dá pra assumir que está na
    página principal.

    Faz polling em vez de checar uma única vez: a página pode ainda estar
    carregando logo depois de voltar pra "Controle de Processos", e uma
    checagem instantânea às vezes falha por pura demora de rede, não por o
    campo realmente não existir.
    """
    tentativas = max(1, timeout_ms // 300)
    for _ in range(tentativas):
        for fr in page.frames:
            candidatos = [
                fr.get_by_placeholder("Pesquisar", exact=False),
                fr.locator("input[placeholder*='Pesquisar' i]"),
            ]
            for loc in candidatos:
                try:
                    if loc.count() > 0 and loc.first.is_visible():
                        return loc.first
                except Exception:
                    continue
        page.wait_for_timeout(300)
    return None


def clicar_por_titulo(page: Page, texto: str) -> bool:
    """Clica no primeiro elemento visível, em qualquer frame da página, cujo
    atributo title/aria-label contenha `texto` (comparação parcial, sem
    diferenciar maiúsculas/minúsculas).

    Usado pra botões de ícone do SEI (ex.: "Gerar Arquivo PDF do Processo"),
    que não têm texto visível — só tooltip. Retorna True se conseguiu clicar.
    """
    for fr in page.frames:
        candidatos = [
            fr.locator(f"[title*='{texto}' i]"),
            fr.locator(f"[aria-label*='{texto}' i]"),
        ]
        for loc in candidatos:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    return True
            except Exception:
                continue
    return False


def clicar_por_texto(page: Page, texto: str, exact: bool = True) -> bool:
    """Clica no primeiro elemento visível, em qualquer frame, cujo texto
    bata com `texto` (usado pra botões/rótulos comuns do SEI, como 'Gerar'
    ou o rótulo de um radio button)."""
    for fr in page.frames:
        candidatos = [
            fr.get_by_role("button", name=texto, exact=exact),
            fr.get_by_text(texto, exact=exact),
        ]
        for loc in candidatos:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    return True
            except Exception:
                continue
    return False


def clicar_por_texto_ou_icone(page: Page, texto: str) -> bool:
    """Clica em um item de menu/ícone localizando-o pelo texto visível ou,
    se não achar, pelo ícone associado (img/title/aria-label com o mesmo
    texto). Procura em todos os frames — mesma lógica usada em
    sei-automacao para navegar entre telas do SEI (ex.: "Controle de
    Processos"). Retorna True se conseguiu clicar.
    """
    for fr in page.frames:
        candidatos = [
            fr.get_by_text(texto, exact=True),
            fr.locator(f"a:has-text('{texto}')"),
            fr.locator(f"img[alt='{texto}'], img[title='{texto}']"),
            fr.locator(f"[title='{texto}']"),
            fr.get_by_text(texto, exact=False),
            fr.locator(f"[title*='{texto}' i]"),
            fr.locator(f"[aria-label*='{texto}' i]"),
            fr.locator(f"img[alt*='{texto}' i]"),
        ]
        for loc in candidatos:
            try:
                if loc.count() > 0 and loc.first.is_visible():
                    loc.first.click()
                    return True
            except Exception:
                continue
    return False


def pesquisar_processo(page: Page, numero_processo: str) -> None:
    """Digita o número do processo no campo de pesquisa do topo e confirma
    com Enter. Assume que a tela atual é a de Controle de Processos (ou
    qualquer tela com a barra de pesquisa visível)."""
    campo = localizar_campo_pesquisa(page)
    if campo is None:
        raise RuntimeError(
            "Não encontrei o campo de pesquisa (placeholder 'Pesquisar...') "
            "em nenhum frame da página."
        )
    campo.click()
    campo.fill(numero_processo)
    page.wait_for_timeout(500)  # dá tempo de um dropdown de sugestão aparecer, se existir

    # Fecha uma eventual lista de sugestões/autocomplete que tenha aberto —
    # sem isso, Enter às vezes seleciona o item sugerido (ex.: uma busca
    # anterior) em vez de submeter o texto que acabamos de digitar. Já
    # causou processos errados sendo baixados. Escape pode reverter o campo
    # pro valor anterior nalguns widgets, então confere e reescreve se preciso.
    # Mesmo assim isso não é 100% garantido (ver `numero_ja_usado_por_outro`,
    # a segunda camada de segurança que pega o caso residual).
    campo.press("Escape")
    page.wait_for_timeout(150)
    if campo.input_value() != numero_processo:
        campo.fill(numero_processo)
        page.wait_for_timeout(150)

    campo.press("Enter")
    page.wait_for_timeout(2000)  # espera o processo abrir


def protocolo_encontrado(page: Page) -> bool:
    """Distingue se o SEI abriu o processo/documento DIRETO (busca rápida
    achou um match exato) ou caiu na tela de busca avançada "Pesquisa" (com
    o campo "Texto para Pesquisa" visível).

    Importante: cair na tela de busca avançada NÃO significa necessariamente
    "não encontrado" — essa mesma tela aparece tanto com zero quanto com
    vários resultados (rolando a página pra baixo). Use
    `contar_resultados_pesquisa` e `encontrar_processo_tipo_aceito_na_pesquisa`
    pra tratar o caso em que esta função retorna False.
    """
    for fr in page.frames:
        try:
            if fr.get_by_text("Texto para Pesquisa", exact=False).first.is_visible():
                return False
        except Exception:
            continue
    return True


RESULTADO_COUNT_RE = re.compile(r"(\d+)\s+resultados?", re.IGNORECASE)


def contar_resultados_pesquisa(page: Page) -> int:
    """Lê o contador "N resultados" da tela de busca avançada. Retorna 0 se
    não achar o contador (trata como nenhum resultado)."""
    for fr in page.frames:
        try:
            texto = fr.locator("body").inner_text()
        except Exception:
            continue
        m = RESULTADO_COUNT_RE.search(texto)
        if m:
            return int(m.group(1))
    return 0


def encontrar_processo_tipo_aceito_na_pesquisa(page: Page, tipos_aceitos) -> tuple[str, str] | None:
    """Na tela de busca avançada (com um ou mais resultados listados),
    procura um resultado cujo título comece com um dos `tipos_aceitos`
    (strings em minúsculas, comparação por trecho contido) e retorna
    (tipo_encontrado, numero_processo) do primeiro que achar.

    A busca avançada por protocolo pode trazer processos de vários tipos
    (ex.: "Gestão e Controle: Demandas..." e "Pessoal: Ressarcimento ao
    Erário" misturados) — cada resultado mostra o tipo e o número do
    processo na mesma linha de título, ex.: "Pessoal: Ressarcimento ao
    Erário Nº 00000.000000/0000-00". Retorna None se nenhum resultado bater
    com os tipos aceitos.
    """
    texto_completo = ""
    for fr in page.frames:
        try:
            texto_completo += "\n" + fr.locator("body").inner_text()
        except Exception:
            continue

    texto_lower = texto_completo.lower()
    for tipo_aceito in tipos_aceitos:
        idx = texto_lower.find(tipo_aceito)
        while idx != -1:
            trecho = texto_completo[idx : idx + len(tipo_aceito) + 60]
            match = NUMERO_PROCESSO_RE.search(trecho)
            if match:
                return tipo_aceito, match.group(0)
            idx = texto_lower.find(tipo_aceito, idx + 1)
    return None


def ler_numero_e_tipo_processo(page: Page) -> tuple[str | None, str | None]:
    """Lê o número do processo e o tipo (tooltip/atributo title) do
    elemento do número do processo no topo da árvore — só existe quando a
    busca abriu um processo de verdade.
    """
    for fr in page.frames:
        for tag in ("a", "span", "div"):
            try:
                candidatos = fr.locator(tag).filter(has_text=NUMERO_PROCESSO_RE)
                total = candidatos.count()
            except Exception:
                continue
            for i in range(min(total, 15)):
                el = candidatos.nth(i)
                try:
                    if not el.is_visible():
                        continue
                    texto = el.inner_text()
                except Exception:
                    continue
                match = NUMERO_PROCESSO_RE.search(texto or "")
                if not match:
                    continue
                numero = match.group(0)
                tipo = ""
                try:
                    tipo = el.get_attribute("title") or ""
                except Exception:
                    tipo = ""
                if not tipo:
                    try:
                        tipo = el.locator("xpath=..").get_attribute("title") or ""
                    except Exception:
                        tipo = ""
                return numero, (tipo or None)
    return None, None


def clicar_numero_processo_no_topo(page: Page) -> bool:
    """Clica no número do processo no topo da árvore (mesmo elemento lido
    por `ler_numero_e_tipo_processo`) — necessário pra trocar o painel
    principal pro contexto do processo (com os ícones de Gerar PDF/zip/
    etc.). Uma busca por Protocolo abre direto num documento específico da
    árvore, não no processo em si, e nesse contexto o ícone de PDF do
    processo não aparece.
    """
    for fr in page.frames:
        for tag in ("a", "span", "div"):
            try:
                candidatos = fr.locator(tag).filter(has_text=NUMERO_PROCESSO_RE)
                total = candidatos.count()
            except Exception:
                continue
            for i in range(min(total, 15)):
                el = candidatos.nth(i)
                try:
                    if not el.is_visible():
                        continue
                    texto = el.inner_text()
                except Exception:
                    continue
                if not NUMERO_PROCESSO_RE.search(texto or ""):
                    continue
                try:
                    el.click()
                    return True
                except Exception:
                    continue
    return False


def sair_do_processo(page: Page, timeout_ms: int = 5000) -> None:
    """Clica no menu "Controle de Processos" pra sair da tela do processo
    atual e voltar pra lista — chamado depois de cada protocolo, antes de
    pesquisar o próximo. Tenta algumas vezes: a página pode ainda estar
    carregando logo depois de uma ação anterior (download, navegação)."""
    tentativas = max(1, timeout_ms // 400)
    for _ in range(tentativas):
        if clicar_por_texto_ou_icone(page, "Controle de Processos"):
            page.wait_for_timeout(1000)
            return
        page.wait_for_timeout(400)

    raise RuntimeError(
        "Não encontrei o menu 'Controle de Processos' pra voltar à tela inicial."
    )


def screenshot(page: Page, nome: str) -> Path:
    """Salva um screenshot de página inteira em screenshots/<nome>.png —
    usado pra registrar/depurar cada etapa sem depender de olhar a tela ao
    vivo no momento exato em que a automação roda."""
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = config.SCREENSHOTS_DIR / f"{nome}.png"
    page.screenshot(path=str(caminho), full_page=True)
    return caminho
