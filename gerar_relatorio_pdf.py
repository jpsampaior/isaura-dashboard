"""
Gera o PDF do Relatório de Engenharia a partir de insumos_relatorio.json.
Execute: python analise_insumos.py && python gerar_relatorio_pdf.py
"""

import json
from pathlib import Path

from fpdf import FPDF

INSUMOS = Path(__file__).parent / "insumos_relatorio.json"
PDF_OUT = Path(__file__).parent / "Relatorio_Engenharia_BI_Incidentes.pdf"
FONT = Path("C:/Windows/Fonts/arial.ttf")


class RelatorioPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Arial", "", str(FONT))
        self.set_font("Arial", "", 11)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 9)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def linha(pdf: FPDF, texto: str, h: float = 6, size: int = 11) -> None:
    pdf.set_font("Arial", "", size)
    pdf.multi_cell(pdf.epw, h, texto)


def secao(pdf: FPDF, titulo: str) -> None:
    pdf.ln(4)
    linha(pdf, titulo, size=12)


def main() -> None:
    dados = json.loads(INSUMOS.read_text(encoding="utf-8"))
    meta = dados["meta_etl"]
    k = dados["kpis"]
    g = dados["gargalo_equipe"]
    s = dados["sintoma_mais_recorrente"]
    pico = dados["mes_pico_aberturas"]
    ev = dados["equipe_maior_volume"]
    pct_sint = dados.get("pct_volume_sintoma_lider", 0)

    pdf = RelatorioPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    linha(pdf, "Relatorio de Engenharia", size=14)
    pdf.set_font("Arial", "", 11)
    linha(pdf, "BI Aplicado a Gestao de Incidentes (ITIL)")
    linha(pdf, "Gerenciamento da Implantacao de Sistemas")
    pdf.ln(4)

    secao(pdf, "1. Tratamentos de ETL aplicados")
    linha(
        pdf,
        "Fonte: incident_event_log.csv (log ServiceNow, 119.999 linhas historicas).\n"
        "Transformacoes antes do painel:",
    )
    for item in [
        "Substituicao de '?' por nulo em resolved_at, assignment_group e u_symptom.",
        f"Deduplicacao: 1 linha por number com maior sys_mod_count "
        f"({meta['chamados_unicos']:,} chamados na tabela fato).",
        f"Resolved/Closed sem resolved_at preenchidos com closed_at "
        f"({meta['preenchidos_closed_at']:,} registros).",
        f"Tabela D_Calendario com {meta['dias_calendario']} dias "
        f"({meta['periodo_inicio']} a {meta['periodo_fim']}).",
        "Campo derivado mttr_horas = resolved_at - opened_at.",
    ]:
        linha(pdf, f"- {item}")

    secao(pdf, "2. Indicadores consolidados")
    linha(
        pdf,
        f"Chamados unicos: {k['total_chamados']:,}\n"
        f"MTTR medio: {k['mttr_medio_horas']} h | mediana: {k['mttr_mediana_horas']} h\n"
        f"SLA cumprido: {k['sla_conformidade_pct']}%\n"
        f"Prioridade critica: {k['chamados_criticos']:,} ({k['pct_criticos']}%)",
    )

    secao(pdf, "3. Analise critica e gargalo tecnico")
    linha(
        pdf,
        f"Somente {k['sla_conformidade_pct']}% dos chamados cumpriram SLA. "
        f"A mediana de MTTR (30 h) e bem menor que a media ({k['mttr_medio_horas']} h), "
        f"indicando filas com casos extremos puxando o tempo de atendimento.",
    )
    linha(
        pdf,
        f"Em {pico['mes']} houve pico de {pico['volume']:,} aberturas, "
        f"exigindo capacidade extra no periodo.",
    )
    linha(
        pdf,
        f"Causa raiz mais provavel (Gestao de Problemas ITIL): "
        f"{s.get('sintoma', 'N/A')} com {int(s.get('volume', 0)):,} chamados "
        f"({pct_sint}% do total). Tratar esse sintoma reduz reincidencia.",
    )
    linha(
        pdf,
        f"Maior carga operacional: {ev.get('assignment_group')} "
        f"({int(ev.get('volume', 0)):,} chamados, SLA {ev.get('sla_pct')}%).",
    )
    if g:
        linha(
            pdf,
            f"Principal gargalo de desempenho (volume >= {50} e SLA baixo): "
            f"{g.get('assignment_group')} - {int(g.get('volume', 0)):,} chamados, "
            f"MTTR {g.get('mttr_horas')} h, SLA {g.get('sla_pct')}%. "
            f"Recomendacao: revisar capacidade, escalonamento e runbooks dessa equipe.",
        )

    secao(pdf, "4. Top 5 sintomas")
    for row in dados.get("top_5_sintomas", []):
        linha(pdf, f"- {row['sintoma']}: {row['volume']:,}")

    secao(pdf, "5. Top 5 equipes por volume")
    for row in dados.get("top_5_equipes_volume", []):
        linha(
            pdf,
            f"- {row['assignment_group']}: {int(row['volume']):,} chamados | "
            f"MTTR {row['mttr_horas']} h | SLA {row['sla_pct']}%",
        )

    secao(pdf, "6. Conclusao")
    linha(
        pdf,
        "O dashboard Streamlit (app.py) apresenta KPIs e graficos da atividade. "
        "Prioridades: (1) atacar o sintoma mais recorrente na gestao de problemas; "
        "(2) melhorar SLA/MTTR na equipe gargalo; (3) planejar capacidade no mes de pico.",
    )

    pdf.output(str(PDF_OUT))
    print(f"PDF gerado: {PDF_OUT}")


if __name__ == "__main__":
    if not INSUMOS.exists():
        raise SystemExit("Execute primeiro: python analise_insumos.py")
    main()
