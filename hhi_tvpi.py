# Script Python per calcolare l'Herfindahl-Hirschman Index (HHI) di concentrazione delle performance (TVPI)
# Utilizzando un CSV di input con colonne: Deal (o altra id), TVPI (o PaidIn+NAV), Distributions (opzionale), NAV
# Elaborato da ChatGPT-5

import pandas as pd 
import argparse
import sys
from typing import Tuple

def compute_tvpi(df: pd.DataFrame) -> pd.Series:
    """
    Calcola TVPI se non presente.
    Richiede colonne: 'NAV' e 'Distributions' (facoltativa) e 'PaidIn'.
    TVPI = (NAV + Distributions) / PaidIn
    """
    if 'TVPI' in df.columns and df['TVPI'].notna().all():
        return df['TVPI'].astype(float)

    missing = [c for c in ['PaidIn', 'NAV'] if c not in df.columns]
    # Distributions può mancare; la assumiamo 0
    if missing:
        raise ValueError(
            "Per calcolare TVPI servono le colonne: PaidIn, NAV (e opzionale Distributions). "
            f"Mancano: {missing}"
        )
    distr = df['Distributions'] if 'Distributions' in df.columns else 0.0
    paidin = df['PaidIn'].astype(float)
    nav = df['NAV'].astype(float)

    # Evita divisioni per zero
    if (paidin <= 0).any():
        raise ValueError("Sono presenti PaidIn <= 0, impossibile calcolare correttamente il TVPI.")

    tvpi = (nav + distr.astype(float)) / paidin
    return tvpi

def build_shares(df: pd.DataFrame, mode: str) -> pd.Series:
    """
    Costruisce le quote s_i per l'HHI in base alla modalità scelta.
    mode:
      - 'tvpi': s_i = TVPI_i / sum(TVPI)
      - 'value': s_i = (TVPI_i * PaidIn_i) / sum(TVPI_j * PaidIn_j) = (NAV+Distr)/totale
      - 'realized': s_i = (Distributions) / sum(Distributions)
      - 'unrealized': s_i = NAV / sum(NAV)
      - 'invested': s_i = Investito_i / sum(Investito) [per CSV semplificato con importi investiti]
    """
    if mode == 'invested':
        # Modalità semplificata: usa direttamente la seconda colonna come importo investito
        # Cerca colonne comuni per investimenti
        invested_col = None
        for col in ['Investito', 'Invested', 'Amount', 'Importo']:
            if col in df.columns:
                invested_col = col
                break

        if invested_col is None:
            # Se non trova colonne note, usa la seconda colonna del DataFrame
            if len(df.columns) >= 2:
                invested_col = df.columns[1]
            else:
                raise ValueError("Per mode='invested' serve almeno 2 colonne (nome società, importo investito).")

        w = df[invested_col].astype(float)
        if (w < 0).any():
            raise ValueError("Sono presenti importi investiti negativi.")
    else:
        # Modalità esistenti che richiedono TVPI
        tvpi = compute_tvpi(df)

        if mode == 'tvpi':
            w = tvpi.astype(float)

        elif mode == 'value':
            if 'PaidIn' not in df.columns:
                raise ValueError("Per mode='value' serve la colonna PaidIn.")
            paidin = df['PaidIn'].astype(float)
            w = tvpi * paidin  # == NAV + Distr

        elif mode == 'realized':
            if 'Distributions' not in df.columns:
                raise ValueError("Per mode='realized' serve la colonna Distributions.")
            w = df['Distributions'].astype(float)

        elif mode == 'unrealized':
            if 'NAV' not in df.columns:
                raise ValueError("Per mode='unrealized' serve la colonna NAV.")
            w = df['NAV'].astype(float)

        else:
            raise ValueError("mode non valido. Usa: tvpi, value, realized, unrealized, invested")

    total = w.sum()
    if total <= 0:
        raise ValueError("La somma dei pesi è <= 0: non è possibile costruire le quote.")
    shares = w / total
    return shares

def compute_hhi(shares: pd.Series) -> Tuple[float, float]:
    """
    Restituisce (HHI, HHI_normalizzato).
    HHI = sum(s_i^2).
    HHI_normalizzato = (HHI - 1/N) / (1 - 1/N), scala 0..1 (0 = equidistribuzione, 1 = massima concentrazione).
    """
    s2 = (shares ** 2).sum()
    n = shares.shape[0]
    if n <= 1:
        # con 1 solo elemento l'HHI è 1 e la normalizzazione non è definita (divide per 0)
        return float(s2), float('nan')
    hhi_norm = (s2 - 1.0/n) / (1.0 - 1.0/n)
    return float(s2), float(hhi_norm)

def classify_hhi(hhi_norm: float) -> str:
    if hhi_norm < 0.20:
        return "Basso"
    elif hhi_norm < 0.40:
        return "Medio-Basso"
    elif hhi_norm < 0.60:
        return "Medio"
    elif hhi_norm < 0.80:
        return "Medio-Alto"
    else:
        return "Alto"

def main():
    parser = argparse.ArgumentParser(description="Calcolo HHI di concentrazione delle performance (TVPI) o investimenti.")
    parser.add_argument("input_csv", help="Percorso al CSV di input.")
    parser.add_argument("--id-col", default="Deal", help="Nome colonna identificativa della partecipazione (default: Deal). Per mode=invested usa la prima colonna se non specificato.")
    parser.add_argument("--mode", choices=["tvpi","value","realized","unrealized","invested"], default="value",
                        help="Definizione delle quote: tvpi, value (default), realized, unrealized, invested (per CSV semplificato con importi investiti).")
    parser.add_argument("--output-csv", default=None, help="(Opzionale) Scrive un CSV con quote e contributi.")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input_csv)
    except Exception as e:
        print(f"Errore nel leggere il CSV: {e}", file=sys.stderr)
        sys.exit(1)

    required_any = {"tvpi": ["TVPI"] or ["PaidIn","NAV"],
                    "value": ["PaidIn","NAV"],  # Distributions opzionale
                    "realized": ["Distributions"],
                    "unrealized": ["NAV"]}

    # Costruisci quote
    try:
        shares = build_shares(df, args.mode)
    except Exception as e:
        print(f"Errore nel calcolo quote: {e}", file=sys.stderr)
        sys.exit(2)

    # HHI
    hhi, hhi_norm = compute_hhi(shares)

    # Costruisci output riassuntivo
    # Per mode='invested', usa la prima colonna come ID se id_col non è specificato
    if args.mode == 'invested':
        id_column = args.id_col if args.id_col in df.columns else df.columns[0]
    else:
        id_column = args.id_col if args.id_col in df.columns else "Deal"

    out = pd.DataFrame({
        id_column: df[id_column] if id_column in df.columns else range(1, len(df)+1),
        "Share": shares,
        "Share^2": shares**2
    })

    # Aggiungi colonne specifiche per mode='invested'
    if args.mode == 'invested':
        # Trova la colonna investito
        invested_col = None
        for col in ['Investito', 'Invested', 'Amount', 'Importo']:
            if col in df.columns:
                invested_col = col
                break
        if invested_col is None and len(df.columns) >= 2:
            invested_col = df.columns[1]

        if invested_col:
            out["Investito"] = df[invested_col].astype(float)
    else:
        # Aggiungi (se disponibili) colonne utili per le altre modalità
        for col in ["TVPI","PaidIn","NAV","Distributions"]:
            if col in df.columns:
                out[col] = df[col]

        # Contributo al valore totale (solo per mode='value')
        if args.mode == "value":
            # (= NAV + Distributions se Distributions presente, altrimenti NAV + 0)
            distr = df['Distributions'] if 'Distributions' in df.columns else 0.0
            out["ValueCreated"] = df["NAV"].astype(float) + distr.astype(float)

    # Ordina per Share decrescente
    out = out.sort_values(by="Share", ascending=False).reset_index(drop=True)

    print("\n=== Herfindahl-Hirschman Index (HHI) sulla definizione di quota:", args.mode, "===")
    print(f"HHI        = {hhi:.6f}")
    if not pd.isna(hhi_norm):
        print(f"HHI* (0-1) = {hhi_norm:.6f}  (0 = equidistribuzione, 1 = massima concentrazione)")
    else:
        print("HHI* (normalizzato) non definito con N=1.")

    # Mostra top 10 righe
    print("\nTop 10 contributi alle quote:")
    print(out.head(10).to_string(index=False))
    
    risk_level = classify_hhi(hhi_norm)
    print(f"Livello di rischio = {risk_level}")


    # Salva CSV opzionale
    if args.output_csv:
        try:
            out.to_csv(args.output_csv, index=False)
            print(f"\nDettaglio quote salvato in: {args.output_csv}")
        except Exception as e:
            print(f"Non riesco a salvare il CSV: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

