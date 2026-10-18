"""Run independent snag cases in separate Python processes, then merge reports.

This changes only scheduling: each worker uses the same MeshScene/audit API.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import argparse,json,os,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from yarnstand.cli import save
from yarnstand.snags import write_report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path);parser.add_argument('cases',type=Path)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.workers<=8:parser.error('workers must be between 1 and 8')
    spec=json.loads(args.cases.read_text(encoding='utf-8-sig'));workers=min(args.workers,len(spec['cases']))
    if workers<1:parser.error('at least one case required')
    processes=[]
    with tempfile.TemporaryDirectory(prefix='yarnstand-snag-') as temporary:
        directory=Path(temporary).resolve()
        assert directory.is_relative_to(Path(tempfile.gettempdir()).resolve())
        try:
            for i in range(workers):
                batch=deepcopy(spec);batch['cases']=spec['cases'][i::workers];save(directory/f'cases_{i}.json',batch)
                command=[sys.executable,'-m','yarnstand','snag-audit',str(args.manifest.resolve()),str(directory/f'cases_{i}.json'),'--out',str(directory/f'report_{i}')]
                processes.append(subprocess.Popen(command,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0))
            failures=[p.wait() for p in processes]
            if any(failures):raise RuntimeError(f'Worker failures: {failures}')
            reports=[json.loads((directory/f'report_{i}/audit.json').read_text(encoding='utf-8')) for i in range(workers)]
            result=reports[0]
            for report in reports[1:]:
                for key in ('schema_version','source_sha256','runtime','provenance','allowances_m','sampling_step_m','motion_step_m'):
                    if report[key]!=result[key]:raise ValueError(f'Workers disagree on {key}')
            by_id={case['id']:case for report in reports for case in report['cases']}
            if len(by_id)!=len(spec['cases']):raise ValueError('Missing or duplicate cases')
            result['cases']=[by_id[c['id']] for c in spec['cases']];result['inputs']=spec
            result['summary']={'cases':len(by_id),'case_statuses':dict(Counter(c['status'] for c in result['cases'])),
                'part_statuses':dict(Counter(p['status'] for c in result['cases'] for p in c['parts'])),
                'distance_samples':sum(r['summary']['distance_samples'] for r in reports)}
            result['execution']={'independent_worker_processes':workers}
            write_report(args.out,result);print(json.dumps(result['summary']),flush=True)
        finally:
            for process in processes:
                if process.poll() is None:
                    if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
                    else:process.terminate()
            for process in processes:process.wait()

if __name__=='__main__':main()
