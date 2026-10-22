# Installazione OPEN WORLD 3.0 da iPhone

1. Pubblica `OPEN_WORLD_V3_DEPLOY.zip` nella **radice** del repository GitHub pubblico `omarbaya/open-world-intelligence` con Add file → Upload files. Non estrarre.
2. L'automazione `.github/workflows/import-v3.yml` estrae e testa il progetto e conserva il runtime esistente; non tenta di modificare workflow protetti.
3. Dopo una importazione verde, `.github/workflows/refresh.yml` può eseguire la raccolta e pubblicare su Pages.
4. **Per attivare realmente l'IA**: crea gratis una chiave sul sito AI Studio. Salvala come GitHub Actions Secret `GEMINI_API_KEY`. Non inviarla in chat.
5. Apri Actions → OPEN WORLD 3.0 → Run workflow → generate_ai=true. Se la quota gratuita è esaurita la dashboard lo dichiara e continua l'aggiornamento RSS.

URL:
- `/original/` = visuale originale Claude identica.
- `/ai/` = analisi agenti IA (attiva solo con secret valido).
- `/` = monitor fonti e mercati ritardati.
