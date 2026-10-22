# OPEN WORLD 3.1 – Metodo del Desk Claude, adattamento per GitHub/Gemini

Fonte: kit del 22 ottobre 2026 fornito dal proprietario del Desk. La dashboard originale Claude (`site/original/assets/original-claude-dashboard.html`) non viene modificata.

## Pipeline
1. Dati freschi RSS e FRED, memoria, ultima lezione e registro.
2. Filtraggio 48 ore (timestamp RSS), apertura di pagine pubbliche e controllo di metadati data pagina dove presenti.
3. Tre agenti specialisti: geopolitica/energia, macro/mercati, difesa.
4. Indicatori Python su dati disponibili, con `null` per input mancanti.
5. Capo Desk scrive la bozza e propone eventuali previsioni verificabili.
6. Verificatore controlla incoerenze, id fonte e numeri non supportati.
7. Insegnante genera una lezione; Revisore finale propone note di metodo senza cambiare regole.
8. Dashboard identica, dati in `site/original/data/`, storico fino a 400 giorni e registro append-only `state/forecast_events.jsonl`.

## Prompt dei sette ruoli
Si trovano in `config/prompts/` insieme a `common.md`: `geopolitica.md`, `macro.md`, `difesa.md`, `capo_desk.md`, `verificatore.md`, `apprendimento.md` (Insegnante), `revisore_finale.md` (diario).

## Verifiche rigorose
- JSON `jsonschema` con una sola ripetizione se output malformato.
- Informazione primaria e reporting giornalistico non confusi con verità indipendentemente dimostrata.
- Prezzi FRED sono ritardati, non streaming. Due testate possono riprendere la stessa agenzia: ciò non prova indipendenza.
- Nessun numero assente dal dossier può sopravvivere senza marcatura `n.d.` (guardia conservativa; non è un motore di fact-checking universale).
- Nessuna previsione è pubblicata nel registro se mancano riferimento numerico, fonte, data, criteri, probabilità 20–85% e verifica del valore sugli input. Previsioni non verificate restano proposte.
- Le stime di tensione degli agenti non diventano automaticamente dati verificati: se non supportate restano `null`.
- `GEMINI_API_KEY` solo come GitHub Actions Secret; **mai** in repository, HTML o output JSON.

## Limiti non risolti
- I sette agenti sono sette chiamate/ruoli dello stesso Gemini, non sette modelli indipendenti sempre attivi. Il livello gratuito non garantisce sette chiamate al giorno.
- Lo stato «validato» del JSON significa struttura corretta, non verificazione esterna della notizia.
- Il filtro sulle notizie vecchie privilegia la data RSS e, quando disponibile, un metadato della pagina; nessun sistema di estrazione automatica copre ogni testata.
- Alcuni mercati (futures, TTF, quotazioni difesa) non hanno ancora doppia fonte gratuita confrontabile; rimangono `n.d.`.
- Quattro analisi trimestrali del vecchio Desk non sono state portate in questa versione.
- Le previsioni storiche Claude rimangono in `state/original_forecasts.json` senza inventare esiti. La valutazione del 22 ottobre riportata nel kit non viene reimportata finché non ci sono prove pubbliche allegabili per le chiusure.
- La lettura settimanale degli orientamenti ES/GC/6E è archivabile, ma uno scoring di mercato richiede prezzi confrontabili con periodo/strumento esatto.
- Il codice può aggiornare memoria e diario, non i pesi del modello Gemini.

## Test
`python -m pip install -r requirements.txt` poi `python -m unittest discover -s tests -v`. La sorgente della dashboard originale non deve mai cambiare.
