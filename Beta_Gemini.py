# Gemini
import pandas as pd

def calcola_average_levered_beta_settoriale(paesi_di_interesse):
    """
    Questa funzione scarica i dati di Damodaran sui beta settoriali,
    li elabora e calcola l'average levered beta per i settori
    dei paesi specificati.

    Args:
        paesi_di_interesse (list): Una lista di stringhe con i nomi dei paesi.

    Returns:
        pandas.DataFrame: Un DataFrame con l'average levered beta per settore
                          per ogni paese di interesse.
    """
    try:
        # URL del file Excel di Damodaran (aggiornato periodicamente)
        # Questo link punta ai dati più recenti disponibili.
        url = "https://www.stern.nyu.edu/~adamodar/pc/datasets/beta.xls"

        # Caricamento del foglio di lavoro specifico che contiene i dati per paese.
        # Il foglio si chiama 'Country'
        # L'opzione header=6 indica che l'intestazione della tabella si trova alla settima riga.
        df = pd.read_excel(url, sheet_name='Country', header=6)

        # Pulizia dei dati: Rimuoviamo righe e colonne non necessarie.
        # Rimuoviamo le righe che contengono valori nulli nelle colonne chiave
        df.dropna(subset=['Country', 'Industry Name', 'Levered Beta'], inplace=True)

        # Selezioniamo solo le colonne di nostro interesse
        colonne_utili = ['Country', 'Industry Name', 'Levered Beta']
        df = df[colonne_utili]

        # Filtriamo il DataFrame per includere solo i paesi di nostro interesse
        df_filtrato = df[df['Country'].isin(paesi_di_interesse)]

        # Raggruppiamo per Paese e Settore e calcoliamo la media del Levered Beta
        # Questo passaggio è fondamentale se un settore avesse più voci per un paese.
        risultato = df_filtrato.groupby(['Country', 'Industry Name'])['Levered Beta'].mean().reset_index()

        # Rinominiamo la colonna per chiarezza
        risultato.rename(columns={'Levered Beta': 'Average Levered Beta'}, inplace=True)

        return risultato

    except Exception as e:
        print(f"Si è verificato un errore: {e}")
        print("Verifica che l'URL sia ancora valido o che la struttura del file Excel non sia cambiata.")
        return None

# Esempio di utilizzo della funzione
# Puoi modificare questa lista per includere i paesi che ti interessano.
nazioni = ['Italy', 'United States']

# Calcolo dei dati
beta_settoriali = calcola_average_levered_beta_settoriale(nazioni)

# Stampa dei risultati
if beta_settoriali is not None:
    print("Average Levered Beta per Settore:")
    # Impostiamo pandas per mostrare tutte le righe del risultato
    pd.set_option('display.max_rows', None)
    print(beta_settoriali)