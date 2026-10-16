"""Registro de PDFs baixados por processo SEI.

Dois arquivos em status/:
- pdfs_baixados.json  -> controle (idempotência): não baixa de novo o que
  já está registrado aqui, e guarda caminho/tamanho/data de cada PDF.
- pdfs_baixados.log   -> log legível, uma linha por download confirmado,
  no formato "<numero do processo> : PDF já baixado".
"""

import json
from datetime import datetime
from pathlib import Path

STATUS_DIR = Path(__file__).resolve().parent.parent / "status"
STATUS_JSON = STATUS_DIR / "pdfs_baixados.json"
FALHAS_JSON = STATUS_DIR / "pdfs_falhas.json"
STATUS_LOG = STATUS_DIR / "pdfs_baixados.log"


def carregar_status() -> dict:
    if not STATUS_JSON.exists():
        return {}
    return json.loads(STATUS_JSON.read_text(encoding="utf-8"))


def carregar_falhas() -> dict:
    if not FALHAS_JSON.exists():
        return {}
    return json.loads(FALHAS_JSON.read_text(encoding="utf-8"))


def ja_baixado(numero_processo: str) -> bool:
    return numero_processo in carregar_status()


def verificar_pdf_valido(caminho_pdf: Path) -> bool:
    """Confirma que o arquivo existe, não está vazio, e começa com a
    assinatura '%PDF-' (pega tanto download que falhou quanto arquivo
    corrompido/vazio salvo no lugar certo)."""
    if not caminho_pdf.exists() or caminho_pdf.stat().st_size == 0:
        return False
    with open(caminho_pdf, "rb") as f:
        return f.read(5) == b"%PDF-"


def registrar_pdf_baixado(numero_processo: str, caminho_pdf: Path) -> None:
    """Grava no JSON de controle e no log legível que o PDF deste processo
    foi baixado. Chame só depois de `verificar_pdf_valido` confirmar que o
    arquivo é um PDF de verdade."""
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    status = carregar_status()
    status[numero_processo] = {
        "arquivo": str(caminho_pdf),
        "tamanho_bytes": caminho_pdf.stat().st_size,
        "data": datetime.now().isoformat(timespec="seconds"),
    }
    STATUS_JSON.write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with open(STATUS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{numero_processo} : PDF já baixado\n")

    print(f"{numero_processo} : PDF já baixado")


def registrar_falha(numero_processo: str, motivo: str) -> None:
    """Grava a falha (PDF não confirmado) tanto no JSON de controle quanto
    no log legível — o JSON é o que o relatório HTML usa pra cruzar com a
    planilha; o log fica só pra leitura humana rápida."""
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    falhas = carregar_falhas()
    falhas[numero_processo] = {
        "motivo": motivo,
        "data": datetime.now().isoformat(timespec="seconds"),
    }
    FALHAS_JSON.write_text(
        json.dumps(falhas, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with open(STATUS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{numero_processo} : FALHA - {motivo}\n")
    print(f"{numero_processo} : FALHA - {motivo}")
