"""Configuração da conexão com o SEI.

Mesma lógica usada em sei-automacao: a automação nunca abre nem loga no
navegador sozinha — ela se conecta a um Chrome que você já abriu e logou
manualmente, via modo de depuração remota (CDP). Veja README.md ->
"Conectar num Chrome já logado" para o passo a passo.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SEI_URL = "https://sei.exemplo.gov.br"  # URL real da sua instância vai em config_local.py

# Porta de depuração remota do Chrome que você abre manualmente antes de
# rodar a automação.
CDP_URL = "http://localhost:9222"

# Processos com muitos documentos demoram mais pra gerar o PDF — 15s já se
# mostrou curto demais em alguns casos reais (timeout estourando antes do
# download começar).
TIMEOUT_PADRAO_MS = 40_000

SCREENSHOTS_DIR = BASE_DIR / "screenshots"
DOWNLOADS_DIR = BASE_DIR / "pdfs_baixados"

# Planilha de entrada do fluxo "por número de processo" (coluna "SEI").
PLANILHA_PROCESSOS = BASE_DIR / "processos.csv"

# ---------------------------------------------------------------------------
# Overrides locais
# ---------------------------------------------------------------------------
# Os valores acima são exemplos genéricos. Dados reais (URL do SEI, nome da
# planilha de entrada) ficam em src/config_local.py, que não é versionado —
# veja src/config_local.example.py.
try:
    from .config_local import *  # noqa: F401,F403
except ImportError:
    pass
