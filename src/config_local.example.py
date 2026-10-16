"""
Modelo de configuração local.

Copie este arquivo para `src/config_local.py` e preencha com seus dados
reais. O `config_local.py` está no .gitignore — nunca é versionado — e
sobrescreve os valores de exemplo de `src/config.py`.
"""

from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent

# Endereço da sua instância do SEI
SEI_URL = "https://sei.seuorgao.gov.br"

# Planilha de entrada do fluxo "por número de processo" (precisa ter a coluna "SEI")
PLANILHA_PROCESSOS = _BASE_DIR / "processos.csv"
