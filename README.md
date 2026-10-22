# OPEN WORLD Intelligence Desk 3.1 — Claude original + Gemini Cloud Free

Ricostruzione fedele dell'interfaccia **originale Claude** (`site/original/assets/original-claude-dashboard.html`, stessa sequenza di byte dell'archivio fornito) con una pipeline dati open-source indipendente. È disponibile in parallelo la dashboard OPEN WORLD V2 e il nuovo pannello agenti IA.

## Link dopo importazione

- Originale **identico nel design**: `https://omarbaya.github.io/open-world-intelligence/original/`
- Agenti AI, traduzione e analisi: `https://omarbaya.github.io/open-world-intelligence/ai/`
- Monitor fonti: `https://omarbaya.github.io/open-world-intelligence/`

## Cosa è davvero attivo

- Raccolta RSS/Atom ogni ora via GitHub Actions, deduplicazione e fonti attribuite.
- FRED (serie storiche, NON live) e `n.d.` dove i prezzi non sono verificati.
- Sette ruoli IA basati sulla stessa API Google Gemini: geopolitica, macro/mercati, difesa, Capo Desk, verificatore, Insegnante, Revisore finale. Sono **sette invocazioni logiche sequenziali** dello stesso modello, non sei modelli sempre residenti.
- Lettura delle pagine pubbliche quando accessibili; se bloccate, stato `solo RSS`, nessun bypass.
- Traduzione in italiano, spiegazione del perché conta e impatto *condizionale* su oro, euro e S&P 500. Niente istruzioni di acquisto/vendita.
- Revisione con fonte-id validato contro il dossier reale; il Verificatore IA è una critica automatica, NON una seconda fonte indipendente.
- Diario metodologico che registra i rilievi e li reintroduce nei briefing successivi. Nessun auto-edit del codice o delle regole, nessun aggiornamento automatico dei pesi del modello.
- Previsioni: registro immutabile esistente e Brier solo sulle previsioni chiuse con prove; niente percentuali inventate.
- L'HTML originale e i componenti visivi sono preservati; il diario privato di Claude usa un database proprietario, quindi **non è disponibile** nel sito pubblico (non pubblichiamo informazioni personali).

## Abilitazione cloud IA — passaggio obbligatorio dell'account

Google AI Studio offre un tier gratuito nei limiti della quota. Il sistema non usa crediti Claude. **La IA non funziona finché il proprietario non crea la propria chiave**:

1. Apri `https://aistudio.google.com/apikey` e crea una API key su un progetto **Free Tier**. Non attivare billing se desideri 0 €.
2. Vai a `https://github.com/omarbaya/open-world-intelligence/settings/secrets/actions` → **New repository secret**.
3. `Name`: `GEMINI_API_KEY`. `Secret`: la chiave generata. Salva. Non condividere la chiave in chat, screenshot o file pubblici.
4. Apri `https://github.com/omarbaya/open-world-intelligence/actions/workflows/refresh.yml` → Run workflow → **generate_ai = true**. GitHub Actions esegue il codice lato server e non esporta la chiave nel browser.
5. Consulta `/ai/` e verifica che lo stato sia «IA generativa attiva». Prima dell'installazione della chiave, lo stato indica esplicitamente «non configurato».

API scelta: `gemini-3.5-flash-lite` di default. Limiti/tier e disponibilità dipendono dal progetto Google, possono cambiare. Le notizie pubbliche inviate alla API nel free tier possono essere usate dal provider per migliorare i suoi prodotti, secondo le condizioni applicabili. Non inviare dati personali.

## Esecuzione

Esegue ogni ora, briefing ogni mattina alle 08:50 ora di Atene (gestione automatica DST Europe/Athens). GitHub Actions non garantisce istantaneità e può saltare o ritardare le esecuzioni. Se mancano chiave, quota o una fonte, aggiorna la pipeline deterministica; l'IA indica errore o non configurata, non inventa un risultato.

Manuale in locale:

```sh
python -m unittest discover -s tests -v
python scripts/refresh.py
GEMINI_API_KEY='...' python scripts/ai_daily.py --force
python scripts/serve.py
```

**Protezione**: chiave SOLO come GitHub Actions Secret; mai in JavaScript, HTML, log o Git. La API è chiamata da Python tramite header `x-goog-api-key`.

**Vincoli dell'originale:** 20 sezioni, righe a 26 chiavi e JSON storico. Al posto dei dati del 20 ottobre, l'adattatore produce contenuti attuali con `n.d.` dove non esiste una fonte verificata. Diagrammi e mappa mantengono gli stessi componenti. Il diario Claude proprietario rimane inattivo.

## Privacy dei file originali

Il prompt storico di Claude con riferimenti personali non è incluso nei file destinati al repository GitHub **pubblico**. Il codice della dashboard originale è incluso identico, e le regole operative rilevanti sono implementate nei moduli Python. La copia integrale del prompt originale resta negli archivi Claude forniti dall’utente. Il diario privato non viene esportato né pubblicato.

## Metodo Claude (kit 22 ottobre 2026)

I sette prompt separati sono in `config/prompts/`, con le regole comuni in `common.md`. Validazione JSON (`jsonschema`), scarto notizie fuori finestra, calcolo degli indicatori e registro immutabile delle previsioni sono implementati in Python. Il workflow mantiene la dashboard originale e pubblica i dati RSS ogni ora, conservando il briefing IA quotidiano. Le nuove previsioni prive di valore di riferimento verificabile sono respinte. Le tensioni dei fronti e le inclinazioni ES/GC/6E sono interpretazioni, NON fatti o consigli di trading. Vedi `docs/METHOD_KIT_2026_10_22.md`.
