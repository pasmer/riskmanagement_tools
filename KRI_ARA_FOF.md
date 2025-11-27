# Script per i KRI dei ARA FOF

## RC5 Indice di concentrazione geo-settoriale

Il KRI (indice di concentrazione HH) è calcolato con riferimento agli investimenti effettuati dal fondo target (tramite look througt), sulla base dei seguenti parametri: settori industriali/aree geografiche.

**Input:** Utilizzare il file `input_invest.csv`
```csv
Società,Investito
```
**Script:** `hhi_tvpi.py`
  - Per modalità `invested`: CSV semplificato a 2 colonne (nome società, importo investito in M€)

```bash
python hhi_tvpi.py input_invest.csv --mode invested --output-csv hhi_invested.csv
```

## RM5 Indice di concentrazione delle partecipate del fondo target

L’indice di Herfindahl-Hirschman utilizzato per stimare la concentrazione delle performance date dal TVPI delle singole partecipazioni in portafoglio al fondo target.

**Input:** Utilizzare il file `input_tvpi_only.csv`
```csv
Deal,TVPI
```
**Script:** `hhi_tvpi.py`
# Script per i KRI dei ARA FOF

## RC5 Indice di concentrazione geo-settoriale

Il KRI (indice di concentrazione HH) è calcolato con riferimento agli investimenti effettuati dal fondo target (tramite look througt), sulla base dei seguenti parametri: settori industriali/aree geografiche.

**Input:** Utilizzare il file `input_invest.csv`
```csv
Società,Investito
```
**Script:** `hhi_tvpi.py`
  - Per modalità `invested`: CSV semplificato a 2 colonne (nome società, importo investito in M€)

```bash
python hhi_tvpi.py input_invest.csv --mode invested --output-csv hhi_invested.csv
```

## RM5 Indice di concentrazione delle partecipate del fondo target

L’indice di Herfindahl-Hirschman utilizzato per stimare la concentrazione delle performance date dal TVPI delle singole partecipazioni in portafoglio al fondo target.

**Input:** Utilizzare il file `input_tvpi_only.csv`
```csv
Deal,TVPI
```
**Script:** `hhi_tvpi.py`
 - Per modalità `tvpi`: CSV con colonne `Deal`, `TVPI`

```bash
python hhi_tvpi.py input_tvpi_only.csv --mode tvpi --output-csv hhi_tvpi.csv
```

## RM3 Rischio di cambio

Volatilità storica a 90 giorni del tasso di cambio tra la valuta di denominazione del FoF (EUR) e la valuta di denominazione del fondo target (es. USD o JPY).

**Script:** `fx_vol_90d.py`

Per USD (default):
```bash
python fx_vol_90d.py --window 90 --save-csv
```

Per JPY:
```bash
python fx_vol_90d.py --window 90 --currency JPY --save-csv
```

Con data di riferimento specifica:
```bash
python fx_vol_90d.py --window 90 --save-csv --end-date 2025-11-26
```