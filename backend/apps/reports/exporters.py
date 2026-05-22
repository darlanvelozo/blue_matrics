"""
Exportadores de dashboard.

- Excel (openpyxl): planilhas estruturadas com KPIs + séries + rankings
- HTML imprimível (cliente faz "Imprimir → PDF" no browser, sem dependência
  de WeasyPrint que requer libs nativas em prod)
"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

_HEADER_FILL = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
_HEADER_FONT = Font(color="FFFFFF", bold=True)


# ===========================================================================
# Excel
# ===========================================================================
def _style_header(ws, ncols: int) -> None:
    for col_idx in range(1, ncols + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="left")


def _auto_size(ws, max_col: int) -> None:
    for col_idx in range(1, max_col + 1):
        letter = get_column_letter(col_idx)
        ws.column_dimensions[letter].width = 22


def _section(ws, title: str, *, row: int) -> int:
    cell = ws.cell(row=row, column=1, value=title)
    cell.font = Font(bold=True, size=12)
    return row + 1


def executive_to_excel(data: dict, tenant_name: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Resumo"

    ws["A1"] = f"Dashboard Executivo — {tenant_name}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (
        f'Período: {data["period"]["start"]} → {data["period"]["end"]} · '
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M}"
    )
    ws["A2"].font = Font(italic=True, color="6B7280")

    # KPIs
    row = _section(ws, "Indicadores", row=4)
    ws.append(["Indicador", "Atual", "Período anterior", "Variação %"])
    _style_header(ws, 4)
    for label, key in [
        ("Faturamento", "revenue"),
        ("Lucro líquido", "net_profit"),
        ("Ticket médio", "avg_ticket"),
        ("Nº de vendas", "num_sales"),
    ]:
        k = data[key]
        ws.append([label, k["current"], k["previous"], k["change_pct"]])

    ws.append([])
    ws.append(["Inadimplência (%)", data["overdue_rate"]])
    _ = row  # quiet linter

    # Revenue by month
    ws_m = wb.create_sheet("Faturamento por mês")
    ws_m.append(["Mês", "Faturamento (R$)", "Nº de vendas"])
    _style_header(ws_m, 3)
    for m in data["revenue_by_month"]:
        ws_m.append([m["month"], m["revenue"], m["sales_count"]])
    _auto_size(ws_m, 3)

    # Top customers
    ws_c = wb.create_sheet("Top clientes")
    ws_c.append(["Posição", "Cliente", "Total (R$)", "Vendas"])
    _style_header(ws_c, 4)
    for i, c in enumerate(data["top_customers"], 1):
        ws_c.append([i, c["name"], c["total"], c["sales"]])
    _auto_size(ws_c, 4)

    # Top products
    ws_p = wb.create_sheet("Top produtos")
    ws_p.append(["Posição", "Produto", "Total (R$)", "Quantidade"])
    _style_header(ws_p, 4)
    for i, p in enumerate(data["top_products"], 1):
        ws_p.append([i, p["name"], p["total"], p["quantity"]])
    _auto_size(ws_p, 4)

    _auto_size(ws, 4)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def financial_to_excel(data: dict, tenant_name: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Resumo"
    ws["A1"] = f"Dashboard Financeiro — {tenant_name}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = (
        f'Período: {data["period"]["start"]} → {data["period"]["end"]} · '
        f"Gerado em {datetime.now():%d/%m/%Y %H:%M}"
    )
    ws["A2"].font = Font(italic=True, color="6B7280")

    ws.append([])
    ws.append(["Indicador", "Atual", "Anterior", "Variação %"])
    _style_header(ws, 4)
    # ws.append empurra header pra última linha — re-aplica
    for label, key in [("Entradas", "cash_in"), ("Saídas", "cash_out"), ("Lucro líquido", "net_profit")]:
        k = data[key]
        ws.append([label, k["current"], k["previous"], k["change_pct"]])
    ws.append([])
    ws.append(["Inadimplência (%)", data["overdue_rate"]])
    _auto_size(ws, 4)

    ws_cf = wb.create_sheet("Fluxo de caixa")
    ws_cf.append(["Mês", "Entradas", "Saídas", "Saldo"])
    _style_header(ws_cf, 4)
    for m in data["cashflow_by_month"]:
        ws_cf.append([m["month"], m["in"], m["out"], m["net"]])
    _auto_size(ws_cf, 4)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def commercial_to_excel(data: dict, tenant_name: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Resumo"
    ws["A1"] = f"Dashboard Comercial — {tenant_name}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f'Período: {data["period"]["start"]} → {data["period"]["end"]}'

    ws.append([])
    ws.append(["Indicador", "Atual", "Anterior", "Variação %"])
    _style_header(ws, 4)
    for label, key in [("Faturamento", "revenue"), ("Nº de vendas", "num_sales"), ("Ticket médio", "avg_ticket")]:
        k = data[key]
        ws.append([label, k["current"], k["previous"], k["change_pct"]])
    _auto_size(ws, 4)

    ws_sp = wb.create_sheet("Por vendedor")
    ws_sp.append(["Posição", "Vendedor", "Total (R$)", "Vendas"])
    _style_header(ws_sp, 4)
    for i, s in enumerate(data["by_salesperson"], 1):
        ws_sp.append([i, s["name"], s["total"], s["sales"]])
    _auto_size(ws_sp, 4)

    ws_c = wb.create_sheet("Top clientes")
    ws_c.append(["Posição", "Cliente", "Total (R$)", "Vendas"])
    _style_header(ws_c, 4)
    for i, c in enumerate(data["top_customers"], 1):
        ws_c.append([i, c["name"], c["total"], c["sales"]])
    _auto_size(ws_c, 4)

    ws_p = wb.create_sheet("Top produtos")
    ws_p.append(["Posição", "Produto", "Total (R$)", "Quantidade"])
    _style_header(ws_p, 4)
    for i, p in enumerate(data["top_products"], 1):
        ws_p.append([i, p["name"], p["total"], p["quantity"]])
    _auto_size(ws_p, 4)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ===========================================================================
# HTML printable — usuário usa Ctrl+P → "Salvar como PDF"
# ===========================================================================
def _fmt_brl(v: float | int) -> str:
    s = f"{float(v):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:+.1f}%".replace(".", ",")


def _kpi_html(label: str, k: dict[str, Any], *, currency: bool = True) -> str:
    val = _fmt_brl(k["current"]) if currency else f"{int(k['current']):,}".replace(",", ".")
    change = _fmt_pct(k["change_pct"])
    return f"""
    <div class="kpi">
      <p class="label">{label}</p>
      <p class="value">{val}</p>
      <p class="change">{change} vs período anterior</p>
    </div>"""


_BASE_CSS = """
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: #0a0a0a;
         max-width: 900px; margin: 32px auto; padding: 0 24px; }
  h1 { font-size: 24px; margin-bottom: 4px; }
  .subtitle { color: #6b7280; margin-bottom: 32px; }
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 16px 0 32px; }
  .kpi { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
  .kpi .label { font-size: 10px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin: 0; }
  .kpi .value { font-size: 22px; font-weight: 700; margin: 8px 0 4px; }
  .kpi .change { font-size: 11px; color: #6b7280; margin: 0; }
  h2 { font-size: 16px; margin: 32px 0 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  table th, table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }
  table th { background: #f9fafb; font-weight: 600; color: #374151; }
  table td.num { text-align: right; font-variant-numeric: tabular-nums; }
  .brand { color: #2563eb; font-weight: 700; }
  .footer { margin-top: 48px; padding-top: 16px; border-top: 1px solid #e5e7eb;
            color: #9ca3af; font-size: 11px; text-align: center; }
  @media print {
    .no-print { display: none; }
    body { margin: 0; padding: 0 16px; }
  }
"""


def _render_html(title: str, tenant_name: str, data: dict, sections: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR"><head>
<meta charset="utf-8"/>
<title>{title} — {tenant_name}</title>
<style>{_BASE_CSS}</style>
</head><body>
  <div class="no-print" style="margin-bottom: 16px; text-align: right;">
    <button onclick="window.print()" style="padding: 8px 16px; background: #2563eb; color: white;
      border: 0; border-radius: 6px; cursor: pointer; font-weight: 600;">
      Imprimir / Salvar como PDF
    </button>
  </div>
  <h1>{title}</h1>
  <p class="subtitle">
    <span class="brand">{tenant_name}</span> ·
    Período: {data['period']['start']} → {data['period']['end']} ·
    Gerado em {datetime.now():%d/%m/%Y %H:%M}
  </p>
  {sections}
  <p class="footer">Relatório gerado por <span class="brand">BlueMetrics</span></p>
</body></html>"""


def executive_to_html(data: dict, tenant_name: str) -> str:
    kpis_html = (
        '<div class="kpis">'
        + _kpi_html("Faturamento", data["revenue"])
        + _kpi_html("Lucro líquido", data["net_profit"])
        + _kpi_html("Ticket médio", data["avg_ticket"])
        + _kpi_html("Nº de vendas", data["num_sales"], currency=False)
        + "</div>"
    )

    rows_rev = "".join(
        f'<tr><td>{m["month"]}</td><td class="num">{_fmt_brl(m["revenue"])}</td>'
        f'<td class="num">{m["sales_count"]}</td></tr>'
        for m in data["revenue_by_month"]
    )
    rev_tbl = (
        '<h2>Faturamento por mês</h2>'
        '<table><thead><tr><th>Mês</th><th class="num">Faturamento</th>'
        '<th class="num">Vendas</th></tr></thead><tbody>'
        + rows_rev + "</tbody></table>"
    )

    rows_c = "".join(
        f'<tr><td>#{i + 1} {c["name"]}</td><td class="num">{_fmt_brl(c["total"])}</td>'
        f'<td class="num">{c["sales"]}</td></tr>'
        for i, c in enumerate(data["top_customers"])
    )
    c_tbl = (
        '<h2>Top clientes</h2><table><thead><tr><th>Cliente</th>'
        '<th class="num">Total</th><th class="num">Vendas</th></tr></thead>'
        '<tbody>' + rows_c + "</tbody></table>"
    )

    rows_p = "".join(
        f'<tr><td>#{i + 1} {p["name"]}</td><td class="num">{_fmt_brl(p["total"])}</td>'
        f'<td class="num">{p["quantity"]:.0f}</td></tr>'
        for i, p in enumerate(data["top_products"])
    )
    p_tbl = (
        '<h2>Top produtos</h2><table><thead><tr><th>Produto</th>'
        '<th class="num">Total</th><th class="num">Quantidade</th></tr></thead>'
        '<tbody>' + rows_p + "</tbody></table>"
    )

    return _render_html("Dashboard Executivo", tenant_name, data, kpis_html + rev_tbl + c_tbl + p_tbl)


def financial_to_html(data: dict, tenant_name: str) -> str:
    kpis_html = (
        '<div class="kpis">'
        + _kpi_html("Entradas", data["cash_in"])
        + _kpi_html("Saídas", data["cash_out"])
        + _kpi_html("Lucro líquido", data["net_profit"])
        + f'<div class="kpi"><p class="label">Inadimplência</p>'
          f'<p class="value">{data["overdue_rate"]:.2f}%</p><p class="change">&nbsp;</p></div>'
        + "</div>"
    )

    rows = "".join(
        f'<tr><td>{m["month"]}</td><td class="num">{_fmt_brl(m["in"])}</td>'
        f'<td class="num">{_fmt_brl(m["out"])}</td>'
        f'<td class="num">{_fmt_brl(m["net"])}</td></tr>'
        for m in data["cashflow_by_month"]
    )
    cf_tbl = (
        '<h2>Fluxo de caixa</h2><table><thead><tr><th>Mês</th>'
        '<th class="num">Entradas</th><th class="num">Saídas</th>'
        '<th class="num">Saldo</th></tr></thead><tbody>' + rows + "</tbody></table>"
    )

    return _render_html("Dashboard Financeiro", tenant_name, data, kpis_html + cf_tbl)


def commercial_to_html(data: dict, tenant_name: str) -> str:
    kpis_html = (
        '<div class="kpis" style="grid-template-columns: repeat(3, 1fr);">'
        + _kpi_html("Faturamento", data["revenue"])
        + _kpi_html("Nº de vendas", data["num_sales"], currency=False)
        + _kpi_html("Ticket médio", data["avg_ticket"])
        + "</div>"
    )

    rows_sp = "".join(
        f'<tr><td>#{i + 1} {s["name"]}</td><td class="num">{_fmt_brl(s["total"])}</td>'
        f'<td class="num">{s["sales"]}</td></tr>'
        for i, s in enumerate(data["by_salesperson"])
    )
    sp_tbl = (
        '<h2>Vendas por vendedor</h2><table><thead><tr><th>Vendedor</th>'
        '<th class="num">Total</th><th class="num">Vendas</th></tr></thead>'
        '<tbody>' + rows_sp + "</tbody></table>"
    )

    return _render_html("Dashboard Comercial", tenant_name, data, kpis_html + sp_tbl)
