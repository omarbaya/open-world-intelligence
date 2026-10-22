# OPEN WORLD Intelligence Desk 3.0 — installazione iPhone

L’installer GitHub V3 è già configurato. Il sito corrente V2 resta online finché l'importazione non è completata.

## 1. Carica il solo ZIP

Scarica da ChatGPT `OPEN_WORLD_V3_DEPLOY.zip`. Apri Safari:
https://github.com/omarbaya/open-world-intelligence/upload/main

Carica lo ZIP **non estratto**, mantenendo esattamente il nome `OPEN_WORLD_V3_DEPLOY.zip` e premi **Commit changes**.

Il workflow `Installa OPEN WORLD 3.0 dallo ZIP`:
- estrae HTML originale Claude inalterato;
- importa codice e agenti Gemini;
- esegue test;
- raccoglie RSS;
- pubblica le tre interfacce su GitHub Pages.

Azioni: https://github.com/omarbaya/open-world-intelligence/actions/workflows/import-v3.yml

## 2. Attiva i 6 agenti IA

Genera una API key **Free Tier** su https://aistudio.google.com/apikey . Non attivare fatturazione se vuoi evitare costi.

Salva la chiave solo in GitHub: https://github.com/omarbaya/open-world-intelligence/settings/secrets/actions , **New repository secret**. Nome: `GEMINI_API_KEY`. Non condividere lo screenshot della chiave.

Poi apri https://github.com/omarbaya/open-world-intelligence/actions/workflows/refresh.yml , seleziona **Run workflow**, spunta `generate_ai` e avvia.

## Link

- Dashboard originale, identica nel codice: https://omarbaya.github.io/open-world-intelligence/original/
- Agenti IA e analisi in italiano: https://omarbaya.github.io/open-world-intelligence/ai/
- Monitor notizie: https://omarbaya.github.io/open-world-intelligence/

## Stato

Il caricamento ZIP e il secret devono essere completati per attivare il nuovo sistema. Un progetto GitHub pubblico non deve contenere chiavi private. Il free tier Google impone limiti: se finisce la quota, le news continuano ad aggiornarsi e la dashboard mostra «IA non disponibile».
