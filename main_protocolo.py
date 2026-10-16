"""Orquestrador do fluxo por Protocolo: pesquisa no SEI, classifica o tipo
do processo, baixa o PDF quando aplicável, e escreve o resultado.

Fluxo por protocolo (repete pra cada linha pendente):
  1. Pesquisa o Protocolo na barra de pesquisa do SEI
  2. Não encontrado -> "protocolo não encontrado"
  3. Encontrado, tipo do processo diferente dos aceitos -> "Tipo diferente"
  4. Encontrado, tipo aceito -> baixa o PDF completo -> grava o nº do processo
  5. Volta pra "Controle de Processos" antes do próximo protocolo

Idempotente: protocolos já processados (status/protocolos_resultados.json)
são pulados — rodar de novo retoma de onde parou.

Uso:
    python main_protocolo.py                # roda todos os pendentes
    python main_protocolo.py --limite 10     # só os N primeiros pendentes
"""

import argparse

from playwright.sync_api import sync_playwright

from src.browser import abrir_sessao
from src.planilha_protocolo import carregar_protocolos
from src.protocolo_processo import processar_protocolo
from src.sei_page import sair_do_processo, screenshot
from src.status_protocolo import ja_processado, registrar_resultado
from gerar_relatorio_protocolo import main as gerar_relatorio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        help="Processa só os N primeiros protocolos pendentes (útil pra testar).",
    )
    args = parser.parse_args()

    protocolos = carregar_protocolos()
    pendentes = [p for p in protocolos if not ja_processado(p)]

    if args.limite is not None:
        pendentes = pendentes[: args.limite]

    if not pendentes:
        print("Nada a processar — todos os protocolos já têm resultado registrado.")
        return

    print(f"{len(pendentes)} protocolo(s) pendente(s) a processar.\n")

    with sync_playwright() as playwright:
        context, page = abrir_sessao(playwright)

        for i, protocolo in enumerate(pendentes, start=1):
            print(f"--- [{i}/{len(pendentes)}] {protocolo} ---")
            try:
                processar_protocolo(page, protocolo)
            except Exception as exc:
                registrar_resultado(protocolo, "falha", f"erro inesperado: {exc}")
                screenshot(page, f"erro_protocolo_{protocolo}")

            try:
                sair_do_processo(page)
            except Exception as exc:
                print(
                    f"\nAVISO: não consegui voltar pra 'Controle de Processos' ({exc})."
                    "\nParando a execução por segurança — os próximos protocolos não "
                    "seriam pesquisados corretamente com a tela num estado desconhecido."
                )
                break

        gerar_relatorio()
        print("\nConcluído. Veja relatorio_protocolos.html e planilha_resultado.xlsx.")


if __name__ == "__main__":
    main()
