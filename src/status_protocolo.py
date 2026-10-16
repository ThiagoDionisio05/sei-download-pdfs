"""Registro de resultados por protocolo (fluxo de busca por Protocolo).

status/protocolos_resultados.json -> controle (idempotência) + fonte de
dados pro relatório HTML e pra planilha de saída (.xlsx).
status/protocolos_resultados.log  -> log legível, uma linha por protocolo.
"""

import json
from datetime import datetime
from pathlib import Path

STATUS_DIR = Path(__file__).resolve().parent.parent / "status"
RESULTADOS_JSON = STATUS_DIR / "protocolos_resultados.json"
RESULTADOS_LOG = STATUS_DIR / "protocolos_resultados.log"


def carregar_resultados() -> dict:
    if not RESULTADOS_JSON.exists():
        return {}
    return json.loads(RESULTADOS_JSON.read_text(encoding="utf-8"))


def ja_processado(protocolo: str) -> bool:
    return protocolo in carregar_resultados()


def numero_ja_usado_por_outro(protocolo: str, numero_processo: str) -> str | None:
    """Retorna o protocolo que já está registrado como 'baixado' com esse
    mesmo numero_processo (diferente do informado), se houver algum.

    Camada de segurança contra o bug do autocomplete do campo de pesquisa
    (Enter às vezes seleciona uma sugestão antiga em vez do texto digitado),
    que já causou o mesmo processo sendo atribuído erradamente a vários
    protocolos diferentes. Sem essa checagem, o segundo/terceiro protocolo
    que "acerta" o mesmo número por engano seria aceito silenciosamente.
    """
    resultados = carregar_resultados()
    for outro_protocolo, info in resultados.items():
        if outro_protocolo == protocolo:
            continue
        if info.get("status") == "baixado" and info.get("valor_sei") == numero_processo:
            return outro_protocolo
    return None


def registrar_resultado(protocolo: str, status: str, valor_sei: str, detalhe: str = "") -> None:
    """status: 'nao_encontrado' | 'tipo_diferente' | 'baixado' | 'falha'
    valor_sei: exatamente o texto que vai pra coluna SEI da planilha de saída."""
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    resultados = carregar_resultados()
    resultados[protocolo] = {
        "status": status,
        "valor_sei": valor_sei,
        "detalhe": detalhe,
        "data": datetime.now().isoformat(timespec="seconds"),
    }
    RESULTADOS_JSON.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with open(RESULTADOS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{protocolo} : {valor_sei}\n")
    print(f"{protocolo} : {valor_sei}")
