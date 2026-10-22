# Specifica dei ruoli e criteri di apprendimento

| Ruolo | Input | Output | Frequenza |
|---|---|---|---|
| Geopolitica | feed attribuiti, link, testo pubblico accessibile | titoli tradotti, fatti attribuiti, impatti ipotetici | 1 volta/giorno |
| Macro | dati e notizie Fed/BCE/energia/mercati | spiegazione macro e scenari condizionali | 1 volta/giorno |
| Difesa | notizie e comunicati dei titoli seguiti | spiegazioni contratti/titoli | 1 volta/giorno |
| Verificatore | analisi + ID fonte + estratti | segnalazioni su inesattezze/non-provato | 1 volta/giorno |
| Capo Desk | output agenti, revisione, dataset FRED | briefing italiano in sezioni | 1 volta/giorno |
| Apprendimento | feedback passati, quote disponibili, forecast ledger | osservazioni e suggerimenti (non modifica prompt) | 1 volta/giorno |

**Risultati**: `site/data/ai/YYYY-MM-DD.json`, `site/data/latest_ai.json`, `site/data/ai/history.json`. Le analisi del giorno sono pubbliche. Non inviare dati personali.

**Qualità**: un modello IA che legge un articolo non costituisce un secondo testimone indipendente. Le etichette `riportato da...` non vengono elevate automaticamente a Verificato. Il modello non può introdurre ID/URL inesistenti. Il livello di certezza viene forzato in modo prudenziale in `verified_items`. Il riassunto potrebbe comunque contenere errori: controlla sempre la fonte.

**Apprendimento**: ogni giorno l'output `learning` cita le criticità del giorno e lo storico recente. Le osservazioni vengono riutilizzate nelle richieste successive; non c'è fine-tuning, apprendimento dei parametri o modifica autonoma del codice. Le previsioni originali non vengono riscritte. Le ipotesi nuove richiedono criteri verificabili.

### Aggiornamento 22 ottobre 2026: sette ruoli
Il sistema esegue `geopolitica`, `macro`, `difesa`, `capo_desk`, `verificatore`, `apprendimento` (Insegnante) e `revisore_finale`. Prompt autonomi in `config/prompts/`. Schema JSON validato via `jsonschema` con una sola ripetizione. Verificatore automatico non è un secondo testimone della notizia. Le verifiche quantitative sono Python, il diario registra proposte, non riscrive autonomamente codice o prompt.
