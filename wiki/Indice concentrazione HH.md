Ottima idea: usare un indice di concentrazione stile Herfindahl-Hirschman (HHI) sulle “quote di performance” legate al TVPI delle singole partecipazioni. Di seguito trovi un piccolo script Python che:

* legge un CSV,
* calcola (se manca) il TVPI per ciascuna partecipazione,
* costruisce diverse definizioni di “quota” $s_i$ su cui calcolare l’HHI,
* restituisce HHI e HHI normalizzato (0 = perfetta equidistribuzione, 1 = massima concentrazione).

### Quale “quota” usare?

A seconda di come vuoi interpretare la “concentrazione della performance” puoi scegliere:

1. **Quota su TVPI “puro”**
   $s_i = \dfrac{TVPI_i}{\sum_j TVPI_j}$
   Buona se vuoi pesare tutte le posizioni allo stesso modo e guardare solo la dispersione dei multipli.

2. **Quota su valore creato/pesato per capitale investito (consigliata)**
   $s_i = \dfrac{TVPI_i \cdot PaidIn_i}{\sum_j TVPI_j \cdot PaidIn_j} = \dfrac{NAV_i + Distr_i}{\sum_j (NAV_j + Distr_j)}$
   Misura la concentrazione della **performance economica complessiva** (quanta parte del valore totale generato è attribuibile a ogni deal).

3. **Altre varianti** (opzionali nel codice): solo realizzato (DPI·PaidIn) o solo non realizzato (NAV).

---

## Script Python (pandas + argparse)

Salvalo come, ad esempio, `hhi_tvpi.py`.

```python
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
    """
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
        raise ValueError("mode non valido. Usa: tvpi, value, realized, unrealized")

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

def main():
    parser = argparse.ArgumentParser(description="Calcolo HHI di concentrazione delle performance (TVPI).")
    parser.add_argument("input_csv", help="Percorso al CSV di input.")
    parser.add_argument("--id-col", default="Deal", help="Nome colonna identificativa della partecipazione (default: Deal).")
    parser.add_argument("--mode", choices=["tvpi","value","realized","unrealized"], default="value",
                        help="Definizione delle quote: tvpi, value (default), realized, unrealized.")
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
    out = pd.DataFrame({
        args.id_col if args.id_col in df.columns else "Deal": df[args.id_col] if args.id_col in df.columns else range(1, len(df)+1),
        "Share": shares,
        "Share^2": shares**2
    })

    # Aggiungi (se disponibili) colonne utili
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

    # Salva CSV opzionale
    if args.output_csv:
        try:
            out.to_csv(args.output_csv, index=False)
            print(f"\nDettaglio quote salvato in: {args.output_csv}")
        except Exception as e:
            print(f"Non riesco a salvare il CSV: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
```

### Formato CSV di input – esempi

Puoi usare uno dei seguenti set minimi di colonne (header esatti):

* **Per `--mode value` (consigliata)**

```
Deal,PaidIn,NAV,Distributions
Deal A,10_000_000,12_000_000,3_000_000
Deal B,8_000_000,7_500_000,1_500_000
Deal C,5_000_000,6_000_000,0
```

* **Se hai già il TVPI** (per `--mode tvpi`)

```
Deal,TVPI
Deal A,1.50
Deal B,1.12
Deal C,1.30
```

> Nota: i separatori **\_** nelle cifre non sono standard CSV; meglio usare numeri “puliti” (es. `10000000`). In alternativa, pulisci in Excel prima di salvare.

### Esecuzione

```bash
# Variante consigliata (concentrazione sul valore complessivo generato)
python hhi_tvpi.py input.csv --mode value --id-col Deal --output-csv hhi_output.csv

# Se vuoi la concentrazione “solo sui multipli”
python hhi_tvpi.py input_tvpi_only.csv --mode tvpi
```

### Interpretazione rapida

* **HHI = 1/N** quando tutte le quote sono uguali (bassa concentrazione).
* **HHI → 1** quando una sola partecipazione domina tutta la performance.
* **HHI normalizzato (HHI*)*\* porta il minimo a 0 e il massimo a 1 per confronto immediato tra portafogli con N diversi.

Se vuoi, posso adattare lo script ai tuoi layout CSV reali (nomi colonne italiani, validazioni, output in Excel con formattazione, grafico a barre dei contributi, ecc.).
