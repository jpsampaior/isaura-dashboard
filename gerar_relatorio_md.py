"""
Gera o Relatório de Engenharia em Markdown.
Execute: python analise_insumos.py && python gerar_relatorio_md.py
"""

import json
from pathlib import Path

INSUMOS = Path(__file__).parent / "insumos_relatorio.json"
MD_OUT = Path(__file__).parent / "Relatorio_Engenharia_BI_Incidentes.md"


def tabela_equipes(rows: list) -> str:
    linhas = ["| Equipe | Chamados | MTTR (h) | SLA (%) |", "|--------|----------|----------|---------|"]
    for r in rows:
        linhas.append(
            f"| {r['assignment_group']} | {int(r['volume']):,} | {r['mttr_horas']} | {r['sla_pct']} |"
        )
    return "\n".join(linhas)


def main() -> None:
    dados = json.loads(INSUMOS.read_text(encoding="utf-8"))
    meta = dados["meta_etl"]
    k = dados["kpis"]
    g = dados["gargalo_equipe"]
    s = dados["sintoma_mais_recorrente"]
    pico = dados["mes_pico_aberturas"]
    ev = dados["equipe_maior_volume"]
    pct_sint = dados.get("pct_volume_sintoma_lider", 0)

    md = f"""# Relatório de Engenharia — BI Gestão de Incidentes (ITIL)

**Disciplina:** Gerenciamento da Implantação de Sistemas  
**Fonte de dados:** `incident_event_log.csv` (log ServiceNow, {meta['linhas_log']:,} linhas)

---

## 1. Tratamentos de ETL aplicados

| Etapa | Descrição |
|-------|-----------|
| Limpeza de `?` | Substituído por nulo em `resolved_at`, `assignment_group` e `u_symptom` |
| Deduplicação | 1 linha por `number` com maior `sys_mod_count` → **{meta['chamados_unicos']:,}** chamados na tabela fato |
| Resolução inconsistente | Chamados Resolved/Closed sem `resolved_at` preenchidos com `closed_at` (**{meta['preenchidos_closed_at']:,}** registros) |
| D_Calendario | **{meta['dias_calendario']}** dias ({meta['periodo_inicio']} a {meta['periodo_fim']}) vinculados à data de abertura |
| Campo derivado | `mttr_horas` = diferença entre `resolved_at` e `opened_at` |

---

## 2. Indicadores consolidados

| Indicador | Valor |
|-----------|-------|
| Chamados únicos | {k['total_chamados']:,} |
| MTTR médio | {k['mttr_medio_horas']} h |
| MTTR mediana | {k['mttr_mediana_horas']} h |
| Conformidade SLA | {k['sla_conformidade_pct']}% |
| Chamados críticos (1 - Critical) | {k['chamados_criticos']:,} ({k['pct_criticos']}%) |

**Distribuição por prioridade**

| Prioridade | Quantidade |
|------------|------------|
"""

    for prio, qtd in dados["prioridade_distribuicao"].items():
        md += f"| {prio} | {qtd:,} |\n"

    md += f"""
---

## 3. Análise crítica e gargalo técnico

- Apenas **{k['sla_conformidade_pct']}%** dos chamados cumpriram o SLA. A mediana de MTTR (**{k['mttr_mediana_horas']} h**) é muito menor que a média (**{k['mttr_medio_horas']} h**), o que indica casos extremos alongando o tempo de atendimento.

- **Pico de demanda:** em **{pico['mes']}** foram abertos **{pico['volume']:,}** chamados.

- **Gestão de Problemas (ITIL):** o sintoma **{s.get('sintoma')}** concentra **{int(s.get('volume', 0)):,}** ocorrências (**{pct_sint}%** do total). É a principal causa recorrente a ser tratada na origem.

- **Maior carga operacional:** **{ev.get('assignment_group')}** com **{int(ev.get('volume', 0)):,}** chamados (SLA {ev.get('sla_pct')}%).

- **Principal gargalo de desempenho** (equipes com volume ≥ 200 e menor SLA): **{g.get('assignment_group')}** — **{int(g.get('volume', 0)):,}** chamados, MTTR **{round(g.get('mttr_horas', 0), 1)} h**, SLA **{g.get('sla_pct')}%**. Recomenda-se revisar capacidade, escalonamento e runbooks dessa equipe.

---

## 4. Top 5 sintomas mais recorrentes

| Sintoma | Volume |
|---------|--------|
"""

    for row in dados["top_5_sintomas"]:
        md += f"| {row['sintoma']} | {row['volume']:,} |\n"

    md += f"""
---

## 5. Top 5 equipes por volume

{tabela_equipes(dados['top_5_equipes_volume'])}

---

## 6. Equipes com pior SLA (referência)

{tabela_equipes(dados['pior_5_equipes_sla'])}

---

## 7. Qualidade dos dados

| Item | Quantidade |
|------|------------|
| Chamados sem `assignment_group` | {dados['qualidade_dados']['sem_assignment_group']:,} |
| Chamados sem `u_symptom` | {dados['qualidade_dados']['sem_u_symptom']:,} |

---

## 8. Conclusão

O dashboard Streamlit (`app.py`) apresenta os KPIs e gráficos exigidos na atividade. Com base nos dados tratados, as prioridades são:

1. Atacar o sintoma mais recorrente na gestão de problemas.
2. Melhorar SLA e MTTR na equipe gargalo (**{g.get('assignment_group')}**).
3. Planejar capacidade no mês de pico (**{pico['mes']}**).
"""

    MD_OUT.write_text(md, encoding="utf-8")
    print(f"Relatorio gerado: {MD_OUT}")


if __name__ == "__main__":
    if not INSUMOS.exists():
        raise SystemExit("Execute primeiro: python analise_insumos.py")
    main()
