import concurrent.futures as cf
import json,zipfile
from download import get
from config import RAW, records, targets

def run(p):
    d=json.loads(p.read_text())['data']; u=(d.get('realtime_replay') or {}).get('download_url')
    if not u:return
    folder=p.parent
    dest=folder/'legacy.zip'
    if not dest.exists():dest.write_bytes(get(u).content)
    with zipfile.ZipFile(dest) as z:
        for name in ['replay/manifest.json','result.json','events.jsonl','configs/robot_info.txt']:
            if name in z.namelist():(folder/('legacy_'+name.split('/')[-1])).write_bytes(z.read(name))
        frames=[];bucket=-1
        for name in sorted(n for n in z.namelist() if n.startswith('replay/chunks/') and n.endswith('.jsonl')):
            for line in z.read(name).splitlines():
                f=json.loads(line);b=int(f['time']*2)
                if b==bucket:continue
                bucket=b
                for r in f['robots']:
                    for k in list(r):
                        if k not in ['name','side','playerNumber','basePosition','upDot']:del r[k]
                frames.append({k:f[k] for k in ['time','ball','robots','commandIntents'] if k in f})
        (folder/'legacy_samples.json').write_text(json.dumps(frames,separators=(',',':')))
    print(folder.name,'legacy frames',len(frames),flush=True)

if __name__=='__main__':
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(run,[RAW/r['id']/'detail.json' for r in targets(records())]))
