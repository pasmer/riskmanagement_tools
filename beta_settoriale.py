# Elaborato da ChatGPT-5
import io
import sys
import math
import time
import json
import zipfile
from dataclasses import dataclass
from typing import List, Dict, Tuple
import requests
import pandas as pd

BASE_CURRENT = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/"
BASE_ARCH    = "https://pages.stern.nyu.edu/~adamodar/pc/archives/"

# Mappa "geografia Damodaran" -> prefisso file
# Nota: "US" usa "betas.xls" (senza suffisso); per archivi usa betasYY.xls
GEOGRAPHY_FILE = {
    "US":       {"current": "betas.xls",        "arch_fmt": "betas{yy}.xls"},
    "Europe":   {"current": "betaEurope.xls",   "arch_fmt": "betaEurope{yy}.xls"},
    "Japan":    {"current": "betaJapan.xls",    "arch_fmt": "betaJapan{yy}.xls"},
    "Global":   {"current": "betaGlobal.xls",   "arch_fmt": "betaGlobal{yy}.xls"},
    "Emerging": {"current": "betaemerg.xls",    "arch_fmt": "betaemerg{yy}.xls"},
    "India":    {"current": "betaIndia.xls",    "arch_fmt": "betaIndia{yy}.xls"},
    "China":    {"current": "indregChina.xls",  "arch_fmt": "indregChina{yy}.xls"},  # (betaChina non sempre presente; vedi nota sotto)
    "Rest":     {"current": "betaRest.xls",     "arch_fmt": "betaRest{yy}.xls"},     # Aus/NZ/Canada in Damodaran = "Rest" nei dataset
}

# Alcuni anni/regioni potrebbero non avere il file; gestiamo con fallback
def fetch_excel(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.read_excel(io.BytesIO(r.content), engine="xlrd")

def year_to_yy(year: int) -> str:
    # nei file d'archivio Damodaran usa spesso due cifre (es. 2023 -> 23)
    return str(year)[-2:]

def load_damodaran_betas(geo: str, year: int) -> pd.DataFrame:
    meta = GEOGRAPHY_FILE[geo]
    if year is None:
        url = BASE_CURRENT + meta["current"]
    else:
        url = BASE_ARCH + meta["arch_fmt"].format(yy=year_to_yy(year))
    try:
        df = fetch_excel(url)
        # Normalizziamo i nomi colonne più usati
        cols = {c: c.strip() for c in df.columns}
        df.rename(columns=cols, inplace=True)
        # Le intestazioni tipiche: "Industry Name", "Number of firms", "Beta", "D/E Ratio", "Tax rate" / "Effective Tax rate" ...
        # Filtra righe valide
        for col in ["Industry Name", "Beta"]:
            if col not in df.columns:
                raise KeyError(f"Colonna {col} non trovata in {url}")
        # Rimuovi totali e righe non settoriali, se presenti
        mask_valid = df["Industry Name"].astype(str).str.lower().str.contains("total market") == False
        df = df.loc[mask_valid].copy()
        df["Year"] = year
        df["Geography"] = geo
        # Harmonize numero aziende
        nf_col = "Number of firms" if "Number of firms" in df.columns else None
        if nf_col:
            df["Number of firms"] = pd.to_numeric(df[nf_col], errors="coerce")
        # Beta levered
        df["Beta"] = pd.to_numeric(df["Beta"], errors="coerce")
        return df[["Industry Name", "Beta", "Number of firms", "Year", "Geography"]]
    except Exception as e:
        raise RuntimeError(f"Errore nel leggere {url}: {e}")

def compute_average_beta(geos: List[str],
                         start_year: int,
                         end_year: int,
                         weight_by_firms: bool = False) -> pd.DataFrame:
    frames = []
    for geo in geos:
        for y in range(start_year, end_year + 1):
            try:
                frames.append(load_damodaran_betas(geo, y))
            except RuntimeError as err:
                # Se un file d'archivio non esiste per quell'anno/geo, salta con warning
                print(f"[WARN] {err}", file=sys.stderr)
                continue
    if not frames:
        raise RuntimeError("Nessun dataset caricato. Controlla geografie e anni.")

    data = pd.concat(frames, ignore_index=True)
    # Aggregazione per settore & geografia
    def agg_fun(g):
        if not weight_by_firms:
            avg_beta = g["Beta"].mean(skipna=True)
        else:
            w = g["Number of firms"].fillna(0)
            b = g["Beta"].fillna(pd.NA)
            if w.sum() > 0:
                avg_beta = (b * w).sum(skipna=True) / w.where(~b.isna(), 0).sum()
            else:
                avg_beta = b.mean(skipna=True)
        # statistica accessoria
        return pd.Series({
            "AvgLeveredBeta": avg_beta,
            "YearsObs": g["Year"].nunique(),
            "AvgFirms": g["Number of firms"].mean(skipna=True)
        })

    out = (data
           .groupby(["Geography", "Industry Name"], as_index=False)
           .apply(agg_fun)
           .reset_index(drop=True))

    out["StartYear"] = start_year
    out["EndYear"] = end_year
    out = out[["Geography", "Industry Name", "StartYear", "EndYear", "AvgLeveredBeta", "YearsObs", "AvgFirms"]]
    return out.sort_values(["Geography", "Industry Name"]).reset_index(drop=True)

# Esempio d’uso:
geos = ["US", "Europe"]            # Italia -> usare "Europe" come proxy
result = compute_average_beta(geos, start_year=2021, end_year=2025, weight_by_firms=True)
print(result.head(20))
result.to_csv("average_levered_beta_sector.csv", index=False)
