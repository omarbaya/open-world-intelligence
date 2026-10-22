# Attivare gli agenti AI da iPhone

1. Crea una chiave del piano gratuito su https://aistudio.google.com/apikey
2. Vai su https://github.com/omarbaya/open-world-intelligence/settings/secrets/actions
3. Tocca **New repository secret**. Nome: **GEMINI_API_KEY**. Incolla la chiave come valore e salva.
4. Avvia https://github.com/omarbaya/open-world-intelligence/actions/workflows/refresh.yml con **Run workflow**, branch main.
5. Apri https://omarbaya.github.io/open-world-intelligence/ e verifica il pannello AI.

Non condividere la chiave nella chat. Il modello invia a Google solo notizie pubbliche, e il piano gratuito ha limiti di utilizzo e può usare gli input per migliorare i propri prodotti.
