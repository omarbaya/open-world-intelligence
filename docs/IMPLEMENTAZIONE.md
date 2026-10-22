# Contratto funzionale e limiti

## Sorgenti e indipendenza
- RSS BBC World, BBC Business, Guardian, Deutsche Welle, France 24, Al Jazeera, NPR, Politico Europe, ANSA, oltre a comunicati Fed e BCE. L'elenco è modificabile via `config/feeds.json`.
- Non estraiamo interi articoli protetti, solo title/description/link e date dal feed. I titoli in lingua originale NON sono tradotti automaticamente.
- News comparse su due testate possono derivare da una stessa agenzia: `cluster_articles` non fornisce fact-checking né prova di indipendenza.
- Serie macro e mercati da download FRED in CSV (non FRED API key). Fonte dati indicata per ogni osservazione, con timestamp del dato originale distinto dalla data di raccolta. Eventuali limitazioni sui diritti delle serie sono responsabilità di chi decide di ripubblicarle.

## Schema dashboard
`site/data/latest.json`: version, generated_at, last_news_success, news_unavailable, articles, topics, clusters, alerts, markets, quality, indicators, forecasts, daily_brief, warnings.
`site/data/history.json`: serie quotidiana fino a 400 giorni.
`site/data/briefs/YYYY-MM-DD.{json,md}`: briefing giornaliero con articoli citati.
`state/forecast_events.jsonl`: journal append-only locale, storico pubblicato in `latest.json` se inserito manualmente.

## Stato operativo dei motori
- `sources.py`: agent informazione. Dataset identificati da SHA256 fonte+URL; titolo e data validati, vecchie notizie escluse.
- `markets.py`: agent mercati, dati non live. Non scarica da endpoint di trading non documentati.
- `intelligence.py`: agent assegnazione topic, raggruppamento, scoring di rilevanza e keywords. Nessuna inferenza geopolitica quantitativa automatica.
- `briefing.py`: agent briefing 13 sezioni, testo statico + riferimenti reali, non analisi generativa cloud.
- `forecasts.py`: agent registro probabilità manuali, immutabili, punteggio Brier.
- `engine.py`: orchestrazione, snapshot e gestione fallback con indicatori originali.

## Indicatori PASSO 3
`core/indicators_original.py` è la formula scritta durante l'export del progetto Claude, non sostituisce la valutazione di tensione; nessuna tensione è dedotta da intensità dei titoli. Lo stress market viene indicato dopo almeno 3 componenti non stantie e riporta il rapporto componenti `3/5`, `4/5` o `5/5`. I componenti assenti sono esclusi dalla media, come nell'originale.
Gli altri tre indicatori rimangono `null` finché non esiste una fonte sufficiente a costruire gli input. `null` va sempre letto «n.d.».

## Failure states
Se tutti i feed falliscono: quality.feeds_ok=0, news_unavailable=true, last_news_success NON cambia, warnings contiene l'errore; l'ultimo contenuto può rimanere in cache solo se ancora dentro le 48h. Le serie market in cache vengono presentate con stale=true e mantengono l'originale observation_date. Non viene fabbricato un nuovo timestamp per un vecchio prezzo.

## Sicurezza
Feed XML elaborati da ElementTree, output titoli sanitizzato via DOM escape nelle schede HTML, link limitati a HTTP(S), solo HTTPS in acquisizione; nessun codice remoto eseguito da article title, kein cookie o login. Non salvare segreti in sito/JSON o git.

## Automatismi
Workflow GitHub due schedulazioni orarie stagionali e cron hourly. L'08:50 locale non è garantito al minuto perché GitHub può ritardare i job. Il brief nasce al primo job con orario locale almeno 08:50; ai cron di 05:50 e 06:50 UTC corrispondono alle 08:50 estiva/invernale rispettivamente.
