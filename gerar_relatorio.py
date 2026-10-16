"""Gera um relatório HTML cruzando a planilha de processos com o status real
de download dos PDFs (status/pdfs_baixados.json e status/pdfs_falhas.json).

Serve pra responder "pulei algum PDF?" de forma visual: cada pessoa da
planilha aparece com um selo de Baixado / Pendente / Falha, e um resumo no
topo mostra quantos faltam.

Uso:
    python gerar_relatorio.py
Gera: relatorio_downloads.html (abra no navegador).
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from src import config
from src.status_pdf import carregar_falhas, carregar_status

CSV_PATH = config.PLANILHA_PROCESSOS
SAIDA_HTML = Path(__file__).resolve().parent / "relatorio_downloads.html"

CPF_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


def carregar_linhas_planilha() -> list[dict]:
    with open(CSV_PATH, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def separar_nome_cpf(identificador: str) -> tuple[str, str]:
    identificador = (identificador or "").strip()
    match = CPF_RE.search(identificador)
    if not match:
        return identificador, ""
    cpf = match.group(0)
    nome = identificador[: match.start()].rstrip(" -").strip()
    return nome, cpf


def montar_linhas() -> list[dict]:
    baixados = carregar_status()
    falhas = carregar_falhas()
    linhas_planilha = carregar_linhas_planilha()

    # Alguns números de processo SEI aparecem em mais de uma linha da
    # planilha (mesmo processo, tarefas/pessoas diferentes) — um único PDF
    # baixado cobre todas essas linhas. Sem sinalizar isso, o total de
    # "Baixados" (contado por linha) não bate com a quantidade de arquivos
    # físicos em pdfs_baixados/ (contados por processo único), o que confunde.
    linhas_por_processo: dict[str, list[int]] = {}
    for i, row in enumerate(linhas_planilha, start=2):
        numero = (row.get("SEI") or "").strip()
        if numero:
            linhas_por_processo.setdefault(numero, []).append(i)

    linhas = []
    for i, row in enumerate(linhas_planilha, start=2):
        numero_processo = (row.get("SEI") or "").strip()
        nome, _cpf = separar_nome_cpf(row.get("Identificador do Interessado", ""))

        if numero_processo in baixados:
            info = baixados[numero_processo]
            status = "baixado"
            detalhe = info.get("data", "")
            arquivo = Path(info.get("arquivo", "")).name
        elif numero_processo in falhas:
            info = falhas[numero_processo]
            status = "falha"
            detalhe = info.get("motivo", "")
            arquivo = ""
        else:
            status = "pendente"
            detalhe = ""
            arquivo = ""

        outras_linhas = [n for n in linhas_por_processo.get(numero_processo, []) if n != i]
        nota_duplicado = (
            "mesmo processo da linha " + " e ".join(str(n) for n in outras_linhas)
            if outras_linhas
            else ""
        )

        linhas.append(
            {
                "numero_linha": i,
                "protocolo": (row.get("Protocolo") or "").strip(),
                "nome": nome,
                "processo": numero_processo,
                "status": status,
                "detalhe": detalhe,
                "arquivo": arquivo,
                "nota_duplicado": nota_duplicado,
            }
        )
    return linhas


def gerar_html(linhas: list[dict]) -> str:
    total = len(linhas)
    n_baixados = sum(1 for l in linhas if l["status"] == "baixado")
    n_pendentes = sum(1 for l in linhas if l["status"] == "pendente")
    n_falhas = sum(1 for l in linhas if l["status"] == "falha")
    n_arquivos_unicos = len({l["processo"] for l in linhas if l["status"] == "baixado"})
    nota_duplicados = (
        f" ({n_arquivos_unicos} arquivo{'s' if n_arquivos_unicos != 1 else ''} único{'s' if n_arquivos_unicos != 1 else ''} — "
        f"{n_baixados - n_arquivos_unicos} linha(s) repete(m) processo já baixado)"
        if n_baixados != n_arquivos_unicos
        else ""
    )
    percentual = round((n_baixados / total) * 100, 1) if total else 0.0

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Embutido como literal JS direto (JSON é um subconjunto válido de JS) —
    # só escapa "</" pra não fechar a tag <script> no meio do conteúdo.
    dados_json = json.dumps(linhas, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório de Download de PDFs</title>
<style>
  :root {{
    color-scheme: light;
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --border: #e1e0d9;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --good: #0ca30c;
    --good-bg: #e6f6e6;
    --warning: #b5790a;
    --warning-bg: #fdf1da;
    --critical: #d03b3b;
    --critical-bg: #fbe6e6;
    --accent: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --surface-1: #1a1a19;
      --page: #0d0d0d;
      --border: #2c2c2a;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted: #898781;
      --good: #0ca30c;
      --good-bg: #123a17;
      --warning: #fab219;
      --warning-bg: #3a2f10;
      --critical: #e66767;
      --critical-bg: #3a1414;
      --accent: #3987e5;
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --surface-1: #1a1a19;
    --page: #0d0d0d;
    --border: #2c2c2a;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted: #898781;
    --good: #0ca30c;
    --good-bg: #123a17;
    --warning: #fab219;
    --warning-bg: #3a2f10;
    --critical: #e66767;
    --critical-bg: #3a1414;
    --accent: #3987e5;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 32px 24px 64px;
    background: var(--page);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; }}
  header {{ margin-bottom: 22px; }}
  h1 {{ font-size: 22px; font-weight: 600; margin: 0 0 4px; }}
  .subtitle {{ color: var(--text-secondary); font-size: 13.5px; }}

  .stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }}
  .stat-tile {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px 18px;
  }}
  .stat-tile .label {{
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: var(--text-muted);
    margin-bottom: 6px;
  }}
  .stat-tile .value {{
    font-size: 28px;
    font-weight: 600;
    font-variant-numeric: proportional-nums;
  }}
  .stat-tile .footnote {{
    font-size: 11.5px;
    color: var(--text-muted);
    margin-top: 4px;
  }}
  .stat-tile.good .value {{ color: var(--good); }}
  .stat-tile.warning .value {{ color: var(--warning); }}
  .stat-tile.critical .value {{ color: var(--critical); }}

  .progress-wrap {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 20px;
  }}
  .progress-label {{
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }}
  .progress-track {{
    height: 8px;
    border-radius: 4px;
    background: var(--border);
    overflow: hidden;
  }}
  .progress-fill {{
    height: 100%;
    background: var(--good);
    border-radius: 4px;
  }}

  .card {{
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
  }}
  .toolbar {{
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }}
  .toolbar input[type="search"] {{
    flex: 1;
    min-width: 200px;
    font: inherit;
    font-size: 13.5px;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--page);
    color: var(--text-primary);
  }}
  .toolbar select {{
    font: inherit;
    font-size: 13.5px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 7px;
    background: var(--page);
    color: var(--text-primary);
  }}
  .toolbar .count {{ margin-left: auto; font-size: 12.5px; color: var(--text-muted); }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
  thead th {{
    text-align: left;
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: .04em;
    color: var(--text-muted);
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    background: var(--surface-1);
  }}
  tbody tr {{ border-bottom: 1px solid var(--border); }}
  tbody tr:hover {{ background: var(--page); }}
  td {{ padding: 9px 16px; vertical-align: middle; color: var(--text-primary); }}
  td.processo {{ font-variant-numeric: tabular-nums; color: var(--text-secondary); }}
  th.col-num, td.col-num {{ width: 44px; font-variant-numeric: tabular-nums; color: var(--text-muted); }}

  .badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }}
  .badge.baixado {{ background: var(--good-bg); color: var(--good); }}
  .badge.pendente {{ background: var(--warning-bg); color: var(--warning); }}
  .badge.falha {{ background: var(--critical-bg); color: var(--critical); }}

  .empty-state {{ padding: 40px 16px; text-align: center; color: var(--text-muted); font-size: 13.5px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Relatório de Download de PDFs — Reposição ao Erário</h1>
    <div class="subtitle">Gerado em {agora} · cruza a planilha original com status/pdfs_baixados.json e status/pdfs_falhas.json</div>
  </header>

  <div class="stats">
    <div class="stat-tile">
      <div class="label">Total de processos</div>
      <div class="value" id="statTotal">{total}</div>
    </div>
    <div class="stat-tile good">
      <div class="label">Baixados</div>
      <div class="value" id="statBaixados">{n_baixados}</div>
      {f'<div class="footnote">{nota_duplicados.strip(" ()")}</div>' if nota_duplicados else ''}
    </div>
    <div class="stat-tile warning">
      <div class="label">Pendentes</div>
      <div class="value" id="statPendentes">{n_pendentes}</div>
    </div>
    <div class="stat-tile critical">
      <div class="label">Falhas</div>
      <div class="value" id="statFalhas">{n_falhas}</div>
    </div>
  </div>

  <div class="progress-wrap">
    <div class="progress-label">
      <span>Progresso</span>
      <span id="progressoTexto">{percentual}% concluído</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" id="progressoFill" style="width: {percentual}%;"></div>
    </div>
  </div>

  <div class="card">
    <div class="toolbar">
      <input type="search" id="busca" placeholder="Buscar por nome ou nº do processo...">
      <select id="filtroStatus">
        <option value="todos">Todos os status</option>
        <option value="baixado">✓ Baixado</option>
        <option value="pendente">⏳ Pendente</option>
        <option value="falha">✕ Falha</option>
      </select>
      <span class="count" id="count"></span>
    </div>
    <table>
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th>Nome</th>
          <th>Nº do Processo SEI</th>
          <th>Status</th>
          <th>Detalhe</th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
    <div class="empty-state" id="emptyState" hidden>Nenhum registro corresponde ao filtro.</div>
  </div>
</div>

<script>
  const DADOS = {dados_json};

  const ROTULOS = {{
    baixado: "✓ Baixado",
    pendente: "⏳ Pendente",
    falha: "✕ Falha",
  }};

  const tbody = document.getElementById("tbody");
  const emptyState = document.getElementById("emptyState");
  const countEl = document.getElementById("count");
  const busca = document.getElementById("busca");
  const filtroStatus = document.getElementById("filtroStatus");

  function normalizar(s) {{
    return (s || "").toLowerCase();
  }}

  function render() {{
    const termo = normalizar(busca.value);
    const status = filtroStatus.value;

    const filtradas = DADOS.filter(l => {{
      if (status !== "todos" && l.status !== status) return false;
      if (!termo) return true;
      return (
        normalizar(l.nome).includes(termo) ||
        normalizar(l.processo).includes(termo)
      );
    }});

    tbody.innerHTML = "";
    emptyState.hidden = filtradas.length > 0;

    filtradas.forEach(l => {{
      const tr = document.createElement("tr");

      const tdNum = document.createElement("td");
      tdNum.className = "col-num";
      tdNum.textContent = l.numero_linha;

      const tdNome = document.createElement("td");
      tdNome.textContent = l.nome;

      const tdProcesso = document.createElement("td");
      tdProcesso.className = "processo";
      tdProcesso.textContent = l.processo;

      const tdStatus = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = "badge " + l.status;
      badge.textContent = ROTULOS[l.status] || l.status;
      tdStatus.appendChild(badge);

      const tdDetalhe = document.createElement("td");
      let textoDetalhe = l.status === "baixado" ? (l.arquivo || l.detalhe) : l.detalhe;
      if (l.nota_duplicado) {{
        textoDetalhe = textoDetalhe ? `${{textoDetalhe}} · ${{l.nota_duplicado}}` : l.nota_duplicado;
      }}
      tdDetalhe.textContent = textoDetalhe;

      tr.append(tdNum, tdNome, tdProcesso, tdStatus, tdDetalhe);
      tbody.appendChild(tr);
    }});

    countEl.textContent = filtradas.length + (filtradas.length === 1 ? " registro" : " registros");
  }}

  busca.addEventListener("input", render);
  filtroStatus.addEventListener("change", render);
  render();
</script>
</body>
</html>
"""


def main():
    linhas = montar_linhas()
    SAIDA_HTML.write_text(gerar_html(linhas), encoding="utf-8")
    print(f"Relatório gerado: {SAIDA_HTML}")


if __name__ == "__main__":
    main()
