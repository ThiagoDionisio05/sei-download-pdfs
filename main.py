"""Orquestrador: baixa o PDF de todos os processos pendentes da planilha.

Fluxo por processo (repete pra cada linha pendente):
  1. Pesquisa o número do processo na barra de pesquisa do SEI
  2. Gera e baixa o PDF do processo ("Todos os documentos disponíveis")
  3. Valida o arquivo e registra o resultado (baixado ou falha)
  4. Volta pra "Controle de Processos" antes do próximo processo

Idempotente: processos já confirmados em status/pdfs_baixados.json são
pulados — rodar de novo retoma de onde parou, sem baixar de novo.

Uso:
    python main.py                # roda todos os pendentes
    python main.py --limite 5     # só os primeiros 5 pendentes (teste)
"""

import argparse
import csv

from playwright.sync_api import sync_playwright

from src import config
from src.browser import abrir_sessao
from src.pdf_processo import baixar_pdf_processo
from src.sei_page import pesquisar_processo, sair_do_processo, screenshot
from src.status_pdf import ja_baixado, registrar_falha
from gerar_relatorio import main as gerar_relatorio

CSV_PATH = config.PLANILHA_PROCESSOS


def carregar_numeros_processo() -> list[str]:
    with open(CSV_PATH, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        numeros = [(row.get("SEI") or "").strip() for row in reader]
    return [n for n in numeros if n]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Processa só os N primeiros processos pendentes (útil pra testar antes do lote todo).",
    )
    args = parser.parse_args()

    numeros = carregar_numeros_processo()
    pendentes = [n for n in numeros if not ja_baixado(n)]

    if args.limite is not None:
        pendentes = pendentes[: args.limite]

    if not pendentes:
        print("Nada a processar — todos os processos já têm PDF baixado e confirmado.")
        return

    print(f"{len(pendentes)} processo(s) pendente(s) a processar.\n")

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        for i, numero in enumerate(pendentes, start=1):
            print(f"--- [{i}/{len(pendentes)}] {numero} ---")
            try:
                pesquisar_processo(page, numero)
                baixar_pdf_processo(page, numero)
            except Exception as exc:
                registrar_falha(numero, f"erro inesperado: {exc}")
                screenshot(page, f"erro_{numero.replace('/', '-')}")

            try:
                sair_do_processo(page)
            except Exception as exc:
                print(
                    f"\nAVISO: não consegui voltar pra 'Controle de Processos' ({exc})."
                    "\nParando a execução por segurança — os próximos processos não seriam "
                    "pesquisados corretamente com a tela num estado desconhecido."
                )
                break

        gerar_relatorio()
        print("\nConcluído. Veja relatorio_downloads.html para o resumo completo.")


if __name__ == "__main__":
    main()
