# OPEN WORLD 3.2 — API GRATUITE E CONTROLLO QUALITÀ

Versione: 22 ottobre 2026. Zero API a pagamento, nessuna fatturazione abilitata.

## Già collegate senza registrazione

- **Finance Calendar**: https://www.financecalendar.com/api/ — calendari ufficiali di banche centrali, eventi macro entro 30 giorni, orari convertiti IANA `Europe/Athens`. Max un prelievo ogni 6 ore, livello senza chiave 2.000 richieste/giorno per IP. **OBBLIGO** di attribuzione con link visibile a `financecalendar.com`: rispettato in `/sources/` e nella riga calendario della dashboard. `consensus`, `previous`, `actual` restano `null` se la fonte non li pubblica. La fonte attuale dichiara che non raccoglie ancora sistematicamente il consenso.
- **BCE**: https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata&lastNObservations=3 — cambi EUR/USD ufficiali della giornata di riferimento, non live. L'osservazione porta data e stato di staleness.
- **Gold API**: https://api.gold-api.com/price/XAU — XAU/USD spot indicativo, con timestamp.
- **XAUS**: https://xaus.com/api/v1/spot — seconda lettura spot indicativa; **può dipendere a monte da Gold API**. Non vale da sola come fonte indipendente. https://xaus.com/api/v1/history — OHLC spot completate, max/min e chiusura, non futures GC/MGC.
- **CFTC ufficiale**: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm — Legacy Futures Only, net non-commerciali = long − short per Oro, Euro FX e E-mini S&P 500. Report settimanale (posizioni del martedì), non serie live.
- **FRED** esistente: CSV ritardati di SPX/VIX/Treasury/Brent/WTI, nessuna API key obbligatoria per l'endpoint grafico già usato. **Non considerare SP500 indice cash come futuro ES**.

## API opzionali, solo livelli gratuiti

1. **METALS_DEV_API_KEY** · https://metals.dev/pricing · 100 richieste/mese gratis, max una richiesta ogni 25h; controllo terzo indipendente dell'oro; la verifica delle fonti si esegue solo su timestamp ravvicinati, scostamenti >0,5% risultano `conflict`, non prezzo certo.
2. **ALPHAVANTAGE_API_KEY** · https://www.alphavantage.co/support/ · 25 richieste/giorno, modello EOD di sei società difesa e barre forex giornaliere; niente live USA. Il ticker **IA** resta deliberatamente escluso finché la società non è identificata in modo verificabile.
3. **FMP_API_KEY** · https://site.financialmodelingprep.com/pricing-plans · piano Basic gratuito 250 richieste/giorno, alternativa alle quotazioni giornaliere di Alpha Vantage; endpoint non incluso nel piano -> `n.d.`, nessun upgrade automatico.
4. **FINANCECALENDAR_API_KEY** · chiave opzionale per 10.000 richieste/giorno gratuite; chiave non necessaria col ritmo configurato.
5. **FRED_API_KEY** · https://fred.stlouisfed.org/docs/api/api_key.html · facoltativa per estendere l'API economica primaria successivamente.

**Solo in** GitHub → Settings → Secrets and variables → Actions → New repository secret. Copia i nomi *esatti*. Mai inserire chiavi nei file, nel prompt, nelle Issues, negli screenshot o in Pages. Il livello API Gemini rimane separato dall'abbonamento Gemini personale.

## Scheduler

- GitHub Actions: RSS e controlli fonti **ogni ora** (`17 * * * *` UTC); cache 1h (prezzi), 6h (BCE/calendario), 12h (OHLC oro), 27h (COT), 26h (dati defense EOD). I cron possono avviarsi in ritardo.
- Brief Gemini: **08:50 ora Atene**, con doppio cron per gestire il cambio d'ora Europa/Atene e guardia software anti-duplicazione.
- Se un API è inaccessibile o ha esaurito la quota: non inventare dati, mostra errore/provenienza; news e dashboard restano attive.
- `site/data/free_data.json`: cache JSON senza chiavi e stato delle fonti; i provider non vengono interrogati più spesso del budget scelto.

## Limiti tecnici da rispettare

- L'oro spot da `gold-api.com` e `xaus.com` può condividere lo stesso upstream: non equivale a doppia verifica indipendente finché non entra un feed autonomo.
- I futures CME realtime ES/GC/6E non sono gratuiti con le licenze ufficiali; i sottostanti SPX cash / XAU spot / EURUSD spot hanno **etichette diverse**. Il codice non esegue ordini o segnali.
- Un dato presente nell'API non garantisce una licenza di ridistribuzione generale: rispettare licenze e condizioni di ogni provider, soprattutto per vendor EOD azioni.
- Gli orari degli eventi senza precisione esatta restano `Da confermare`. Nessun consenso economico dedotto o inventato.
- `DXY`, TTF e future CME restano `n.d.` finché non esiste una fonte gratuita specifica, legittima e verificata.
- L'algoritmo 7 sentiment è **strict**: niente calcolo canonico con componenti assenti.

## Test

`python -m unittest discover -s tests -v`

Audit: https://omarbaya.github.io/open-world-intelligence/sources/
