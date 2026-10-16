"""Processa um Protocolo: pesquisa no SEI, classifica pelo tipo do processo,
e baixa o PDF completo quando o tipo bate com um dos aceitos.
"""

from playwright.sync_api import Page

from .pdf_processo import baixar_pdf_processo
from .sei_page import (
    clicar_numero_processo_no_topo,
    contar_resultados_pesquisa,
    encontrar_processo_tipo_aceito_na_pesquisa,
    ler_numero_e_tipo_processo,
    pesquisar_processo,
    protocolo_encontrado,
)
from .status_protocolo import numero_ja_usado_por_outro, registrar_resultado

# Comparação por trecho contido, normalizado (minúsculas, sem espaços nas
# pontas) — não precisa bater caractere a caractere com o tooltip do SEI.
TIPOS_ACEITOS = (
    "pessoal: ressarcimento ao erário",
    "pessoal: saúde - ressarcimento ao erário",
)


def processar_protocolo(page: Page, protocolo: str) -> None:
    pesquisar_processo(page, protocolo)

    if protocolo_encontrado(page):
        # Busca rápida abriu o processo/documento direto.
        numero, tipo = ler_numero_e_tipo_processo(page)
        if not numero:
            registrar_resultado(
                protocolo,
                "falha",
                "erro: não consegui ler o número do processo",
                detalhe="elemento do número do processo não encontrado na tela",
            )
            return
        _classificar_e_baixar(page, protocolo, numero, tipo)
        return

    # Não abriu direto — caiu na tela de busca avançada "Pesquisa", que pode
    # ter zero resultados (não encontrado de verdade) ou vários resultados
    # de tipos variados (o protocolo aparece no conteúdo de outros
    # documentos/processos, nem sempre do tipo que interessa).
    resultado = encontrar_processo_tipo_aceito_na_pesquisa(page, TIPOS_ACEITOS)
    if resultado is None:
        total = contar_resultados_pesquisa(page)
        if not total:
            registrar_resultado(protocolo, "nao_encontrado", "protocolo não encontrado")
        else:
            registrar_resultado(
                protocolo,
                "tipo_diferente",
                "Tipo diferente",
                detalhe=f"{total} resultado(s) na busca avançada, nenhum de tipo aceito",
            )
        return

    tipo_achado, numero_achado = resultado

    # Reabre o processo pesquisando pelo número já identificado — mais
    # confiável do que tentar clicar no item específico da lista de
    # resultados (layout incerto), e reaproveita o mesmo fluxo já testado.
    pesquisar_processo(page, numero_achado)
    if not protocolo_encontrado(page):
        registrar_resultado(
            protocolo,
            "falha",
            f"encontrei o processo {numero_achado} na busca avançada, mas não consegui abri-lo direto",
            detalhe=tipo_achado,
        )
        return

    numero_confirmado, tipo_confirmado = ler_numero_e_tipo_processo(page)
    _classificar_e_baixar(
        page, protocolo, numero_confirmado or numero_achado, tipo_confirmado or tipo_achado
    )


def _classificar_e_baixar(page: Page, protocolo: str, numero: str, tipo: str | None) -> None:
    """Compara `tipo` com os aceitos; se bater, clica no número do processo
    (troca o painel principal pro contexto do processo) e baixa o PDF."""
    tipo_normalizado = (tipo or "").strip().lower()
    if not any(aceito in tipo_normalizado for aceito in TIPOS_ACEITOS):
        registrar_resultado(
            protocolo, "tipo_diferente", "Tipo diferente", detalhe=tipo or "(tipo não lido)"
        )
        return

    # Camada de segurança contra o bug do autocomplete do campo de pesquisa
    # (já visto na prática): se esse mesmo número de processo já foi
    # confirmado como baixado para OUTRO protocolo, não confia cegamente —
    # provavelmente a busca pegou uma sugestão antiga em vez do texto certo.
    conflito = numero_ja_usado_por_outro(protocolo, numero)
    if conflito:
        registrar_resultado(
            protocolo,
            "falha",
            f"suspeita de busca incorreta: processo {numero} já registrado para o "
            f"protocolo {conflito} — confira manualmente",
            detalhe=tipo or "",
        )
        return

    # Busca por protocolo (ou reabertura por número) abre direto num
    # documento específico da árvore — precisa clicar no número do processo
    # pra trocar o painel principal pro contexto do processo, onde o ícone
    # "Gerar Arquivo PDF do Processo" existe.
    if not clicar_numero_processo_no_topo(page):
        registrar_resultado(
            protocolo,
            "falha",
            f"erro: não consegui clicar no número do processo {numero}",
            detalhe=tipo or "",
        )
        return
    page.wait_for_timeout(1000)

    sucesso = baixar_pdf_processo(page, numero)
    if sucesso:
        registrar_resultado(protocolo, "baixado", numero, detalhe=tipo or "")
    else:
        registrar_resultado(protocolo, "falha", f"erro ao baixar PDF de {numero}", detalhe=tipo or "")
