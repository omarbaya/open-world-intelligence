#!/usr/bin/env python3
"""Immutable forecasting register; user must provide explicit primary source on resolution."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.forecasts import read_events,append_event,project,VALID
PATH=Path(__file__).resolve().parents[1]/'state'/'forecast_events.jsonl'

def main():
    ap=argparse.ArgumentParser()
    subs=ap.add_subparsers(dest='cmd',required=True)
    new=subs.add_parser('add')
    for k in ('id','claim','date','due','criterion','base-value'): new.add_argument('--'+k,required=True)
    new.add_argument('--probability',type=float,required=True,help='0..1, e.g. 0.65')
    rev=subs.add_parser('revise')
    rev.add_argument('--id',required=True); rev.add_argument('--note',required=True);rev.add_argument('--probability-new',type=float)
    res=subs.add_parser('resolve')
    res.add_argument('--id',required=True);res.add_argument('--status',choices=list(VALID),required=True);res.add_argument('--proof',required=True,help='verifiable official source URL')
    subs.add_parser('list')
    args=ap.parse_args()
    events=read_events(PATH)
    stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
    if args.cmd=='add':
        item={'op':'open','id':args.id,'claim':args.claim,'date':args.date,'due':args.due,'criterion':args.criterion,'base_value':args.base_value,'probability':args.probability}
    elif args.cmd=='revise':
        item={'op':'revise','id':args.id,'note':args.note,'at':stamp,'probability_new':args.probability_new}
    elif args.cmd=='resolve':
        if not args.proof.startswith('https://'): ap.error('proof URL must be HTTPS')
        item={'op':'resolve','id':args.id,'status':args.status,'proof':args.proof,'at':stamp}
    else:
        import json
        print(json.dumps(project(events),ensure_ascii=False,indent=2)); return
    # Validate journal before writing to avoid corrupting immutable history.
    project(events+[item])
    append_event(PATH,item)
    print(f'Registro aggiornato: {args.cmd} {args.id}')
if __name__=='__main__':main()
