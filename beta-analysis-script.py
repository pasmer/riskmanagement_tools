# Script Python per calcolare Average Levered Beta settoriali
# Utilizzando i database di Aswath Damodaran (NYU Stern)
# Autore: Risk Manager
# Data: Settembre 2025
# Versione: 1.0
# Elaborato da Perplexity AI

import pandas as pd
import numpy as np
import requests
from io import BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class DamodaranBetaAnalyzer:
    """
    Classe per analizzare e calcolare Average Levered Beta settoriali 
    utilizzando i database di Damodaran della NYU Stern School of Business.
    
    I dataset includono beta settoriali per:
    - USA
    - Europa (Western Europe)  
    - Globale (tutte le regioni)
    - Giappone
    - Mercati Emergenti
    - Rest (Australia, Nuova Zelanda, Canada)
    """
    
    def __init__(self):
        self.datasets = {}
        self.urls = {
            'USA': 'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls',
            'Europe': 'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaEurope.xls', 
            'Global': 'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaglobal.xls',
            'Japan': 'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaJapan.xls',
            'EmergingMarkets': 'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaemerg.xls',
            'Rest': 'https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaRest.xls'
        }
        
    def load_data(self, regions=None, verbose=True):
        """
        Carica i dati dei beta settoriali da Damodaran per le regioni specificate.
        
        Parameters:
        -----------
        regions : list, optional
            Lista delle regioni da caricare. Se None, carica tutte.
        verbose : bool, optional 
            Se True, stampa messaggi di debug durante il caricamento.
        
        Returns:
        --------
        dict : Dizionario con i dataset caricati per regione
        """
        if regions is None:
            regions = list(self.urls.keys())
        
        if verbose:
            print(f"Caricamento dati Damodaran per: {', '.join(regions)}")
        
        for region in regions:
            if region not in self.urls:
                if verbose:
                    print(f"Regione {region} non disponibile")
                continue
                
            try:
                if verbose:
                    print(f"Scaricando dati per {region}...")
                
                # Scarica il file Excel
                response = requests.get(self.urls[region], timeout=30)
                response.raise_for_status()
                
                # Leggi il file Excel
                excel_file = BytesIO(response.content)
                
                # Prova diversi approcci per leggere il file
                df = self._parse_excel_file(excel_file, region)
                
                if df is not None and not df.empty:
                    # Aggiungi colonna regione
                    df['Region'] = region
                    self.datasets[region] = df
                    
                    if verbose:
                        print(f"✓ Caricati {len(df)} settori per {region}")
                else:
                    if verbose:
                        print(f"✗ Nessun dato valido trovato per {region}")
                        
            except Exception as e:
                if verbose:
                    print(f"✗ Errore nel caricamento per {region}: {e}")
        
        if verbose:
            print(f"\nDataset caricati con successo: {list(self.datasets.keys())}")
        
        return self.datasets
        
    def _parse_excel_file(self, excel_file, region):
        """
        Metodo interno per parsare i file Excel di Damodaran.
        Gestisce le diverse strutture dei fogli Excel.
        """
        try:
            # Leggi tutto il file per trovare la struttura
            df_full = pd.read_excel(excel_file, sheet_name=0, header=None)
            
            # Cerca la riga che contiene "Industry Name"
            header_row = None
            for idx, row in df_full.iterrows():
                row_str = ' '.join([str(val) for val in row.values if pd.notna(val)])
                if 'Industry Name' in row_str:
                    header_row = idx
                    break
            
            if header_row is not None:
                # Rileggi con le intestazioni corrette
                excel_file.seek(0)
                df = pd.read_excel(excel_file, sheet_name=0, skiprows=header_row)
                
                # Pulisci i nomi delle colonne
                df.columns = [str(col).strip() for col in df.columns]
                
                # Filtra le righe valide
                df = df[df['Industry Name'].notna() & 
                       (df['Industry Name'] != 'Industry Name') &
                       (~df['Industry Name'].astype(str).str.contains('Total Market', na=False))]
                
                # Converti le colonne numeriche
                numeric_cols = ['Number of firms', 'Beta', 'D/E Ratio', 'Effective Tax rate', 
                              'Unlevered beta', 'Cash/Firm value', 'Unlevered beta corrected for cash']
                
                for col in numeric_cols:
                    if col in df.columns:
                        # Gestisci percentuali (converte "15.5%" in 0.155)
                        if df[col].dtype == 'object':
                            df[col] = df[col].astype(str).str.rstrip('%').replace('nan', np.nan)
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        
                        # Se sembra essere una percentuale (valori > 1), dividi per 100
                        if col in ['D/E Ratio', 'Effective Tax rate', 'Cash/Firm value'] and df[col].max() > 1:
                            df[col] = df[col] / 100
                
                return df
                
        except Exception as e:
            print(f"Errore nel parsing per {region}: {e}")
            return None
        
        return None
        
    def get_sector_beta(self, sector_name, regions=None, exact_match=False):
        """
        Cerca il beta di un settore specifico nelle regioni indicate.
        
        Parameters:
        -----------
        sector_name : str
            Nome del settore da cercare
        regions : list, optional  
            Regioni in cui cercare. Se None, cerca in tutte quelle caricate.
        exact_match : bool, optional
            Se True, cerca match esatto del nome, altrimenti cerca substring.
        
        Returns:
        --------
        pd.DataFrame : DataFrame con i risultati trovati
        """
        if not self.datasets:
            print("Nessun dataset caricato. Usa load_data() prima.")
            return pd.DataFrame()
        
        if regions is None:
            regions = list(self.datasets.keys())
        
        results = []
        
        for region in regions:
            if region not in self.datasets:
                continue
                
            df = self.datasets[region]
            
            if exact_match:
                matches = df[df['Industry Name'].str.lower() == sector_name.lower()]
            else:
                matches = df[df['Industry Name'].str.contains(sector_name, case=False, na=False)]
            
            if not matches.empty:
                results.append(matches)
        
        if results:
            combined = pd.concat(results, ignore_index=True)
            return combined
        else:
            print(f"Settore '{sector_name}' non trovato nelle regioni specificate")
            return pd.DataFrame()
    
    def calculate_levered_beta(self, unlevered_beta, target_de_ratio, target_tax_rate):
        """
        Calcola il beta levered utilizzando la formula di Hamada.
        
        Formula: βL = βU × (1 + (1 - T) × (D/E))
        
        Parameters:
        -----------
        unlevered_beta : float
            Beta unlevered (senza effetto della leva finanziaria)
        target_de_ratio : float  
            Rapporto Debt/Equity target (es: 0.5 per 50%)
        target_tax_rate : float
            Aliquota fiscale target (es: 0.25 per 25%)
        
        Returns:
        --------
        float : Beta levered calcolato
        """
        return unlevered_beta * (1 + (1 - target_tax_rate) * target_de_ratio)
    
    def analyze_sector(self, sector_name, target_de_ratio=None, target_tax_rate=None, regions=None):
        """
        Analizza un settore e calcola l'average levered beta per diverse regioni.
        
        Parameters:
        -----------
        sector_name : str
            Nome del settore da analizzare
        target_de_ratio : float, optional
            Rapporto D/E target. Se None, usa quello originale del settore.
        target_tax_rate : float, optional
            Tax rate target. Se None, usa quello originale del settore.
        regions : list, optional
            Regioni da includere nell'analisi
        
        Returns:
        --------
        pd.DataFrame : Analisi completa del settore con beta calcolati
        """
        sector_data = self.get_sector_beta(sector_name, regions=regions)
        
        if sector_data.empty:
            return pd.DataFrame()
        
        results = []
        
        for _, row in sector_data.iterrows():
            result = {
                'Sector': row['Industry Name'],
                'Region': row['Region'],
                'Number_of_Firms': row.get('Number of firms', np.nan),
                'Beta_Levered_Original': row.get('Beta', np.nan),
                'DE_Ratio_Original': row.get('D/E Ratio', np.nan),
                'Tax_Rate_Original': row.get('Effective Tax rate', np.nan),
                'Beta_Unlevered': row.get('Unlevered beta', np.nan),
                'Beta_Unlevered_Cash_Adjusted': row.get('Unlevered beta corrected for cash', np.nan)
            }
            
            # Calcola beta levered con parametri target se forniti
            if target_de_ratio is not None and target_tax_rate is not None:
                # Usa beta unlevered corretto per cash se disponibile
                unlevered = row.get('Unlevered beta corrected for cash', 
                                   row.get('Unlevered beta', np.nan))
                
                if not pd.isna(unlevered):
                    result['Beta_Levered_Target'] = self.calculate_levered_beta(
                        unlevered, target_de_ratio, target_tax_rate
                    )
                    result['DE_Ratio_Target'] = target_de_ratio
                    result['Tax_Rate_Target'] = target_tax_rate
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def calculate_weighted_average_beta(self, sector_analysis, weight_col='Number_of_Firms', beta_col=None):
        """
        Calcola la media ponderata dei beta tra le regioni.
        
        Parameters:
        -----------
        sector_analysis : pd.DataFrame
            DataFrame con l'analisi del settore
        weight_col : str
            Colonna da usare come peso (default: numero di aziende)
        beta_col : str, optional
            Colonna del beta da usare. Se None, usa Target se disponibile, altrimenti Original.
        
        Returns:
        --------
        float : Beta medio ponderato
        """
        if sector_analysis.empty:
            return np.nan
        
        # Determina quale colonna beta usare
        if beta_col is None:
            if 'Beta_Levered_Target' in sector_analysis.columns and sector_analysis['Beta_Levered_Target'].notna().any():
                beta_col = 'Beta_Levered_Target'
            else:
                beta_col = 'Beta_Levered_Original'
        
        # Rimuovi righe con valori mancanti
        valid_data = sector_analysis[[beta_col, weight_col]].dropna()
        
        if valid_data.empty:
            return np.nan
        
        # Calcola media ponderata
        if weight_col in valid_data.columns and valid_data[weight_col].sum() > 0:
            weighted_avg = np.average(valid_data[beta_col], weights=valid_data[weight_col])
        else:
            # Se non ci sono pesi validi, usa media semplice
            weighted_avg = valid_data[beta_col].mean()
        
        return weighted_avg
    
    def export_analysis(self, sector_analysis, filename=None):
        """
        Esporta l'analisi in formato CSV.
        
        Parameters:
        -----------
        sector_analysis : pd.DataFrame
            DataFrame con l'analisi da esportare
        filename : str, optional
            Nome del file. Se None, genera automaticamente con timestamp.
        
        Returns:
        --------
        str : Nome del file creato
        """
        if sector_analysis.empty:
            print("Nessun dato da esportare")
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sector_name = sector_analysis['Sector'].iloc[0].replace(' ', '_').replace('/', '_')
            filename = f"beta_analysis_{sector_name}_{timestamp}.csv"
        
        sector_analysis.to_csv(filename, index=False)
        print(f"Analisi esportata in: {filename}")
        return filename
        
    def get_available_sectors(self, region=None):
        """
        Restituisce la lista dei settori disponibili.
        
        Parameters:
        -----------
        region : str, optional
            Regione specifica. Se None, mostra settori di tutte le regioni.
        
        Returns:
        --------
        list : Lista ordinata dei settori disponibili
        """
        if not self.datasets:
            print("Nessun dataset caricato.")
            return []
        
        sectors = []
        
        if region and region in self.datasets:
            sectors = self.datasets[region]['Industry Name'].tolist()
        else:
            for df in self.datasets.values():
                sectors.extend(df['Industry Name'].tolist())
        
        return sorted(list(set(sectors)))
    
    def compare_sectors(self, sector_names, target_de_ratio=None, target_tax_rate=None, regions=None):
        """
        Confronta i beta di più settori.
        
        Parameters:
        -----------
        sector_names : list
            Lista dei nomi dei settori da confrontare
        target_de_ratio : float, optional
            Rapporto D/E target da applicare a tutti i settori
        target_tax_rate : float, optional  
            Tax rate target da applicare a tutti i settori
        regions : list, optional
            Regioni da includere nel confronto
        
        Returns:
        --------
        pd.DataFrame : Confronto dei settori con average beta
        """
        comparison_results = []
        
        for sector in sector_names:
            analysis = self.analyze_sector(
                sector, 
                target_de_ratio=target_de_ratio,
                target_tax_rate=target_tax_rate,
                regions=regions
            )
            
            if not analysis.empty:
                avg_beta = self.calculate_weighted_average_beta(analysis)
                
                comparison_results.append({
                    'Sector': sector,
                    'Average_Levered_Beta': avg_beta,
                    'Regions_Count': len(analysis),
                    'Total_Firms': analysis['Number_of_Firms'].sum() if 'Number_of_Firms' in analysis.columns else np.nan
                })
        
        return pd.DataFrame(comparison_results).sort_values('Average_Levered_Beta', ascending=False)

# =============================================================================
# ESEMPIO DI UTILIZZO
# =============================================================================

def main_example():
    """
    Esempio completo di utilizzo dello script per calcolare Average Levered Beta settoriali.
    """
    print("SCRIPT PER CALCOLARE AVERAGE LEVERED BETA SETTORIALI")
    print("Utilizzando i database di Aswath Damodaran (NYU Stern)")
    print("="*70)
    
    # 1. Inizializza l'analyzer
    analyzer = DamodaranBetaAnalyzer()
    
    # 2. Carica i dati per le regioni desiderate
    print("\n1. Caricamento dati...")
    regions_to_load = ['Europe', 'USA', 'Global']  # Modifica secondo necessità
    analyzer.load_data(regions_to_load)
    
    if not analyzer.datasets:
        print("Nessun dataset caricato. Verifica connessione internet e URL.")
        return
    
    # 3. Mostra settori disponibili
    print(f"\n2. Settori disponibili (primi 20):")
    available_sectors = analyzer.get_available_sectors()[:20]
    for i, sector in enumerate(available_sectors, 1):
        print(f"   {i:2}. {sector}")
    
    # 4. Analizza un settore specifico
    print(f"\n3. Analisi settore Banking...")
    
    # Parametri target della struttura finanziaria
    target_de = 0.5      # 50% debt/equity ratio
    target_tax = 0.25    # 25% tax rate
    
    banking_analysis = analyzer.analyze_sector(
        'Banking', 
        target_de_ratio=target_de,
        target_tax_rate=target_tax
    )
    
    if not banking_analysis.empty:
        print("\nRisultati analisi Banking:")
        print(banking_analysis.to_string(index=False))
        
        # Calcola average levered beta
        avg_beta = analyzer.calculate_weighted_average_beta(banking_analysis)
        print(f"\nAverage Levered Beta (ponderato per numero aziende): {avg_beta:.4f}")
        
        # Esporta risultati
        filename = analyzer.export_analysis(banking_analysis)
    
    # 5. Confronto multi-settoriale
    print(f"\n4. Confronto multi-settoriale...")
    
    sectors_to_compare = ['Banking', 'Technology', 'Healthcare', 'Energy', 'Retail']
    comparison = analyzer.compare_sectors(
        sectors_to_compare,
        target_de_ratio=target_de,
        target_tax_rate=target_tax
    )
    
    if not comparison.empty:
        print("\nConfronto settoriale (ordinato per beta decrescente):")
        print(comparison.to_string(index=False))
        
        # Esporta confronto
        comparison.to_csv('sector_comparison.csv', index=False)
        print("\nConfronto esportato in: sector_comparison.csv")

if __name__ == "__main__":
    main_example()

# =============================================================================
# NOTE METODOLOGICHE
# =============================================================================
"""
FONTI DATI:
- Database Aswath Damodaran, NYU Stern School of Business
- Aggiornamento: Gennaio 2025
- URL: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/data.html

METODOLOGIA CALCOLO BETA:
1. Beta Levered Originale: Media semplice dei beta delle aziende del settore
2. Beta Unlevered: β / (1 + (1-T) × (D/E)) 
3. Beta Levered Target: βU × (1 + (1-T_target) × (D/E)_target)

FORMULE:
- Hamada Formula: βL = βU × (1 + (1-T) × (D/E))
- Media Ponderata: Σ(βi × wi) / Σ(wi), dove wi = numero aziende per regione

LIMITAZIONI:
- I dati riflettono condizioni di mercato al momento dell'aggiornamento
- I beta sono stimati su base storica e potrebbero non riflettere rischi futuri
- La categorizzazione settoriale segue la classificazione Damodaran

RACCOMANDAZIONI:
- Utilizzare beta unlevered corretti per la liquidità quando possibile
- Considerare multiple regioni per robustezza delle stime
- Aggiornare periodicamente i dati
- Verificare la coerenza della classificazione settoriale
"""