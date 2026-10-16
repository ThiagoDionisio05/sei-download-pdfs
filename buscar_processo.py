"""Teste: baixa o PDF do processo SEI da primeira linha pendente da planilha.

Uso:
    python buscar_processo.py
"""

import csv

from playwright.sync_api import sync_playwright

from src import config
from src.browser import abrir_sessao
from src.pdf_processo import baixar_pdf_processo
from src.sei_page import pesquisar_processo, screenshot
from src.status_pdf import ja_baixado
from gerar_relatorio import main as gerar_relatorio

CSV_PATH = config.PLANILHA_PROCESSOS


def carregar_primeiro_numero_pendente() -> str:
    with open(CSV_PATH, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            numero = (row.get("SEI") or "").strip()
            if numero and not ja_baixado(numero):
                return numero
    raise RuntimeError("Nenhum processo pendente encontrado na planilha.")


def main():
    numero_processo = carregar_primeiro_numero_pendente()
    print(f"Processo a pesquisar: {numero_processo}")

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        pesquisar_processo(page, numero_processo)
        screenshot(page, "01_processo_aberto")

        sucesso = baixar_pdf_processo(page, numero_processo)
        print("Sucesso!" if sucesso else "Falhou — veja status/pdfs_baixados.log e o screenshot gerado.")

        gerar_relatorio()


if __name__ == "__main__":
    main()
