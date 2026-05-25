"""ETL compartilhado entre dashboard e relatório."""

from pathlib import Path

import pandas as pd

DATA_FILE = Path(__file__).parent / "incident_event_log.csv"
ETL_NULL_COLS = ["resolved_at", "assignment_group", "u_symptom"]
RESOLVED_STATES = {"Resolved", "Closed"}


def run_etl() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    log = pd.read_csv(DATA_FILE, na_values=["?", ""], low_memory=False)

    for col in ETL_NULL_COLS:
        log[col] = log[col].replace("?", pd.NA)

    log["made_sla"] = (
        log["made_sla"].astype(str).str.strip().str.lower().map({"true": True, "false": False})
    )
    for col in ["opened_at", "resolved_at", "closed_at"]:
        log[col] = pd.to_datetime(log[col], dayfirst=True, errors="coerce")

    idx = log.groupby("number")["sys_mod_count"].idxmax()
    fato = log.loc[idx].copy()

    sem_resolucao = fato["incident_state"].isin(RESOLVED_STATES) & fato["resolved_at"].isna()
    fato.loc[sem_resolucao, "resolved_at"] = fato.loc[sem_resolucao, "closed_at"]

    fato["mttr_horas"] = (fato["resolved_at"] - fato["opened_at"]).dt.total_seconds() / 3600
    fato["data_abertura"] = fato["opened_at"].dt.normalize()

    min_d, max_d = fato["data_abertura"].min(), fato["data_abertura"].max()
    d_cal = pd.DataFrame({"data": pd.date_range(min_d, max_d, freq="D")})

    meta = {
        "linhas_log": len(log),
        "chamados_unicos": int(fato["number"].nunique()),
        "preenchidos_closed_at": int(sem_resolucao.sum()),
        "periodo_inicio": str(min_d.date()),
        "periodo_fim": str(max_d.date()),
        "dias_calendario": len(d_cal),
    }
    return fato, d_cal, meta
