"""Gera o relatório HTML e a planilha .xlsx de saída do fluxo por Protocolo,
cruzando a planilha de entrada (Protocolo/Prazo/SEI) com
status/protocolos_resultados.json.

Uso:
    python gerar_relatorio_protocolo.py
Gera: relatorio_protocolos.html (abra no navegador) e planilha_resultado.xlsx
"""

import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from src.planilha_protocolo import carregar_linhas_planilha
from src.status_protocolo import carregar_resultados

PASTA_PROJETO = Path(__file__).resolve().parent
SAIDA_HTML = PASTA_PROJETO / "relatorio_protocolos.html"
SAIDA_XLSX = PASTA_PROJETO / "planilha_resultado.xlsx"

ROTULOS_STATUS = {
    "baixado": "✓ Baixado",
    "pendente": "⏳ Pendente",
    "tipo_diferente": "⊘ Tipo diferente",
    "nao_encontrado": "✕ Não encontrado",
    "falha": "✕ Falha",
}


def montar_linhas() -> list[dict]:
    resultados = carregar_resultados()
    linhas_planilha = carregar_linhas_planilha()

    linhas = []
    for i, row in enumerate(linhas_planilha, start=2):
        protocolo = (row.get("Protocolo") or "").strip()
        prazo_bruto = (row.get("Prazo") or "").strip()

        info = resultados.get(protocolo)
        if info:
            status = info.get("status", "falha")
            valor_sei = info.get("valor_sei", "")
            detalhe = info.get("detalhe", "")
        else:
            status = "pendente"
            valor_sei = ""
            detalhe = ""

        linhas.append(
            {
                "numero_linha": i,
                "protocolo": protocolo,
                "prazo_bruto": prazo_bruto,
                "status": status,
                "valor_sei": valor_sei,
                "detalhe": detalhe,
            }
        )
    return linhas


def gerar_xlsx(linhas: list[dict]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultado"
    ws.append(["Protocolo", "Prazo", "SEI"])
    for l in linhas:
        ws.append([l["protocolo"], l["prazo_bruto"], l["valor_sei"]])

    try:
        wb.save(str(SAIDA_XLSX))
    except PermissionError:
        # Provavelmente o arquivo está aberto no Excel — o Windows bloqueia
        # a escrita nesse caso. Salva num caminho alternativo em vez de
        # travar a execução inteira (o status já foi gravado antes disso).
        alternativo = SAIDA_XLSX.with_stem(
            SAIDA_XLSX.stem + "_" + datetime.now().strftime("%H%M%S")
        )
        wb.save(str(alternativo))
        print(
            f"AVISO: {SAIDA_XLSX.name} está aberto (provavelmente no Excel) — "
            f"salvei em {alternativo.name} em vez disso. Feche o arquivo original "
            "e rode 'python gerar_relatorio_protocolo.py' de novo pra atualizá-lo."
        )


def gerar_html(linhas: list[dict]) -> str:
    total = len(linhas)
    contagem = {"baixado": 0, "pendente": 0, "tipo_diferente": 0, "nao_encontrado": 0, "falha": 0}
    for l in linhas:
        contagem[l["status"]] = contagem.get(l["status"], 0) + 1

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    dados_json = json.dumps(linhas, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relatório de Protocolos — Reposição ao Erário</title>
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
    --serious: #c15a30;
    --serious-bg: #fbe9e0;
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
      --serious: #ec835a;
      --serious-bg: #3a2015;
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
    --serious: #ec835a;
    --serious-bg: #3a2015;
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
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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
  .stat-tile.good .value {{ color: var(--good); }}
  .stat-tile.warning .value {{ color: var(--warning); }}
  .stat-tile.serious .value {{ color: var(--serious); }}
  .stat-tile.critical .value {{ color: var(--critical); }}

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
  .toolbar button {{
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 14px;
    border-radius: 7px;
    border: 1px solid var(--border);
    background: var(--accent);
    color: #fff;
    cursor: pointer;
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
  .badge.tipo_diferente {{ background: var(--serious-bg); color: var(--serious); }}
  .badge.nao_encontrado {{ background: var(--critical-bg); color: var(--critical); }}
  .badge.falha {{ background: var(--critical-bg); color: var(--critical); }}

  .empty-state {{ padding: 40px 16px; text-align: center; color: var(--text-muted); font-size: 13.5px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Relatório de Protocolos — Reposição ao Erário</h1>
    <div class="subtitle">Gerado em {agora} · cruza a planilha de entrada com status/protocolos_resultados.json · exportável em planilha_resultado.xlsx</div>
  </header>

  <div class="stats">
    <div class="stat-tile">
      <div class="label">Total</div>
      <div class="value">{total}</div>
    </div>
    <div class="stat-tile good">
      <div class="label">Baixados</div>
      <div class="value">{contagem['baixado']}</div>
    </div>
    <div class="stat-tile warning">
      <div class="label">Pendentes</div>
      <div class="value">{contagem['pendente']}</div>
    </div>
    <div class="stat-tile serious">
      <div class="label">Tipo diferente</div>
      <div class="value">{contagem['tipo_diferente']}</div>
    </div>
    <div class="stat-tile critical">
      <div class="label">Não encontrados</div>
      <div class="value">{contagem['nao_encontrado']}</div>
    </div>
    <div class="stat-tile critical">
      <div class="label">Falhas</div>
      <div class="value">{contagem['falha']}</div>
    </div>
  </div>

  <div class="card">
    <div class="toolbar">
      <input type="search" id="busca" placeholder="Buscar por protocolo, interessado ou processo...">
      <select id="filtroStatus">
        <option value="todos">Todos os status</option>
        <option value="baixado">✓ Baixado</option>
        <option value="pendente">⏳ Pendente</option>
        <option value="tipo_diferente">⊘ Tipo diferente</option>
        <option value="nao_encontrado">✕ Não encontrado</option>
        <option value="falha">✕ Falha</option>
      </select>
      <button id="btnExport">Exportar CSV</button>
      <span class="count" id="count"></span>
    </div>
    <table>
      <thead>
        <tr>
          <th class="col-num">#</th>
          <th>Protocolo</th>
          <th>Interessado (col. "Prazo" da planilha)</th>
          <th>Status</th>
          <th>SEI / Valor</th>
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
    tipo_diferente: "⊘ Tipo diferente",
    nao_encontrado: "✕ Não encontrado",
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

  function filtradas() {{
    const termo = normalizar(busca.value);
    const status = filtroStatus.value;
    return DADOS.filter(l => {{
      if (status !== "todos" && l.status !== status) return false;
      if (!termo) return true;
      return (
        normalizar(l.protocolo).includes(termo) ||
        normalizar(l.prazo_bruto).includes(termo) ||
        normalizar(l.valor_sei).includes(termo)
      );
    }});
  }}

  function render() {{
    const linhas = filtradas();

    tbody.innerHTML = "";
    emptyState.hidden = linhas.length > 0;

    linhas.forEach(l => {{
      const tr = document.createElement("tr");

      const tdNum = document.createElement("td");
      tdNum.className = "col-num";
      tdNum.textContent = l.numero_linha;

      const tdProtocolo = document.createElement("td");
      tdProtocolo.textContent = l.protocolo;

      const tdInteressado = document.createElement("td");
      tdInteressado.textContent = l.prazo_bruto;

      const tdStatus = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = "badge " + l.status;
      badge.textContent = ROTULOS[l.status] || l.status;
      tdStatus.appendChild(badge);

      const tdValor = document.createElement("td");
      tdValor.className = "processo";
      tdValor.textContent = l.valor_sei;

      const tdDetalhe = document.createElement("td");
      tdDetalhe.textContent = l.detalhe;

      tr.append(tdNum, tdProtocolo, tdInteressado, tdStatus, tdValor, tdDetalhe);
      tbody.appendChild(tr);
    }});

    countEl.textContent = linhas.length + (linhas.length === 1 ? " registro" : " registros");
  }}

  document.getElementById("btnExport").addEventListener("click", () => {{
    const cabecalho = "Protocolo,Prazo,SEI\\n";
    const linhasCsv = filtradas().map(l => {{
      const esc = v => `"${{String(v || "").replace(/"/g, '""')}}"`;
      return [esc(l.protocolo), esc(l.prazo_bruto), esc(l.valor_sei)].join(",");
    }}).join("\\n");
    const csv = cabecalho + linhasCsv;
    const blob = new Blob(["\\ufeff" + csv], {{ type: "text/csv;charset=utf-8;" }});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "planilha_resultado.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }});

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
    gerar_xlsx(linhas)
    print(f"Relatório gerado: {SAIDA_HTML}")
    print(f"Planilha gerada: {SAIDA_XLSX}")


if __name__ == "__main__":
    main()
