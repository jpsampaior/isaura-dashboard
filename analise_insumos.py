"""
Gera insumos verídicos para o Relatório de Engenharia (PDF).
Execute: python analise_insumos.py
"""

import json
from pathlib import Path

import pandas as pd

from etl_core import run_etl

OUT = Path(__file__).parent / "insumos_relatorio.json"
MIN_VOLUME_EQUIPE = 50


def analisar(fato: pd.DataFrame, meta: dict) -> dict:
    total = len(fato)
    sla_pct = round(fato["made_sla"].mean() * 100, 1)
    mttr_medio = round(fato["mttr_horas"].mean(), 1)
    mttr_mediana = round(fato["mttr_horas"].median(), 1)
    criticos = int((fato["priority"] == "1 - Critical").sum())
    pct_criticos = round(100 * criticos / total, 1)

    prioridade = (
        fato["priority"].value_counts().sort_index().astype(int).to_dict()
    )

    top_sintomas = (
        fato["u_symptom"].dropna().value_counts().head(10).reset_index()
    )
    top_sintomas.columns = ["sintoma", "volume"]
    sintoma_lider = top_sintomas.iloc[0].to_dict() if len(top_sintomas) else {}

    por_mes = (
        fato.assign(mes=fato["opened_at"].dt.to_period("M").astype(str))
        .groupby("mes")["number"]
        .count()
        .sort_values(ascending=False)
    )
    mes_pico = por_mes.index[0] if len(por_mes) else ""
    vol_mes_pico = int(por_mes.iloc[0]) if len(por_mes) else 0

    equipes = (
        fato.dropna(subset=["assignment_group"])
        .groupby("assignment_group")
        .agg(
            volume=("number", "count"),
            mttr_horas=("mttr_horas", "mean"),
            sla_pct=("made_sla", lambda s: round(s.mean() * 100, 1)),
        )
        .reset_index()
    )
    equipes_grandes = equipes[equipes["volume"] >= MIN_VOLUME_EQUIPE].copy()
    equipes_grandes["mttr_horas"] = equipes_grandes["mttr_horas"].round(1)

    media_mttr = fato["mttr_horas"].mean()

    # Gargalo operacional: alto volume e baixo SLA (impacto real na fila)
    cand = equipes_grandes.copy()
    cand["pressao"] = cand["volume"] * (100 - cand["sla_pct"])
    gargalo_equipe = (
        cand.sort_values("pressao", ascending=False).iloc[0].to_dict() if len(cand) else {}
    )

    maior_volume = equipes.sort_values("volume", ascending=False).iloc[0].to_dict()
    pct_sintoma_lider = round(100 * sintoma_lider.get("volume", 0) / total, 1) if total else 0

    sem_equipe = int(fato["assignment_group"].isna().sum())
    sem_sintoma = int(fato["u_symptom"].isna().sum())

    return {
        "meta_etl": meta,
        "kpis": {
            "total_chamados": total,
            "mttr_medio_horas": mttr_medio,
            "mttr_mediana_horas": mttr_mediana,
            "sla_conformidade_pct": sla_pct,
            "chamados_criticos": criticos,
            "pct_criticos": pct_criticos,
        },
        "prioridade_distribuicao": prioridade,
        "sintoma_mais_recorrente": sintoma_lider,
        "top_5_sintomas": top_sintomas.head(5).to_dict(orient="records"),
        "mes_pico_aberturas": {"mes": mes_pico, "volume": vol_mes_pico},
        "equipe_maior_volume": maior_volume,
        "gargalo_equipe": gargalo_equipe,
        "pct_volume_sintoma_lider": pct_sintoma_lider,
        "top_5_equipes_volume": equipes.sort_values("volume", ascending=False)
        .head(5)
        .round(1)
        .to_dict(orient="records"),
        "pior_5_equipes_sla": equipes_grandes.sort_values("sla_pct")
        .head(5)
        .round(1)
        .to_dict(orient="records"),
        "qualidade_dados": {
            "sem_assignment_group": sem_equipe,
            "sem_u_symptom": sem_sintoma,
            "media_mttr_geral": round(media_mttr, 1),
        },
    }


def main() -> None:
    fato, _, meta = run_etl()
    insumos = analisar(fato, meta)
    OUT.write_text(json.dumps(insumos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Insumos salvos em: {OUT}")
    print(json.dumps(insumos["kpis"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
