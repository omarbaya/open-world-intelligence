"""Agents 3+4: transparent deterministic tagging, clustering, verification metadata.

No news fact is declared verified merely because similar headlines occur in RSS.
No causal or probability judgments are generated automatically.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import re

TOPICS = {
 "Russia–Ucraina": ["ukrain","russia","moscow","kyiv","kremlin","zelensk","putin","ucrain","russie","russland"],
 "Medio Oriente": ["israel","gaza","hamas","iran","hezbollah","leban","liban","palestin","tehran","tel aviv","netanyahu","israele"],
 "Golfo e Mar Rosso": ["houthi","yemen","red sea","hormuz","strait","saudi","gulf","shipping","mar rosso","golfo"],
 "Cina–Taiwan": ["taiwan","beijing","china","xi jinping","south china sea","taipei","pechino"],
 "Energia": ["oil ","petrol","brent","wti","opec","natgas","natural gas","lng","ttf","energy","gas prices","crude"],
 "Macro e banche centrali": ["inflation","interest rate","central bank","federal reserve","ecb","eurozone","gdp","payroll","consumer price","fed ","bank of england","bce","inflazione","tassi","bond yield","powell"],
 "Mercati e difesa": ["s&p","nasdaq","stock market","equities","earnings","gold price","futures","contract","defense","defence","aerospace","leonardo drs","ducommun","kratos","national presto","curtiss-wright","moog","aerosystems"]
}
ALERT_WORDS = {
 "interruzione rotte": ["strait closed","strait closure","hormuz blocked","red sea attacks","shipping halted"],
 "militare": ["missile attack","airstrike","invasion","nuclear threat","declares war","ceasefire collapsed"],
 "banche centrali": ["emergency rate","unscheduled meeting","surprise rate","unexpected hike","unexpected cut"],
 "finanza": ["market crash","trading halted","bank failure","default on debt"]
}
STOP = set("the of to on for and in from after amid as with a an is at by says said has have its that about new over into will are was be it this what why how le la il un una con nel dalla sul da per di del che i gli in su la et des est and at from says du et une de les au la".split())

def tokens(text):
    return {w for w in re.findall(r"[a-zà-ÿ0-9]{3,}", (text or "").lower()) if w not in STOP}

def categorise(headline, summary):
    content = (headline + " " + summary[:220]).lower()
    matched = [(name,sum(content.count(w) for w in words)) for name,words in TOPICS.items()]
    ordered = [k for k,v in sorted(matched,key=lambda x:-x[1]) if v]
    return ordered[:3] or ["Altre notizie"]

def relevance(item):
    text=(item["title"]+" "+item.get("summary","")).lower()
    topic=item.get("topics",[])
    points=2 if topic!=["Altre notizie"] else 0
    points+=2 if item["source_type"]=="primary" else 0
    points+=min(2,sum(1 for w in ("breaking", "announces", "decision", "emergency", "agreement", "attack", "rates", "earnings") if w in text))
    return points

def similarity(a,b):
    # Headline-only similarity intentionally conservative.
    ta,tb=tokens(a),tokens(b)
    if min(len(ta),len(tb))<4: return 0.0
    return len(ta & tb)/max(1,len(ta | tb))

def cluster_articles(articles):
    clusters=[]
    for item in articles:
        joined=False
        for cluster in clusters:
            if len(cluster["members"]) >= 12: continue
            exemplar=cluster["members"][0]
            if item["source"]==exemplar["source"]: continue
            if similarity(item["title"],exemplar["title"]) >= .50:
                cluster["members"].append(item)
                joined=True
                break
        if not joined: clusters.append({"members":[item]})
    for cl in clusters:
        members=cl["members"]
        names=sorted({m["source"] for m in members})
        cl.update({"headline":members[0]["title"],"sources":names,"source_count":len(names),"articles":[m["id"] for m in members],
                   "status":"titoli simili su più fonti; fatti non verificati" if len(names)>1 else "una sola testata"})
        del cl["members"]
    return [c for c in clusters if len(c["articles"])>1][:35]

def analyse(articles,now=None):
    now=now or datetime.now(timezone.utc)
    recent=[]
    for a in articles:
        a=a.copy()
        stamp=datetime.fromisoformat(a["published_at"].replace("Z","+00:00"))
        if now-timedelta(hours=48) <= stamp <= now+timedelta(minutes=10):
            a["topics"]=categorise(a["title"],a.get("summary",""))
            a["relevance"]=relevance(a)
            a["article_age_hours"]=round((now-stamp).total_seconds()/3600,1)
            # Institutional communications are primary evidence of that institution's claims,
            # not independent confirmation of the truth of external allegations.
            a["verification"] = ("fonte primaria: dichiarazione ufficiale" if a["source_type"]=="primary" else "notizia riportata dalla testata; non verificata indipendentemente")
            recent.append(a)
    recent.sort(key=lambda a:(a["relevance"],a["published_at"]),reverse=True)
    selected=recent[:250]
    topic_stats=[]
    for topic in list(TOPICS)+["Altre notizie"]:
        subset=[a for a in selected if topic in a["topics"]]
        if subset:
            names={a["source"] for a in subset}
            topic_stats.append({"topic":topic,"articles":len(subset),"sources":len(names),"recent":subset[0]["published_at"]})
    topic_stats.sort(key=lambda item:item["articles"],reverse=True)
    alerts=[]
    for a in selected:
        text=a["title"].lower()
        matches=[key for key,terms in ALERT_WORDS.items() if any(term in text for term in terms)]
        if matches:
            alerts.append({"article_id":a["id"],"title":a["title"],"source":a["source"],"published_at":a["published_at"],"url":a["url"],"match":matches,
                           "label":"parole chiave: richiede controllo umano"})
    return selected, topic_stats, cluster_articles(selected), alerts[:30]
