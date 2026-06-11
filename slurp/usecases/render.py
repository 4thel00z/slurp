"""Live HTML view of the generated QA dataset.

Serves a small Tailwind page that polls a JSON endpoint, so the dataset updates
in the browser as the worker persists new QA pairs. Read-only and dependency-free
(stdlib ``http.server`` + ``sqlite3``).
"""

import json
import logging
import sqlite3
import sys
import webbrowser
from dataclasses import dataclass
from dataclasses import field
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer

from slurp.domain.config import SQLiteConfig


logger = logging.getLogger(__name__)


def load_generations(database: str) -> list[dict]:
    """Read the generations table into view dicts. Empty if the table is absent."""
    con = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        try:
            rows = con.execute(
                'SELECT id, question_answers, "references", language FROM generations'
            ).fetchall()
        except sqlite3.OperationalError:
            return []  # worker hasn't created the table yet
    finally:
        con.close()

    out: list[dict] = []
    for gid, qa_raw, refs_raw, lang in rows:
        qa = json.loads(qa_raw) if qa_raw else {}
        refs = json.loads(refs_raw) if refs_raw else []
        ref = refs[0] if isinstance(refs, list) and refs else {}
        out.append(
            {
                "id": gid,
                "language": lang,
                "qa": qa,
                "title": ref.get("title", ""),
                "url": ref.get("url", ""),
                "source": (ref.get("content", "") or "")[:2000],
            }
        )
    return out


PAGE = r"""<!DOCTYPE html>
<html lang="de" class="scroll-smooth">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Slurp · QA Dataset</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{font-family:'Inter',system-ui,sans-serif}
  .mono{font-family:'JetBrains Mono',monospace}
  .prose-answer{line-height:1.7}
  details[open] .chev{transform:rotate(90deg)}
</style>
</head>
<body class="bg-slate-50 text-slate-800 antialiased">
  <header class="sticky top-0 z-10 backdrop-blur bg-white/80 border-b border-slate-200">
    <div class="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500 to-sky-400 grid place-items-center text-white font-extrabold">🌊</div>
        <div>
          <h1 class="font-extrabold text-slate-900 leading-tight">Slurp · QA Dataset</h1>
          <p class="text-xs text-slate-500">live view · <span id="status" class="text-emerald-600 font-semibold">●</span> <span id="updated"></span></p>
        </div>
      </div>
      <div class="flex gap-2 text-sm">
        <span class="px-3 py-1 rounded-full bg-indigo-50 text-indigo-700 font-semibold" id="docCount">…</span>
        <span class="px-3 py-1 rounded-full bg-sky-50 text-sky-700 font-semibold" id="qaCount">…</span>
      </div>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-6 py-8 space-y-6" id="docs"></main>
  <p id="empty" class="max-w-5xl mx-auto px-6 text-center text-slate-400 hidden">No QA pairs yet — waiting for the worker…</p>

  <footer class="max-w-5xl mx-auto px-6 py-10 text-center text-xs text-slate-400">
    Slurp · local connector + OpenAI-compatible LLM · auto-refreshing every 3s
  </footer>

<script>
const esc = s => (s??'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const root = document.getElementById('docs');
let lastKey = '';

function renderDoc(d){
  const pairs = Object.entries(d.qa);
  const qaHtml = pairs.map(([q,a],j)=>`
    <div class="border-t border-slate-100 pt-4 mt-4 first:border-0 first:pt-0 first:mt-0">
      <div class="flex gap-3">
        <span class="shrink-0 h-6 w-6 grid place-items-center rounded-lg bg-indigo-100 text-indigo-700 text-xs font-bold">Q${j+1}</span>
        <p class="font-semibold text-slate-900">${esc(q)}</p>
      </div>
      <div class="flex gap-3 mt-2">
        <span class="shrink-0 h-6 w-6 grid place-items-center rounded-lg bg-emerald-100 text-emerald-700 text-xs font-bold">A</span>
        <p class="prose-answer text-slate-600 text-[15px]">${esc(a)}</p>
      </div>
    </div>`).join('');
  return `
    <section class="bg-white rounded-2xl shadow-sm ring-1 ring-slate-200 overflow-hidden">
      <div class="px-6 py-4 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100 flex items-start justify-between gap-4">
        <div class="min-w-0">
          <h2 class="font-bold text-slate-900 truncate">${esc(d.title)||'(untitled)'}</h2>
          <p class="mono text-[11px] text-slate-400 truncate">${esc(d.url)}</p>
        </div>
        <div class="flex shrink-0 gap-2">
          <span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-xs font-semibold uppercase">${esc(d.language)}</span>
          <span class="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-600 text-xs font-semibold">${pairs.length} QA</span>
        </div>
      </div>
      <div class="px-6 py-5">${qaHtml}</div>
      <details class="px-6 pb-5">
        <summary class="cursor-pointer text-xs font-semibold text-slate-400 hover:text-slate-600 flex items-center gap-1 select-none">
          <span class="chev transition-transform">▸</span> Source excerpt
        </summary>
        <pre class="mono text-[11px] text-slate-500 bg-slate-50 rounded-xl p-4 mt-2 whitespace-pre-wrap max-h-72 overflow-auto">${esc(d.source)}</pre>
      </details>
    </section>`;
}

async function tick(){
  try{
    const data = await (await fetch('/api/generations')).json();
    document.getElementById('status').className = 'text-emerald-600 font-semibold';
    document.getElementById('updated').textContent = 'updated ' + new Date().toLocaleTimeString();
    const key = JSON.stringify(data.map(d=>d.id));
    document.getElementById('docCount').textContent = data.length + ' documents';
    document.getElementById('qaCount').textContent = data.reduce((n,d)=>n+Object.keys(d.qa).length,0) + ' QA pairs';
    document.getElementById('empty').classList.toggle('hidden', data.length>0);
    if(key !== lastKey){ lastKey = key; root.innerHTML = data.map(renderDoc).join(''); }
  }catch(e){
    document.getElementById('status').className = 'text-rose-500 font-semibold';
  }
}
tick();
setInterval(tick, 3000);
</script>
</body>
</html>"""


def build_page() -> str:
    """Return the static page shell that polls ``/api/generations``."""
    return PAGE


def _make_handler(database: str):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # quiet by default
            pass

        def _send(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/api/generations"):
                body = json.dumps(load_generations(database), ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
            elif self.path in ("/", "/index.html"):
                self._send(200, build_page().encode("utf-8"), "text/html; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")

    return Handler


@dataclass
class RenderUsecase:
    config: SQLiteConfig = field(init=False)
    host: str = "127.0.0.1"
    port: int = 8077
    open_browser: bool = False

    def __post_init__(self):
        self.config = SQLiteConfig.from_default(sys.argv)

    def run(self) -> None:
        server = ThreadingHTTPServer((self.host, self.port), _make_handler(self.config.database))
        url = f"http://{self.host}:{self.port}/"
        print(f"Serving live QA view from {self.config.database} at {url}")
        print("Press Ctrl+C to stop.")
        if self.open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping render server.")
        finally:
            server.server_close()
