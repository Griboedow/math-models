"""Local-only UI. Serves known assets and executes the same Python model as CLI."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import json
from .model import simulate,from_config
from .cli import clean
from .presets import config


def serve(port):
    class Handler(BaseHTTPRequestHandler):
        def send(self,status,body,kind='application/json'):
            raw=body.encode('utf-8');self.send_response(status)
            self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if self.path=='/': self.send(200,(Path(__file__).parent/'ui.html').read_text(encoding='utf-8'),'text/html')
            elif self.path=='/presets':
                configs={f'{ba}/{mo}/{po}':config(ball_name=ba,motion_name=mo,setup_name=po) for ba in ['full','nearly_empty','large'] for mo in ['knitting','crochet','gentle'] for po in ['desk_side','front','far_side','high_table','floor']}
                self.send(200,json.dumps(configs,ensure_ascii=False))
            else:self.send(404,'{"error":"Not found"}')
        def do_POST(self):
            if self.path!='/simulate': return self.send(404,'{"error":"Not found"}')
            origin=self.headers.get('Origin')
            if origin and origin not in [f'http://127.0.0.1:{port}',f'http://localhost:{port}']: return self.send(403,'{"error":"Same-origin only"}')
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=100000:raise ValueError('Invalid request size')
                args=from_config(json.loads(self.rfile.read(n)))
                if args[2].duration_s/args[2].dt_s>100000:raise ValueError('Browser limit: 100000 integration steps; use CLI for longer runs')
                self.send(200,json.dumps(clean(simulate(*args)),ensure_ascii=False,allow_nan=False))
            except (ValueError,TypeError,KeyError) as e:self.send(400,json.dumps({'error':str(e)}))
        def log_message(self,*args): pass
    print(f'Open http://127.0.0.1:{port} — Ctrl+C to stop. CPU, no external services.',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
