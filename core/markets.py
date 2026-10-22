"""Agent 2: retrieve free delayed, dated macro series; never label as live quotes."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
from urllib.parse import quote
from .sources import fetch_bytes
import csv
import io


def parse_fred_csv(payload, series: str):
    lines = csv.DictReader(io.StringIO(payload.decode("utf-8-sig",errors="replace")))
    if not lines.fieldnames or series not in lines.fieldnames:
        raise ValueError(f"Series {series} missing from FRED CSV")
    last = []
    for row in lines:
        try:
            dt = date.fromisoformat(row.get("observation_date", row.get("DATE", "")))
            val = float(row[series])
            last.append((dt, val))
        except (ValueError, TypeError):
            continue
    if not last:
        raise ValueError(f"No values in {series}")
    last.sort(key=lambda x:x[0])
    today = date.today()
    available = [i for i in last if i[0] <= today]
    if not available:
        raise ValueError(f"Only future values in {series}")
    return available[-2:]


def collect_markets(config, fetcher=fetch_bytes, now=None):
    now = now or datetime.now(timezone.utc)
    result = []
    def task(item):
        copy = {k:item[k] for k in ("id","name","unit","source","type")}
        copy.update({"value":None,"previous":None,"change":None,"change_pct":None,"observation_date":None,"previous_date":None,"stale":True,"delayed":True,"error":None})
        series = item.get("series")
        if not series:
            copy["error"] = "Nessuna fonte gratuita verificata configurata"
            return copy
        try:
            values = parse_fred_csv(fetcher("https://fred.stlouisfed.org/graph/fredgraph.csv?id="+quote(series)),series)
            dt,val = values[-1]
            copy["value"] = val
            copy["observation_date"] = dt.isoformat()
            copy["stale"] = (now.date()-dt).days > 5
            copy["url"] = "https://fred.stlouisfed.org/series/" + quote(series)
            if len(values)>1:
                prev_dt,prev = values[0]
                copy["previous"],copy["previous_date"] = prev,prev_dt.isoformat()
                copy["change"] = round(val-prev,6)
                if prev: copy["change_pct"] = round(100*(val-prev)/abs(prev),4)
        except Exception as exc:
            copy["error"] = str(exc)[:160]
        return copy
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(task,item) for item in config]
        for future in as_completed(jobs): result.append(future.result())
    lookup={v["id"]:v for v in result}
    return [lookup[item["id"]] for item in config]
