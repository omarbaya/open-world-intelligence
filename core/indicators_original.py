#!/usr/bin/env python3
"""AGGIUNTO PER L'ESPORTAZIONE – non fa parte del progetto originale.

Nel sistema originale gli indicatori NON sono calcolati da codice: il modello li calcola
ogni giorno seguendo le regole scritte nel PASSO 3 del prompt. Questo modulo traduce
quelle regole, alla lettera, in funzioni Python, per chi vuole ricostruire il sistema
con un altro agente e rendere i calcoli deterministici. Gli input soggettivi (tensione dei
fronti, tono di Fed/BCE, "attacchi in corso", ecc.) restano decisioni dell'agente.
"""

def label(v):
    return "Basso" if v < 25 else "Medio" if v < 50 else "Alto" if v < 75 else "Molto alto"

def conviction_label(v):
    return "Bassa" if v < 40 else "Media" if v < 70 else "Alta"

def war_escalation(tensions):
    """tensions: dict fronte -> tensione 0-100."""
    if not tensions:
        return None
    vals = sorted(tensions.values(), reverse=True)
    return min(100, vals[0] + 5 * sum(1 for v in vals[1:] if v > 60))

def _band(x, cuts):
    for lim, score in cuts:
        if x < lim:
            return score
    return cuts[-1][1]

def market_stress(vix=None, spx_pct=None, us10y_bp=None, brent_pct=None, dxy_pct=None):
    s = []
    if vix is not None: s.append(_band(vix, [(13, 10), (16, 25), (20, 40), (25, 60), (30, 75), (float("inf"), 90)]))
    if spx_pct is not None: s.append(_band(abs(spx_pct), [(0.5, 10), (1, 30), (2, 55), (3, 75), (float("inf"), 90)]))
    if us10y_bp is not None: s.append(_band(abs(us10y_bp), [(5, 10), (10, 35), (15, 60), (float("inf"), 85)]))
    if brent_pct is not None: s.append(_band(abs(brent_pct), [(1, 10), (3, 35), (5, 60), (float("inf"), 85)]))
    if dxy_pct is not None: s.append(_band(abs(dxy_pct), [(0.3, 10), (0.7, 35), (1.2, 60), (float("inf"), 85)]))
    return round(sum(s) / len(s)) if s else None

def macro_risk(infl_surprises=(), hike_prob_change_pts=0, recession_signal=False):
    """infl_surprises: lista di +1 (sopra attese) / -1 (sotto) per CPI, PPI, PCE, HICP usciti nelle ultime 48 ore."""
    v = 50 + 10 * sum(infl_surprises)
    if hike_prob_change_pts >= 10: v += 10
    elif hike_prob_change_pts <= -10: v -= 10
    if recession_signal: v += 10
    return max(0, min(100, v))

def global_risk(war, stress, macro):
    return round(0.4 * war + 0.3 * stress + 0.3 * macro)

def conviction(nd_market=0, single_source_news=0, conflicting_keys=0):
    return max(20, 100 - 8 * nd_market - 5 * single_source_news - min(30, 10 * conflicting_keys))

def clamp(v):
    return int(max(-100, min(100, round(v))))

def sentiments(spx_pct, fut_pct, nikkei_pct, vix_pct, gold_pct, dxy_dir, us10y_dir, war,
               eur_pct, ecb_tone, fed_tone, brent_pct, oil_supply):
    """dxy_dir/us10y_dir: -1 scende, 0, +1 sale. ecb_tone/fed_tone: +1 più dura, -1 più morbida, 0.
    oil_supply: 'attacchi', 'minacce', 'piu_offerta' oppure None."""
    equity = clamp(20 * spx_pct + 20 * fut_pct + 5 * nikkei_pct)
    riskon = clamp((equity + (-3 * vix_pct)) / 2)
    gold = 25 * gold_pct - 20 * dxy_dir - 15 * us10y_dir + (10 if war >= 75 else 0)
    eurusd = 40 * eur_pct + 15 * ecb_tone - 15 * fed_tone
    oil = 15 * brent_pct + {"attacchi": 40, "minacce": 20, "piu_offerta": -20}.get(oil_supply, 0)
    war_s = clamp((war - 50) * 2)
    glob = clamp((riskon + equity - war_s) / 3)
    return {"global": glob, "riskon": riskon, "equity": equity, "gold": clamp(gold),
            "eurusd": clamp(eurusd), "oil": clamp(oil), "war": war_s}

def brier(p, outcome):
    """p in 0-1, outcome 1 (Confermata) o 0 (Smentita)."""
    return (p - outcome) ** 2

if __name__ == "__main__":
    # Controllo di coerenza con i valori REALI del file oggi.json del 20 ottobre 2026
    # (original/dashboard/data_files/oggi.json, righe gauge e front).
    w = war_escalation({"gulf": 80, "yemen": 78, "ru-ua": 78, "me": 60, "tw": 33})
    s = market_stress(vix=18.44, spx_pct=0.41, us10y_bp=-2.0, brent_pct=0.41, dxy_pct=-0.22)
    g = global_risk(w, s, 50)
    c = conviction(nd_market=7, single_source_news=3, conflicting_keys=2)
    print("escalation", w, "(atteso 90) | stress", s, "(atteso 16) | globale", g, "(atteso 56) | convinzione", c, "(atteso 20)")
    assert (w, s, g, c) == (90, 16, 56, 20)
