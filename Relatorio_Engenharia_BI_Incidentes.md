# Relatório de Engenharia — BI Gestão de Incidentes (ITIL)

**Disciplina:** Gerenciamento da Implantação de Sistemas  
**Fonte de dados:** `incident_event_log.csv` (log ServiceNow, 119,998 linhas)

---

## 1. Tratamentos de ETL aplicados

| Etapa | Descrição |
|-------|-----------|
| Limpeza de `?` | Substituído por nulo em `resolved_at`, `assignment_group` e `u_symptom` |
| Deduplicação | 1 linha por `number` com maior `sys_mod_count` → **20,769** chamados na tabela fato |
| Resolução inconsistente | Chamados Resolved/Closed sem `resolved_at` preenchidos com `closed_at` (**1,418** registros) |
| D_Calendario | **75** dias (2016-02-29 a 2016-05-13) vinculados à data de abertura |
| Campo derivado | `mttr_horas` = diferença entre `resolved_at` e `opened_at` |

---

## 2. Indicadores consolidados

| Indicador | Valor |
|-----------|-------|
| Chamados únicos | 20,769 |
| MTTR médio | 186.5 h |
| MTTR mediana | 30.0 h |
| Conformidade SLA | 60.6% |
| Chamados críticos (1 - Critical) | 220 (1.1%) |

**Distribuição por prioridade**

| Prioridade | Quantidade |
|------------|------------|
| 1 - Critical | 220 |
| 2 - High | 337 |
| 3 - Moderate | 19,554 |
| 4 - Low | 658 |

---

## 3. Análise crítica e gargalo técnico

- Apenas **60.6%** dos chamados cumpriram o SLA. A mediana de MTTR (**30.0 h**) é muito menor que a média (**186.5 h**), o que indica casos extremos alongando o tempo de atendimento.

- **Pico de demanda:** em **2016-03** foram abertos **8,995** chamados.

- **Gestão de Problemas (ITIL):** o sintoma **Symptom 491** concentra **7,856** ocorrências (**37.8%** do total). É a principal causa recorrente a ser tratada na origem.

- **Maior carga operacional:** **Group 70** com **7,369** chamados (SLA 81.4%).

- **Principal gargalo de desempenho** (equipes com volume ≥ 200 e menor SLA): **Group 10** — **271** chamados, MTTR **702.3 h**, SLA **14.4%**. Recomenda-se revisar capacidade, escalonamento e runbooks dessa equipe.

---

## 4. Top 5 sintomas mais recorrentes

| Sintoma | Volume |
|---------|--------|
| Symptom 491 | 7,856 |
| Symptom 534 | 1,285 |
| Symptom 116 | 425 |
| Symptom 387 | 384 |
| Symptom 4 | 368 |

---

## 5. Top 5 equipes por volume

| Equipe | Chamados | MTTR (h) | SLA (%) |
|--------|----------|----------|---------|
| Group 70 | 7,369 | 76.4 | 81.4 |
| Group 25 | 1,080 | 255.4 | 42.8 |
| Group 39 | 995 | 80.0 | 63.8 |
| Group 24 | 907 | 135.5 | 62.8 |
| Group 23 | 745 | 242.8 | 57.7 |

---

## 6. Equipes com pior SLA (referência)

| Equipe | Chamados | MTTR (h) | SLA (%) |
|--------|----------|----------|---------|
| Group 9 | 71 | 4192.6 | 2.8 |
| Group 75 | 53 | 689.3 | 5.7 |
| Group 12 | 98 | 351.7 | 7.1 |
| Group 10 | 271 | 702.3 | 14.4 |
| Group 3 | 89 | 1330.0 | 18.0 |

---

## 7. Qualidade dos dados

| Item | Quantidade |
|------|------------|
| Chamados sem `assignment_group` | 2,157 |
| Chamados sem `u_symptom` | 4,931 |

---

## 8. Conclusão

O dashboard Streamlit (`app.py`) apresenta os KPIs e gráficos exigidos na atividade. Com base nos dados tratados, as prioridades são:

1. Atacar o sintoma mais recorrente na gestão de problemas.
2. Melhorar SLA e MTTR na equipe gargalo (**Group 10**).
3. Planejar capacidade no mês de pico (**2016-03**).
