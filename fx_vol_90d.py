#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script per calcolare la volatilità storica a 90 giorni del cambio USD/EUR o JPY/EUR
# Utilizzando i dati pubblici di FRED (Federal Reserve Economic Data)

import io
import sys
import argparse
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import requests


# DEXUSEU = U.S. Dollars per One Euro  -> USD/EUR (autoritativo e daily)
# DEXJPUS = Japanese Yen per One U.S. Dollar -> JPY/USD (autoritativo e daily)
FRED_URL_TEMPLATE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def fetch_fred_series(series_id: str) -> pd.Series:
    """
    Scarica la serie da FRED in formato CSV pubblico e restituisce una Series con DateTimeIndex.
    """
    url = FRED_URL_TEMPLATE.format(series_id=series_id)
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
    series_id_lower = series_id.lower()
    for key, original in lowered.items():
        if key.startswith(series_id_lower):
            value_key = original
            break
    if not value_key:
        # Fallback: try to find any column that is not the date column
        potential_values = [col for col in df.columns if col != date_key]
        if len(potential_values) == 1:
            value_key = potential_values[0]
        else:
            raise ValueError(
                f"Colonna {series_id} non trovata nel CSV FRED. Colonne disponibili: {list(df.columns)}"
            )

    df = df.rename(columns={date_key: "DATE", value_key: "VALUE"})
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce", utc=True).dt.tz_convert(None)
    df["VALUE"] = pd.to_numeric(df["VALUE"].replace(".", np.nan), errors="coerce")
    df = df.dropna(subset=["DATE", "VALUE"]).sort_values("DATE")

    if df.empty:
        raise ValueError(f"Serie FRED {series_id} vuota dopo la pulizia dei dati.")

    return pd.Series(df["VALUE"].values, index=df["DATE"], name=series_id)


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
        description="Volatilità storica a 90 giorni del cambio USD/EUR o JPY/EUR (Dati FRED)."
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
    parser.add_argument(
        "--end-date",
        type=str,
        help="Data di riferimento finale (YYYY-MM-DD). Se omessa, usa l'ultima disponibile.",
    )
    parser.add_argument(
        "--currency",
        type=str,
        choices=["USD", "JPY"],
        default="USD",
        help="Valuta da analizzare contro EUR (default: USD).",
    )
    args = parser.parse_args()

    series = None
    currency_pair_name = ""

    # 1) Scarica serie da FRED
    try:
        if args.currency == "USD":
            # USD/EUR directly available as DEXUSEU
            series = fetch_fred_series("DEXUSEU")
            currency_pair_name = "USD/EUR"
        elif args.currency == "JPY":
            # JPY/EUR calculated as (JPY/USD) * (USD/EUR) -> DEXJPUS * DEXUSEU
            # Note: DEXJPUS is JPY per USD. DEXUSEU is USD per EUR.
            # So JPY per EUR = (JPY/USD) * (USD/EUR) = DEXJPUS * DEXUSEU
            print("Scaricamento dati JPY (DEXJPUS) e USD (DEXUSEU)...")
            s_jpy_usd = fetch_fred_series("DEXJPUS")
            s_usd_eur = fetch_fred_series("DEXUSEU")
            
            # Align series on common dates
            df_aligned = pd.concat([s_jpy_usd, s_usd_eur], axis=1, join="inner")
            df_aligned.columns = ["DEXJPUS", "DEXUSEU"]
            
            # Calculate JPY/EUR
            series = df_aligned["DEXJPUS"] * df_aligned["DEXUSEU"]
            series.name = "JPY_per_EUR"
            currency_pair_name = "JPY/EUR"
            
    except Exception as e:
        print(f"Errore nel download/elaborazione dati FRED: {e}", file=sys.stderr)
        sys.exit(1)

    # 1.5) Filtra per data se richiesto
    if args.end_date:
        try:
            ref_date = datetime.strptime(args.end_date, "%Y-%m-%d")
            # series ha index datetime64[ns] (naive)
            series = series[series.index <= ref_date]
            if series.empty:
                print(f"Nessun dato disponibile fino al {args.end_date}.", file=sys.stderr)
                sys.exit(1)
        except ValueError:
            print("Errore: Il formato della data deve essere YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)

    # 2) Calcola vol
    try:
        res = compute_annualized_vol(series, window=args.window, trading_days=252)
    except Exception as e:
        print(f"Errore nel calcolo: {e}", file=sys.stderr)
        sys.exit(1)

    # 3) Output leggibile
    print(f"=== Volatilità storica {currency_pair_name} (FRED) ===")
    print(f"Finestra rendimenti:          {res['window']} giorni (osservazioni effettive: {res['obs_count']})")
    print(f"Periodo rendimenti:           {res['start_date']} → {res['end_date']}")
    print(f"Ultimo spot disponibile:      {res['last_spot']:.6f} {args.currency} per EUR (data {res['last_spot_date']})")
    print(f"Deviazione std giornaliera:   {res['stdev_daily']:.6%}")
    print(f"Vol annualizzata (252):       {res['vol_annualized_252']:.2%}")
    print(f"Vol annualizzata (365):       {res['vol_annualized_365']:.2%}")

    # 4) (opzionale) salvataggio CSV con i dati usati
    if args.save_csv:
        df = series.to_frame(name="RATE")
        df["log_return"] = np.log(series / series.shift(1))
        # Filtra il periodo usato per la finestra calcolata
        mask = (df.index.date >= pd.to_datetime(res["start_date"]).date()) & (
            df.index.date <= pd.to_datetime(res["end_date"]).date()
        )
        df_used = df.loc[mask].copy()
        out_path = f"{args.currency.lower()}_eur_fred_window_{res['window']}d.csv"
        df_used.to_csv(out_path, index_label="date")
        print(f"Dati usati salvati in: {out_path}")


if __name__ == "__main__":
    main()
