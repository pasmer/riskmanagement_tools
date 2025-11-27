# GEMINI.md

This file provides guidance to Gemini AI when working with code in this repository.

## Overview

This repository contains standalone Python scripts for quantitative risk management analysis. Each script operates independently and focuses on specific financial metrics:

- **Sectoral beta analysis** using Damodaran datasets (NYU Stern)
- **FX volatility calculations** from FRED data (USD/EUR, JPY/EUR)
- **Portfolio concentration metrics** via Herfindahl-Hirschman Index
- **Risk rating calculations** with logarithmic weighting

The codebase is in Italian, with documentation and variable names primarily in Italian. Scripts are designed to run from the command line without interdependencies.

## Environment Setup

```bash
# ALWAYS use WSL for running scripts and tests
# Activate the existing virtual environment in WSL
source .venv/bin/activate

# Install dependencies (if needed)
pip install pandas numpy requests xlrd
```

Python 3.10+ required.

## Running Scripts

### Beta Analysis Scripts

**beta-analysis-script.py** - Main orchestrator for multi-region beta analysis:
```bash
python beta-analysis-script.py
```
- Downloads Damodaran datasets (USA, Europe, Global, Japan, Emerging Markets, Rest)
- Calculates levered/unlevered beta by sector
- Exports sector comparison to `sector_comparison.csv`
- Uses `DamodaranBetaAnalyzer` class as reusable component

**Beta_Gemini.py** - Compact version for country-level beta:
```bash
python Beta_Gemini.py
```
- Focuses on Country sheet from Damodaran beta.xls
- Prints average levered beta by sector and country

**beta_settoriale.py** - Historical beta pipeline with weighting:
```bash
python beta_settoriale.py
```
- Handles both current and historical Damodaran datasets
- Weights beta by number of firms
- Outputs `average_levered_beta_sector.csv`

### FX Volatility

**fx_vol_90d.py** - USD/EUR or JPY/EUR historical volatility:
```bash
# Default USD/EUR
python fx_vol_90d.py --window 60 --save-csv

# JPY/EUR (calculated via cross-rate)
python fx_vol_90d.py --window 60 --currency JPY --save-csv
```
- Default 90-day rolling window
- Downloads FRED DEXUSEU (and DEXJPUS for JPY) series
- Calculates annualized volatility (direct or cross-rate)
- Optional CSV export: `<currency>_eur_fred_window_<N>d.csv`

### Portfolio Concentration

**hhi_tvpi.py** - HHI concentration index:
```bash
# Portfolio performance concentration (TVPI-based)
python hhi_tvpi.py input_tvpi_only.csv --mode value --output-csv hhi_output.csv

# Simple investment concentration (amount-based)
python hhi_tvpi.py input_invest.csv --mode invested --output-csv hhi_invested.csv
```

Modes:
- `value` (recommended for performance): Concentration by total value created (NAV + Distributions)
- `tvpi`: Pure TVPI multiple concentration
- `realized`: Distributions only
- `unrealized`: NAV only
- `invested`: Simple concentration by investment amount (milioni €)

CSV formats:
- For `value` mode: `Deal`, `PaidIn`, `NAV`, `Distributions` (optional)
- For `tvpi` mode: `Deal`, `TVPI`
- For `invested` mode: Two columns (company name, amount invested)

Example CSV for `invested` mode:
```csv
Società,Investito
Alpha SpA,15.5
Beta Srl,22.3
Gamma Industries,8.7
```

Outputs HHI, normalized HHI (0-1 scale), and risk classification.

### Risk Rating

**weakest_link.py** - Interactive risk rating calculator:
```bash
python weakest_link.py
```
- Prompts for 6 risk ratings interactively
- Applies logarithmic weighting
- Prints weighted average risk score

## Architecture Notes

### Data Flow Pattern

Scripts follow a consistent pattern:
1. **Download/Load**: Fetch data from external sources (Damodaran, FRED) or local CSV
2. **Transform**: Calculate metrics using pandas/numpy
3. **Output**: Print to console and/or export CSV

No persistent state or databases. All outputs are CSV files in the working directory.

### Beta Calculation Methodology

Levered beta calculation uses Hamada formula:
```
βL = βU × (1 + (1 - T) × (D/E))
```

Where:
- βL = Levered beta
- βU = Unlevered beta (cash-adjusted when available)
- T = Tax rate
- D/E = Debt/equity ratio

Weighted averages use firm count as weights across regions.

### HHI Concentration Metric

The HHI (Herfindahl-Hirschman Index) measures portfolio concentration:
```
HHI = Σ(si²)
HHI* = (HHI - 1/N) / (1 - 1/N)  # Normalized 0-1
```

Where si is the share of each deal in total portfolio value.

Risk classifications:
- HHI* < 0.20: Basso (Low)
- 0.20-0.40: Medio-Basso
- 0.40-0.60: Medio
- 0.60-0.80: Medio-Alto
- > 0.80: Alto (High)

See `wiki/Indice concentrazione HH.md` for detailed theory.

## Data Sources

- **Damodaran datasets**: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/data.html
- **FRED USD/EUR**: https://fred.stlouisfed.org/series/DEXUSEU
- **FRED JPY/USD**: https://fred.stlouisfed.org/series/DEXJPUS

Scripts require internet connectivity for downloads. Historical files use `xlrd` for legacy .xls format support.

## CSV Examples

Root directory contains example input/output files:
- `input_tvpi_only.csv` - Sample HHI input
- `sector_comparison.csv` - Beta comparison output
- `beta_analysis_*.csv` - Timestamped beta analysis exports

## Git Workflow

Current branch: `main`
Recent versions: v4.1, v4, v3, v2.1, v2

Scripts are versioned as a collection. Individual script modifications are tracked but not independently versioned.
