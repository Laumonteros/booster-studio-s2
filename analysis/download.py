import concurrent.futures as cf
import gzip
import json
import time
from urllib.parse import urljoin
import requests
from config import RAW, records, targets

def get(url):
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2: raise
            time.sleep(1)

def segment(args):
    url, path = args
    if not path.exists():
        frames = []
        bucket = -1
        for line in gzip.decompress(get(url).content).splitlines():
            try:
                f = json.loads(line)
            except json.JSONDecodeError:
                with (RAW / 'malformed_frames.log').open('a') as log:
                    log.write(str(path.relative_to(RAW)) + ' malformed JSON line skipped\n')
                continue
            b = int(f['time'] * 2)
            if b == bucket: continue
            bucket = b
            frames.append({k:f[k] for k in ['time','ball','commandIntents','robots'] if k in f})
            for robot in frames[-1]['robots']:
                for k in list(robot):
                    if k not in ['name','side','playerNumber','basePosition','upDot']: del robot[k]
        path.write_text(json.dumps(frames, separators=(',',':')))
    return str(path)

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    status=[]
    jobs=[]
    for r in targets(records()):
        mid=r['id']; folder=RAW/mid;folder.mkdir(exist_ok=True)
        try:
            p=folder/'detail.json'
            if not p.exists(): p.write_text(json.dumps(get('https://api.booster.tech/api/v1/competition/matches/'+mid).json()))
            d=json.loads(p.read_text())['data']
            u=(d.get('realtime_replay') or {}).get('manifest_url')
            alternatives=[]
            def walk(v,key=''):
                if isinstance(v,dict):
                    for k,x in v.items(): walk(x,key+'.'+k)
                elif isinstance(v,str) and ('replay' in key.lower() or 'manifest' in key.lower()) and v.startswith('http'): alternatives.append((key,v))
            walk(d)
            if not u:
                u=next((v for k,v in alternatives if '.json' in v),None)
            if not u:
                status.append(dict(id=mid,status='legacy ZIP available' if (d.get('realtime_replay') or {}).get('download_url') else 'replay unavailable',alternatives=alternatives))
                print(mid,status[-1]['status'],flush=True)
                continue
            p=folder/'manifest.json'
            if not p.exists():p.write_text(get(u).text)
            m=json.loads(p.read_text())
            for s in m['segments']: jobs.append((urljoin(u,s['path']),folder/('sample_'+str(s['index'])+'.json')))
            status.append(dict(id=mid,status='manifest available',segments=len(m['segments']),url=u))
        except Exception as e:status.append(dict(id=mid,status='error',error=str(e)))
        print(mid,status[-1]['status'],flush=True)
    (RAW/'replay_status.json').write_text(json.dumps(status,indent=2))
    print('segments',len(jobs),flush=True)
    errors=[]
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        fs={pool.submit(segment,j):j for j in jobs}
        for n,f in enumerate(cf.as_completed(fs),1):
            try:f.result()
            except Exception as e:errors.append((str(fs[f][1]),str(e)))
            if n%100==0:print('segments complete',n,'/',len(jobs),flush=True)
    (RAW/'download_errors.json').write_text(json.dumps(errors,indent=2))
    print('DONE errors',len(errors),flush=True)
    if errors or any(s['status']=='error' for s in status):
        raise RuntimeError('Replay fetch failed; inspect data/raw download status/errors')

if __name__=='__main__':main()
