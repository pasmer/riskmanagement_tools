# Script Catalog

Questo repository raccoglie script indipendenti per analisi quantitative di risk management. Ogni file Python puo essere eseguito singolarmente e non condivide stato globale con gli altri, ma spesso riutilizza le stesse dipendenze (pandas, numpy, requests).

## Struttura generale
- Ogni script e pensato per essere avviato da linea di comando con `python <nome_script>.py`.
- Gli output principali sono CSV o stampe a schermo; non sono presenti package Python installabili.
- I file CSV presenti nella radice sono esempi di input o output generati dagli script.

## Dettaglio script

### beta-analysis-script.py
- **Purpose**: orchestrare il download dei dataset Damodaran beta per piu regioni (USA, Europe, Global, Japan, Emerging Markets, Rest) e calcolare beta levered/unlevered per settore con possibilita di confronto multi regione.
- **Entry point**: `main_example()` (eseguito se il file e lanciato come script).
- **Dipendenze chiave**: `pandas`, `numpy`, `requests`.
- **Input**: nessun input locale obbligatorio; richiede connessione internet per scaricare file Excel dal sito NYU Stern.
- **Output**: stampa risultati al terminale, esporta analisi settoriale in CSV (es. `sector_comparison.csv`).
- **Note**: contiene classi riutilizzabili (`DamodaranBetaAnalyzer`) per carico e filtraggio dataset.

### Beta_Gemini.py
- **Purpose**: versione compatta focalizzata sui beta levered per paese tramite il foglio `Country` del dataset Damodaran.
- **Entry point**: esecuzione del blocco finale che chiama `calcola_average_levered_beta_settoriale` con una lista di paesi.
- **Dipendenze chiave**: `pandas`.
- **Input**: nessun file locale; scarica direttamente il file `beta.xls` dal sito Damodaran.
- **Output**: stampa a schermo un DataFrame con medie per settore e paese.
- **Note**: non salva automaticamente risultati; e pensato come snippet dimostrativo.

### beta_settoriale.py
- **Purpose**: pipeline modulare per interrogare i dataset Damodaran correnti e storici, con possibilita di pesare i beta per numero di aziende e salvare output storici.
- **Entry point**: blocco finale che definisce `geos` e invoca `compute_average_beta`.
- **Dipendenze chiave**: `requests`, `pandas`, `xlrd` (per alcuni file storici), `dataclasses`.
- **Input**: nessun file locale; necessita connessione per scaricare file Excel.
- **Output**: stampa le prime righe del risultato e salva `average_levered_beta_sector.csv` con beta medi per geografia/settore.
- **Note**: gestisce differenze di naming nei file Damodaran e include logica di fallback per anni mancanti.

### fx_vol_90d.py
- **Purpose**: calcolare la volatilita storica annualizzata del cambio USD/EUR o JPY/EUR su una finestra di default di 90 giorni usando dati FRED.
- **Entry point**: `main()` con CLI basata su `argparse`.
- **Dipendenze chiave**: `requests`, `pandas`, `numpy`, `argparse`.
- **Input**: parametri opzionali `--window`, `--currency` (USD/JPY) e `--save-csv`; necessita rete per scaricare i CSV FRED.
- **Output**: stampa metriche di volatilita e, se richiesto, salva `<currency>_eur_fred_window_<N>d.csv` con serie e rendimenti.
- **Note**: include controlli su content-type e gestione errori per download falliti.

### hhi_tvpi.py
- **Purpose**: calcolare l'indice di concentrazione Herfindahl-Hirschman (HHI) su metriche di performance (TVPI, valore, realized, unrealized) o su importi investiti (modalità semplificata) a partire da un CSV di portafoglio.
- **Entry point**: `main()` con CLI basata su `argparse`.
- **Dipendenze chiave**: `pandas`, `argparse`.
- **Input**:
  - Per modalità `value`: CSV con colonne `Deal`, `PaidIn`, `NAV`, `Distributions` (opzionale)
  - Per modalità `tvpi`: CSV con colonne `Deal`, `TVPI`
  - Per modalità `invested`: CSV semplificato a 2 colonne (nome società, importo investito in M€)
- **Output**: stampa HHI, HHI normalizzato (0-1), livello di rischio, e top contributor; può salvare un CSV dettagliato con quote (`--output-csv`).
- **Esempio modalità invested**:
  ```bash
  python hhi_tvpi.py input_invest.csv --mode invested --output-csv hhi_invested.csv
  ```
  Formato CSV: `Società,Investito` (2 colonne: identificativo, importo)
- **Note**: nella directory `wiki` è presente ulteriore documentazione teorica (`wiki/Indice concentrazione HH.md`).

### weakest_link.py
- **Purpose**: raccogliere rating di rischio tramite input utente e calcolare una media ponderata con pesi logaritmici.
- **Entry point**: `main()`.
- **Dipendenze chiave**: `numpy`.
- **Input**: inserimento interattivo di sei rating di rischio.
- **Output**: stampa i rating, i pesi calcolati e la media ponderata.
- **Note**: script legacy; utile come esempio di trasformazione dei pesi.

## Suggerimenti di integrazione con altri agenti
- Fornire a un agente informazioni su quale script eseguire e con quali parametri e sufficiente per ottenere risultati; non esistono dipendenze incrociate.
- Per flussi riproducibili, indicare sempre la fonte dei dati e i file CSV di output attesi.
- Gli script che effettuano download (beta*, fx_vol_90d) funzionano anche con dati gia scaricati sostituendo le funzioni di fetch con percorsi locali, se necessario.
