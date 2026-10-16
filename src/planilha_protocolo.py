"""Leitura da planilha de entrada do fluxo por Protocolo (Protocolo/Prazo/SEI)."""

import csv
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent.parent


def encontrar_planilha_entrada() -> Path:
    """Acha o CSV de entrada mais recente — o nome muda a cada vez que uma
    nova versão é colada na pasta (sufixos tipo '(1) (2)'), então não dá
    pra fixar um nome exato no código."""
    candidatos = sorted(
        PASTA_PROJETO.glob("relatorio_lista_de_tarefa*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidatos:
        raise RuntimeError(
            "Nenhum arquivo 'relatorio_lista_de_tarefa*.csv' encontrado na pasta do projeto."
        )
    return candidatos[0]


def carregar_linhas_planilha() -> list[dict]:
    # utf-8-sig: esse CSV vem com BOM (diferente do formato usado no fluxo
    # anterior, que era latin-1) — sem isso, a primeira coluna do cabeçalho
    # vem com lixo na frente ("Protocolo" vira "﻿﻿..Protocolo") e
    # row.get("Protocolo") retorna sempre vazio.
    caminho = encontrar_planilha_entrada()
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def carregar_protocolos() -> list[str]:
    linhas = carregar_linhas_planilha()
    protocolos = [(row.get("Protocolo") or "").strip() for row in linhas]
    return [p for p in protocolos if p]
