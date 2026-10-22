# OPEN WORLD — Intelligence Desk 2.0 (Free Edition)

Sistema **nuovo e indipendente da Claude** costruito a partire dalla struttura funzionale del progetto OPEN WORLD fornito dall'utente. Solo **Python 3.11+ e libreria standard** per il core. Dashboard web responsive senza dipendenze CDN. Nessuna chiave o token richiesti per la modalità standard.

## Il risultato concreto

- 12 fonti RSS/Atom di notizie e comunicazioni ufficiali; pipeline parallela con errori e latenza registrati.
- 7 indicatori di mercato/macro attraverso download CSV pubblici FRED, datati, con valori precedente e variazione; 5 strumenti dichiarati **n.d.** dove non è disponibile una fonte gratuita verificata.
- Motori indipendenti: ingestione, macro, classificazione, raggruppamento prudenziale, segnalazioni, briefing, forecast journal. **Non sono agenti LLM nel cloud**.
- Dashboard con notizie, filtri, aree di crisi, segnali a keyword, gruppi multi-testata, mercati, pannello metodologico, previsioni e storico.
- Brief giornaliero dall'esecuzione delle 08:50 ora di Atene: testo italiano di contorno, collegamenti e titoli nella lingua originale; 13 rubriche compatibili concettualmente con l'originale, le rubriche senza dati sono marcate **n.d.**.
- Formule originali PASSO 3 conservate in `core/indicators_original.py`. Market stress calcolato **solo da input sufficienti e freschi**, e dichiarato come media parziale se manca DXY. Macro risk, escalation, global risk e probabilità **non sono inventati**.
- Registro previsioni append-only e Brier calcolato con probabilità originale, se sono stati inseriti manualmente eventi precisi e risultati documentati.
- Backup dello storico quotidiano e generazione di JSON statici; l'app non raccoglie dati privati né telemetria.
- Opzione **AI locale con Ollama**, non attiva sul cloud gratuito: `scripts/local_ai.py`.

## Esecuzione su Mac/Windows/Linux

```bash
cd OPEN_WORLD_INTELLIGENCE_FREE
python3 -m unittest discover -s tests -v
python3 scripts/refresh.py
python3 scripts/serve.py
```

Apri **http://127.0.0.1:8787** nel browser. Serve una connessione Internet per scaricare feed e serie FRED. `refresh.py` è un aggiornamento una tantum; per aggiornamenti continui eseguilo periodicamente con il scheduler del sistema oppure usa GitHub Actions qui sotto. Non avviare `index.html` tramite `file://`, perché il browser non leggerà i JSON locali.

Su Windows usa `py` al posto di `python3` se necessario.

## Metterlo online 24/7 senza Claude

**Non è ancora pubblicato.** Serve una repository GitHub (pubblica se si usa Pages con piano gratuito).

1. Entra in GitHub e crea un repository **pubblico** nuovo, per esempio `open-world-free`, senza aggiungere README online.
2. Estrai questo ZIP e carica il contenuto della cartella del progetto nella **radice del repository**, includendo `.github/workflows/refresh.yml` e le cartelle nascoste (controlla che GitHub mostri `.github`). Con `git`:
   ```bash
   git init && git add . && git commit -m "OPEN WORLD free desk"
   git branch -M main
   git remote add origin https://github.com/TUO-USERNAME/open-world-free.git
   git push -u origin main
   ```
3. Vai su **Settings → Pages → Build and deployment → Source: GitHub Actions** e salva.
4. Vai su **Actions → OPEN WORLD · aggiornamento gratuito → Run workflow** per la prima raccolta. Se il workflow è stato bloccato, abilitalo dalla pagina Actions.
5. Il sito sarà all'indirizzo `https://TUO-USERNAME.github.io/open-world-free/`. L'azione girerà **ogni ora al minuto :17 UTC**, più ai minuti compatibili con **08:50 Europe/Athens** nei diversi periodi dell'anno. Gli orari programmati possono essere posticipati o saltati da GitHub.
6. Controlla periodicamente **Actions** per gli errori. Se l'account o il repository risultano inattivi per 60 giorni, GitHub può disabilitare i workflow programmati; riabilitali dalle impostazioni.

GitHub Pages e GitHub Actions sono gratuiti per repository pubblici con runner standard, **nei limiti delle condizioni attuali di GitHub**. Il repository e i dati pubblicati diventano **pubblici**: NON inserire password, diario personale, documenti riservati o credenziali. La pubblicazione di serie finanziarie può essere soggetta alle licenze dei rispettivi titolari: verifica le condizioni di ripubblicazione prima di aprire il sito al pubblico.

## Agente AI gratuito *vero* (facoltativo, sul proprio Mac)

1. Installa [Ollama](https://ollama.com/) sul tuo computer.
2. `ollama pull qwen3:4b` (richiede download e RAM).
3. `python3 scripts/refresh.py`.
4. `python3 scripts/local_ai.py` oppure `OLLAMA_MODEL=nome_modello python3 scripts/local_ai.py`.

L'analisi viene scritta in `site/data/ai_analysis.json` e mostrata nell'area «Brief del giorno», marcata *non verificata*. Richiede che il computer sia **acceso**; un modello locale può sbagliare o allucinare. Non è la stessa cosa di quattro agenti Sonnet+Opus sempre attivi nel cloud e senza costi. Questa funzione è separata dal servizio standard e non è richiesta per l'aggiornamento della dashboard.

## Gli 8 passi rispetto all'originale

| PASSO originale | Nuovo workflow |
|---|---|
| 1 Leggi il desk | Legge la precedente fotografia JSON, lo storico e il giornale append-only |
| 2 Ricerca task force | Raccoglie RSS/Atom e CSV FRED in parallelo; NON esegue OpenAI/Claude web agent |
| 3 Indicatori | Riusa la formula di stress sui dati realmente disponibili; altri indici n.d. in assenza di base fattuale |
| 4 Brief 13 sezioni | Crea una rassegna attribuita; sezioni non verificabili riportano n.d., non storie inventate |
| 5 Previsioni | Registro append-only manuale con regole Brier originali |
| 6 Documento | Salva ogni giorno un JSON+Markdown in `site/data/briefs/` |
| 7 Dashboard | Pubblica `latest.json`, `history.json`, brief+stato per la dashboard nuova |
| 8 Consegna | Pubblicazione web su Pages; notifiche GitHub per errori del workflow secondo impostazioni utente |

## Che cosa NON è

- Non è un terminale con dati di borsa *tick-by-tick* o newswire Reuters/Bloomberg; feed e serie hanno latenza variabile e alcuni media offrono solo titoli.
- Non certifica la verità di un evento con il solo confronto dei titoli. Le comunicazioni istituzionali restano dichiarazioni ufficiali del rispettivo ente.
- Non calcola probabilità di eventi geopolitici o analisi causali senza fonti sufficienti.
- Non garantisce uptime perfetto: GitHub Actions può subire ritardi, riduzione di quota o disattivazione; servizi esterni possono cambiare URL o policy.
- Non offre automaticamente agenti AI multimodali cloud illimitati gratuiti.

## Directory

`core/` motori; `config/feeds.json` elenco RSS; `config/markets.json` strumenti;
`scripts/` avvio, webserver e registro; `.github/workflows/refresh.yml` schedule;
`site/` sito; `site/data/` archivio pubblico; `tests/` unit test;
`docs/` documenti implementativi. I file dell'archivio Claude **non sono ripubblicati**.

**Informazione, non consulenza finanziaria.**
