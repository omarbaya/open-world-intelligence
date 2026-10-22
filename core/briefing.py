"""Agent 5: deterministic brief, with source links and no generated hypotheses."""
from datetime import datetime
from zoneinfo import ZoneInfo

ATHENS=ZoneInfo("Europe/Athens")

def brief_payload(payload):
    now=datetime.fromisoformat(payload["generated_at"].replace("Z","+00:00")).astimezone(ATHENS)
    news=payload["articles"]
    top=news[:5]
    by_topic={row["topic"]: [a for a in news if row["topic"] in a["topics"]][:5] for row in payload["topics"]}
    quote_rows = [m for m in payload["markets"] if m["value"] is not None]
    return {
       "date":now.date().isoformat(),"generated_local":now.strftime("%d/%m/%Y %H:%M %Z"),
       "headline":"Rassegna automatica da fonti aperte · nessuna sintesi AI inventata",
       "top":[{"title":a["title"],"source":a["source"],"published_at":a["published_at"],"url":a["url"],"verification":a["verification"]} for a in top],
       "topics":{key:[{"title":a["title"],"source":a["source"],"url":a["url"],"published_at":a["published_at"]} for a in vals] for key,vals in by_topic.items()},
       "markets":[{"name":m["name"],"value":m["value"],"unit":m["unit"],"date":m["observation_date"],"stale":m["stale"]} for m in quote_rows],
       "method":"Titoli originali classificati con regole trasparenti; non sostituisce l'analisi giornalistica né un analista umano.",
       "forecast_status":"Nessuna previsione probabilistica generata automaticamente. Registro separato e verificabile."
    }

def brief_markdown(brief):
    out=[f"# OPEN WORLD · {brief['date']}", f"Generato: {brief['generated_local']}","","> Rassegna automatica verificabile. I titoli rappresentano ciò che le fonti hanno pubblicato, non un fatto certificato.","", "## 1. In 60 secondi"]
    if not brief["top"]: out.append("Nessuna fonte disponibile: non pubblicare conclusioni.")
    for n in brief["top"]: out.append(f"- [{n['title']}]({n['url']}) — {n['source']} · {n['published_at']} · {n['verification']}")
    out.extend(["","## 2. Guerre e crisi","## 3. Mercati e dati disponibili"])
    if brief["markets"]:
        for m in brief["markets"]: out.append(f"- **{m['name']}**: {m['value']} {m['unit']} — osservazione {m['date']}" + (" (dato vecchio)" if m['stale'] else " (dato ritardato)"))
    else: out.append("n.d. — nessun dato di mercato collegato.")
    out.extend(["","## 4. Macro e banche centrali","## 5. Dalla geopolitica ai mercati","Nessuna causalità attribuita automaticamente: richiede una fonte esplicita.","","## 6. Agenda di oggi","n.d. — non è collegato un calendario ufficiale economico verificato.","","## 7. Difesa e titoli seguiti"])
    for topic, num in (("Guerre e crisi", "2"),("Macro e banche centrali", "4"),("Mercati e difesa", "7")):
        if num=="2": sections=["Russia–Ucraina","Medio Oriente","Golfo e Mar Rosso","Cina–Taiwan"]
        elif num=="4": sections=["Macro e banche centrali","Energia"]
        else: sections=["Mercati e difesa"]
        rows=[(t,a) for t in sections for a in brief["topics"].get(t,[])][:8]
        if rows:
            at=out.index(f"## {num}. " + {"2":"Guerre e crisi","4":"Macro e banche centrali","7":"Difesa e titoli seguiti"}[num]) + 1
            out[at:at]=[f"- {t}: [{a['title']}]({a['url']}) — {a['source']}" for t,a in rows]
    out.extend(["","## 8. Scenari a 7, 30, 90 giorni","Non calcolati automaticamente in assenza di un modello di previsione validato.","","## 9. Verifica delle previsioni",brief["forecast_status"],"","## 10. Valutazione finale","Sintesi causale non generata: si rimanda alle notizie attribuite alle fonti.","","## 11. Lezione del giorno","Nessuna lezione automatica per evitare spiegazioni non contestualizzate.","","## 12. Parole del giorno","VIX: indice della volatilità implicita attesa sull'S&P 500; non indica la direzione del prezzo.","","## 13. Fonti","Ogni titolo sopra contiene un collegamento alla fonte originale.","", "_Informazione, non consulenza finanziaria._"])
    return "\n".join(out)+"\n"
