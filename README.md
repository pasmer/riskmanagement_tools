# riskmanagement_tools

Raccolta di script Python per analisi quantitative e metriche utilizzate nel risk management. I tool coprono beta settoriali Damodaran, volatilita storica dei cambi, indici di concentrazione delle performance e calcoli interattivi per rating di rischio.

## Requisiti
- Python 3.10 o superiore
- Librerie: `pandas`, `numpy`, `requests`, `argparse` (standard), `dataclasses` (built-in), `xlrd` per la lettura di alcuni file Excel storici

Per installare le dipendenze principali:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install pandas numpy requests xlrd
```

## Script principali
- `beta-analysis-script.py`: scarica i dataset Damodaran per piu regioni, consente analisi di settore, calcola beta levered/unlevered e produce CSV di confronto.
- `Beta_Gemini.py`: funzione compatta che calcola l'average levered beta per i paesi indicati combinando dati Damodaran (sheet "Country").
- `beta_settoriale.py`: pipeline parametrizzabile per aggregare beta settoriali Damodaran su archivi storici e pesare per numero di aziende.
- `fx_vol_90d.py`: calcola la volatilita storica annualizzata del cambio USD/EUR o JPY/EUR (serie FRED) su una finestra mobile di 90 giorni e salva opzionalmente i dati.
- `hhi_tvpi.py`: misura la concentrazione dei risultati di portafoglio tramite HHI su TVPI o altre definizioni di quota, esportando il dettaglio per deal.
- `weakest_link.py`: utility interattiva per derivare una media ponderata dei rating di rischio con pesi logaritmici.

Le cartelle CSV presenti nella radice contengono esempi di input/output generati dagli script.

## Utilizzo rapido
Eseguire gli script con Python attivando prima l'ambiente virtuale, ad esempio:
```bash
python beta-analysis-script.py
python fx_vol_90d.py --window 60 --save-csv
python fx_vol_90d.py --window 60 --currency JPY

# HHI su performance (TVPI)
python hhi_tvpi.py input_tvpi_only.csv --mode value --output-csv hhi_output.csv

# HHI su importi investiti (formato semplificato)
python hhi_tvpi.py input_invest.csv --mode invested --output-csv hhi_invested.csv
```
Gli script che richiedono input interattivo (es. `weakest_link.py`) possono essere lanciati direttamente e seguire le istruzioni a schermo.

### Formato CSV per hhi_tvpi.py

Lo script supporta diverse modalità di input:

**Modalità `invested` (semplificata)**: CSV con 2 colonne
```csv
Società,Investito
Alpha SpA,15.5
Beta Srl,22.3
Gamma Industries,8.7
```
Calcola la concentrazione degli investimenti direttamente sugli importi (es. milioni di euro).

**Modalità `value`**: richiede colonne `PaidIn`, `NAV`, `Distributions` (opzionale)

**Modalità `tvpi`**: richiede colonna `TVPI` o i dati per calcolarlo

## Risorse aggiuntive
- Documentazione di dettaglio sull'indice di concentrazione: `wiki/Indice concentrazione HH.md`.
- I dataset Damodaran sono disponibili su https://pages.stern.nyu.edu/~adamodar/New_Home_Page/data.html
- I dati FRED per USD/EUR e JPY/USD sono accessibili tramite https://fred.stlouisfed.org

## Note operative
- Alcuni script effettuano download da internet: assicurarsi di avere connettivita o scaricare preventivamente i file.
- I percorsi di output CSV sono generati nella directory corrente salvo specificato diversamente.
- Aggiornare regolarmente le librerie e rieseguire i calcoli per allineare le metriche alle condizioni di mercato correnti.
