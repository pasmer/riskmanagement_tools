#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script per calcolare la volatilità storica a 90 giorni del cambio USD/EUR
# Utilizzando i dati pubblici di FRED (Federal Reserve Economic Data)

import io
import sys
import argparse
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import requests


FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU"
# DEXUSEU = U.S. Dollars per One Euro  -> USD/EUR (autoritativo e daily)


def fetch_fred_series(url: str) -> pd.Series:
    """
    Scarica la serie da FRED in formato CSV pubblico e restituisce una Series con DateTimeIndex.
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "csv" not in content_type.lower():
        sample = resp.text[:200].replace("\n", " ")
        raise ValueError(
            f"Risposta inattesa da FRED (content-type: {content_type!r}, sample: {sample!r})"
        )

    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = [col.strip() for col in df.columns]
    lowered = {col.lower(): col for col in df.columns}

    date_key = lowered.get("date") or lowered.get("observation_date")
    if not date_key:
        raise ValueError(
            f"Colonna data non trovata nel CSV FRED. Colonne disponibili: {list(df.columns)}"
        )

    value_key = None
    for key, original in lowered.items():
        if key.startswith("dexuseu"):
            value_key = original
            break
    if not value_key:
        raise ValueError(
            f"Colonna DEXUSEU non trovata nel CSV FRED. Colonne disponibili: {list(df.columns)}"
        )

    df = df.rename(columns={date_key: "DATE", value_key: "DEXUSEU"})
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce", utc=True).dt.tz_convert(None)
    df["DEXUSEU"] = pd.to_numeric(df["DEXUSEU"].replace(".", np.nan), errors="coerce")
    df = df.dropna(subset=["DATE", "DEXUSEU"]).sort_values("DATE")

    if df.empty:
        raise ValueError("Serie FRED vuota dopo la pulizia dei dati.")

    return pd.Series(df["DEXUSEU"].values, index=df["DATE"], name="USD_per_EUR")


def compute_annualized_vol(series: pd.Series, window: int = 90, trading_days: int = 252):
    """
    Calcola volatilità storica annualizzata su 'window' rendimenti giornalieri logaritmici.
    Ritorna dict con risultati principali.
    """
    # Rendimenti logaritmici giornalieri
    rets = np.log(series / series.shift(1)).dropna()

    if len(rets) < window:
        raise ValueError(
            f"Osservazioni insufficienti ({len(rets)}) per una finestra di {window} rendimenti."
        )

    # Prendi gli ultimi 'window' rendimenti disponibili
    last_rets = rets.iloc[-window:]
    stdev_daily = last_rets.std(ddof=1)  # sample stdev
    vol_annualized = stdev_daily * np.sqrt(trading_days)

    out = {
        "window": window,
        "obs_count": int(last_rets.shape[0]),
        "start_date": last_rets.index[0].date().isoformat(),
        "end_date": last_rets.index[-1].date().isoformat(),
        "last_spot_date": series.index[-1].date().isoformat(),
        "last_spot": float(series.iloc[-1]),
        "stdev_daily": float(stdev_daily),
        "vol_annualized_252": float(vol_annualized),
        "vol_annualized_365": float(stdev_daily * np.sqrt(365)),  # opzionale, su base calendario
    }
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Volatilità storica a 90 giorni del cambio USD/EUR (FRED DEXUSEU)."
    )
    parser.add_argument(
        "--window",
        type=int,
        default=90,
        help="Numero di rendimenti giornalieri per la finestra (default: 90).",
    )
    parser.add_argument(
        "--save-csv",
        action="store_true",
        help="Se indicato, salva CSV con prezzi e rendimenti usati.",
    )
    args = parser.parse_args()

    # 1) Scarica serie da FRED
    try:
        series = fetch_fred_series(FRED_CSV_URL)
    except Exception as e:
        print(f"Errore nel download dati FRED: {e}", file=sys.stderr)
        sys.exit(1)

    # 2) Calcola vol
    try:
        res = compute_annualized_vol(series, window=args.window, trading_days=252)
    except Exception as e:
        print(f"Errore nel calcolo: {e}", file=sys.stderr)
        sys.exit(1)

    # 3) Output leggibile
    print("=== Volatilità storica USD/EUR (DEXUSEU, FRED) ===")
    print(f"Finestra rendimenti:          {res['window']} giorni (osservazioni effettive: {res['obs_count']})")
    print(f"Periodo rendimenti:           {res['start_date']} → {res['end_date']}")
    print(f"Ultimo spot disponibile:      {res['last_spot']:.6f} USD per EUR (data {res['last_spot_date']})")
    print(f"Deviazione std giornaliera:   {res['stdev_daily']:.6%}")
    print(f"Vol annualizzata (252):       {res['vol_annualized_252']:.2%}")
    print(f"Vol annualizzata (365):       {res['vol_annualized_365']:.2%}")

    # 4) (opzionale) salvataggio CSV con i dati usati
    if args.save_csv:
        df = series.to_frame()
        df["log_return"] = np.log(series / series.shift(1))
        # Filtra il periodo usato per la finestra calcolata
        mask = (df.index.date >= pd.to_datetime(res["start_date"]).date()) & (
            df.index.date <= pd.to_datetime(res["end_date"]).date()
        )
        df_used = df.loc[mask].copy()
        out_path = f"usd_eur_fred_window_{res['window']}d.csv"
        df_used.to_csv(out_path, index_label="date")
        print(f"Dati usati salvati in: {out_path}")


if __name__ == "__main__":
    main()
