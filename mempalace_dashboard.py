#!/usr/bin/env python3
import sqlite3, os, json, http.server
from pathlib import Path

PALACE_PATH = os.path.expanduser("~/.mempalace/palace/chroma.sqlite3")
PORT = 7823


def get_data():
    conn = sqlite3.connect(PALACE_PATH)
    total = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    wings = {
        r[0]: r[1]
        for r in conn.execute("""
            SELECT string_value, COUNT(*) as cnt
            FROM embedding_metadata
            WHERE key='wing' AND string_value IS NOT NULL AND string_value!=''
            GROUP BY string_value ORDER BY cnt DESC
        """)
    }

    rooms_by_wing = {}
    for wing in wings:
        rooms_by_wing[wing] = {
            r[0]: r[1]
            for r in conn.execute("""
                SELECT string_value, COUNT(*) as cnt
                FROM embedding_metadata m1
                WHERE key='room' AND string_value IS NOT NULL AND string_value!=''
                AND EXISTS (SELECT 1 FROM embedding_metadata m2 WHERE m2.id=m1.id AND m2.key='wing' AND m2.string_value=?)
                GROUP BY string_value ORDER BY cnt DESC
            """, (wing,))
        }

    timeline = {
        r[0]: r[1]
        for r in conn.execute("""
            SELECT substr(string_value,1,10) as day, COUNT(*) as cnt
            FROM embedding_metadata
            WHERE key='filed_at' AND string_value IS NOT NULL
            GROUP BY substr(string_value,1,10) ORDER BY day DESC LIMIT 30
        """)
    }

    tag_counts = {}
    for row in conn.execute("""
        SELECT string_value FROM embedding_metadata
        WHERE key='entities' AND string_value IS NOT NULL AND string_value!='' LIMIT 3000
    """):
        for t in row[0].split(';'):
            t = t.strip()
            # Filter out single letters, common noisy words, and overly generic terms
            if t and len(t) > 1 and t not in ['User', 'Tool', 'Account', 'Let', 'Add', 'Big', 'Build', 'Input', 'Output', 'Apple', 'Actually', 'Successfully', 'They', 'You', 'Bases', 'Array', 'Object', 'String', 'Document', 'Version', 'Settings', 'Config']:
                tag_counts[t] = tag_counts.get(t, 0) + 1
    tags = dict(sorted(tag_counts.items(), key=lambda x: -x[1])[:25])

    agents = {
        r[0]: r[1]
        for r in conn.execute("""
            SELECT string_value, COUNT(*) as cnt
            FROM embedding_metadata
            WHERE key='agent' AND string_value IS NOT NULL AND string_value!=''
            GROUP BY string_value ORDER BY cnt DESC LIMIT 15
        """)
    }

    sources = {
        r[0]: r[1]
        for r in conn.execute("""
            SELECT string_value, COUNT(*) as cnt
            FROM embedding_metadata
            WHERE key='source_file' AND string_value IS NOT NULL AND string_value!=''
            GROUP BY string_value ORDER BY cnt DESC LIMIT 15
        """)
    }

    room_samples = {}
    for row in conn.execute("""
        SELECT DISTINCT string_value FROM embedding_metadata
        WHERE key='room' AND string_value IS NOT NULL LIMIT 12
    """):
        doc = conn.execute("""
            SELECT m_doc.string_value
            FROM embedding_metadata m_room
            JOIN embedding_metadata m_doc ON m_room.id=m_doc.id AND m_doc.key='chroma:document'
            WHERE m_room.key='room' AND m_room.string_value=?
            AND m_doc.string_value IS NOT NULL AND m_doc.string_value != '' LIMIT 1
        """, (row[0],)).fetchone()
        if doc:
            content = (doc[0] or '').strip()
            if content.startswith('---'):
                content = content[content.find('---', 3)+3:].strip()
            room_samples[row[0]] = content[:400]

    total_meta = conn.execute("SELECT COUNT(*) FROM embedding_metadata").fetchone()[0]
    conn.close()
    return {
        'total': total, 'total_meta': total_meta,
        'wings': wings, 'rooms_by_wing': rooms_by_wing, 'timeline': timeline,
        'tags': tags, 'agents': agents, 'sources': sources, 'room_samples': room_samples
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            try:
                data = get_data()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.wfile.write(str(e).encode())
        elif self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_response(404)

    def log_message(self, fmt, *args):
        print(f"  {args[0]}")


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MemPalace Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--border:#30363d;--text:#e6edf3;--text2:#8b949e;--accent:#58a6ff;--green:#3fb950;--yellow:#d29922;--red:#f85149;--purple:#a371f7}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh}
.topbar{background:var(--bg2);border-bottom:1px solid var(--border);padding:16px 24px;display:flex;align-items:center;gap:20px;position:sticky;top:0;z-index:100}
.topbar h1{font-size:18px;font-weight:600;color:var(--accent)}
.topbar .subtitle{color:var(--text2);font-size:13px}
.refresh-btn{margin-left:auto;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 14px;border-radius:6px;cursor:pointer;font-size:12px;transition:all .15s}
.refresh-btn:hover{border-color:var(--accent);color:var(--accent)}
.status-dot{width:8px;height:8px;border-radius:50%;background:var(--green);display:inline-block}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:20px}
.grid-full{grid-column:1/-1}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px;overflow:hidden}
.card-header{display:flex;align-items:center;gap:10px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:10px}
.card-header h2{font-size:14px;font-weight:600}
.card-header .count{margin-left:auto;font-size:12px;color:var(--text2);background:var(--bg3);padding:2px 8px;border-radius:10px}
.stats-row{display:flex;gap:12px;padding:0 20px 16px}
.stat-card{flex:1;background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:14px 18px;display:flex;flex-direction:column;gap:4px}
.stat-label{font-size:11px;color:var(--text2);text-transform:uppercase;letter-spacing:.05em}
.stat-value{font-size:28px;font-weight:700;color:var(--accent)}
.stat-sub{font-size:11px;color:var(--text2)}
.room-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px}
.room-chip{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:10px 12px;cursor:pointer;transition:all .15s;text-align:center}
.room-chip:hover{border-color:var(--accent);transform:translateY(-1px)}
.room-chip .room-name{font-size:12px;font-weight:500;color:var(--text);margin-bottom:4px}
.room-chip .room-bar{height:4px;border-radius:2px;background:var(--accent);margin-bottom:4px}
.room-chip .room-count{font-size:11px;color:var(--text2)}
.wing-tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.wing-tab{padding:4px 12px;border-radius:16px;font-size:11px;font-weight:500;border:1px solid var(--border);cursor:pointer;transition:all .15s;color:var(--text2)}
.wing-tab.active{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.tag-cloud{display:flex;flex-wrap:wrap;gap:6px}
.tag{padding:3px 10px;border-radius:12px;font-size:11px;background:var(--bg3);border:1px solid var(--border);color:var(--text2);cursor:default}
.tag.large{font-size:14px;padding:5px 14px;color:var(--accent);border-color:var(--accent)}
.source-list{font-size:12px}
.source-item{display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)}
.source-item:last-child{border-bottom:none}
.source-bar{height:4px;border-radius:2px;background:var(--accent);min-width:4px}
.source-path{color:var(--text);flex:1;font-family:'SF Mono',monospace;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.source-count{color:var(--text2);font-size:11px}
.agent-list{display:flex;flex-direction:column;gap:8px}
.agent-item{display:flex;align-items:center;gap:10px}
.agent-avatar{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0}
.agent-name{font-size:12px;color:var(--text);flex:1}
.agent-count{font-size:11px;color:var(--text2)}
.sample-content{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:12px;font-family:'SF Mono',monospace;font-size:11px;color:var(--text2);line-height:1.5;max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-word}
.sample-content::-webkit-scrollbar{width:4px}.sample-content::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}
.chart-wrap{height:180px}
.room-technical{border-left:3px solid #58a6ff}
.room-general{border-left:3px solid #3fb950}
.room-architecture{border-left:3px solid #a371f7}
.room-planning{border-left:3px solid #d29922}
.room-problems{border-left:3px solid #f85149}
.room-diary{border-left:3px solid #f778ba}
.room-tasknotes{border-left:3px solid #79c0ff}
.room-decisions{border-left:3px solid #56d364}
.room-personal_ai_space{border-left:3px solid #ffa657}
.room-bmo{border-left:3px solid #d2a8ff}
.room-other{border-left:3px solid #8b949e}
.loading{text-align:center;padding:40px;color:var(--text2);font-size:14px}
.loading::after{content:'...';animation:dots 1.2s infinite}
@keyframes dots{0%{content:'.'}33%{content:'..'}66%{content:'...'}}
</style>
</head>
<body>

<div class="topbar">
  <span class="status-dot"></span>
  <h1>MemPalace Dashboard</h1>
  <span class="subtitle">~/.mempalace/palace/</span>
  <button class="refresh-btn" onclick="loadData()">↻ Refresh</button>
</div>

<div class="loading" id="loading">Loading data</div>
<div id="content" style="display:none">

<div class="stats-row">
  <div class="stat-card">
    <span class="stat-label">Total Drawers</span>
    <span class="stat-value" id="stat-total">-</span>
    <span class="stat-sub" id="stat-meta">- metadata rows</span>
  </div>
  <div class="stat-card">
    <span class="stat-label">Wings</span>
    <span class="stat-value" id="stat-wings">-</span>
    <span class="stat-sub">rooms across wings</span>
  </div>
  <div class="stat-card">
    <span class="stat-label">Top Room</span>
    <span class="stat-value" id="stat-toproom" style="font-size:18px">-</span>
    <span class="stat-sub" id="stat-toproomcnt">- drawers</span>
  </div>
  <div class="stat-card">
    <span class="stat-label">Files Mined</span>
    <span class="stat-value" id="stat-files">-</span>
    <span class="stat-sub">source files</span>
  </div>
</div>

<div class="grid">
  <div class="card grid-full">
    <div class="card-header">
      <h2>Rooms by Wing</h2>
      <span class="count" id="wing-count">-</span>
    </div>
    <div class="wing-tabs" id="wing-tabs"></div>
    <div class="room-grid" id="room-grid"></div>
  </div>

  <div class="card">
    <div class="card-header"><h2>Filing Activity</h2></div>
    <div class="chart-wrap"><canvas id="timeline-chart"></canvas></div>
  </div>

  <div class="card">
    <div class="card-header"><h2>Top Tags</h2><span class="count" id="tag-count">-</span></div>
    <div class="tag-cloud" id="tag-cloud"></div>
  </div>

  <div class="card">
    <div class="card-header">
      <h2>Room Preview</h2>
      <select id="room-select" style="margin-left:auto;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:6px;font-size:12px"></select>
    </div>
    <div class="sample-content" id="sample-content">Click a room to preview...</div>
  </div>

  <div class="card">
    <div class="card-header"><h2>Active Agents</h2><span class="count" id="agent-count">-</span></div>
    <div class="agent-list" id="agent-list"></div>
  </div>

  <div class="card">
    <div class="card-header"><h2>Top Source Files</h2><span class="count" id="source-count">-</span></div>
    <div class="source-list" id="source-list"></div>
  </div>
</div>
</div>

<script>
const COLORS=['#58a6ff','#3fb950','#a371f7','#d29922','#f85149','#ffa657','#79c0ff','#f778ba','#56d364','#d2a8ff'];
let currentWing=null, currentData=null, timelineChart=null;

async function loadData(){
  document.getElementById('loading').style.display='block';
  document.getElementById('content').style.display='none';
  try{
    currentData=await fetch('/api/data').then(r=>r.json());
    renderAll(currentData);
  }catch(e){alert('Failed: '+e);}
}

function renderAll(d){
  document.getElementById('loading').style.display='none';
  document.getElementById('content').style.display='block';

  document.getElementById('stat-total').textContent=d.total.toLocaleString();
  document.getElementById('stat-meta').textContent=(d.total_meta||0).toLocaleString()+' metadata rows';
  document.getElementById('stat-wings').textContent=Object.keys(d.wings).length;
  document.getElementById('stat-files').textContent=Object.keys(d.sources||{}).length;
  const wk=Object.keys(d.wings)[0];
  const topR=Object.entries(d.rooms_by_wing[wk]||{}).sort((a,b)=>b[1]-a[1])[0];
  document.getElementById('stat-toproom').textContent=topR?topR[0].replace(/_/g,' '):'-';
  document.getElementById('stat-toproomcnt').textContent=topR?topR[1]+' drawers':'';

  const tabsEl=document.getElementById('wing-tabs');
  tabsEl.innerHTML=Object.keys(d.wings).map((w,i)=>`<div class="wing-tab ${i===0?'active':''}" data-wing="${w}">${w.replace('wing_','').replace(/_/g,' ')} (${d.wings[w]})</div>`).join('');
  tabsEl.querySelectorAll('.wing-tab').forEach(t=>t.addEventListener('click',()=>{
    tabsEl.querySelectorAll('.wing-tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    currentWing=t.dataset.wing;
    renderRooms(d);
  }));
  currentWing=Object.keys(d.wings)[0];
  renderRooms(d);
  renderTimeline(d);
  renderTags(d);
  renderAgents(d);
  renderSources(d);
  renderRoomSelect(d);
}

function renderRooms(d){
  const rooms=d.rooms_by_wing[currentWing]||{};
  const sorted=Object.entries(rooms).sort((a,b)=>b[1]-a[1]);
  const max=Math.max(...sorted.map(r=>r[1]),1);
  document.getElementById('wing-count').textContent=Object.values(rooms).reduce((a,b)=>a+b,0)+' total';
  document.getElementById('room-grid').innerHTML=sorted.map(([name,count])=>{
    const pct=Math.round((count/max)*100);
    const cls='room-'+(['technical','general','architecture','planning','problems','diary','tasknotes','decisions','personal_ai_space','bmo'].includes(name)?name:'other');
    return `<div class="room-chip ${cls}" onclick="showSample('${name}')">
      <div class="room-name">${name.replace(/_/g,' ')}</div>
      <div class="room-bar" style="width:${pct}%"></div>
      <div class="room-count">${count}</div>
    </div>`;
  }).join('');
}

function renderTimeline(d){
  const sorted=Object.entries(d.timeline).sort((a,b)=>a[0].localeCompare(b[0]));
  const ctx=document.getElementById('timeline-chart').getContext('2d');
  if(timelineChart)timelineChart.destroy();
  timelineChart=new Chart(ctx,{
    type:'bar',
    data:{labels:sorted.map(r=>r[0]),datasets:[{label:'Drawers filed',data:sorted.map(r=>r[1]),backgroundColor:'#58a6ff',borderRadius:4,borderSkipped:false}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'#21262d'},ticks:{color:'#8b949e',font:{size:10}}},y:{grid:{color:'#21262d'},ticks:{color:'#8b949e',font:{size:10}},beginAtZero:true}}}
  });
}

function renderTags(d){
  const tags=Object.entries(d.tags).sort((a,b)=>b[1]-a[1]).slice(0,25);
  document.getElementById('tag-count').textContent=tags.length;
  const max=Math.max(...tags.map(t=>t[1]),1);
  document.getElementById('tag-cloud').innerHTML=tags.map(([tag,count])=>`<span class="tag ${count>=max*0.5?'large':''}" style="font-size:${8+((count/max)*6)}px">${tag} <small style="opacity:.6">×${count}</small></span>`).join('');
}

function renderAgents(d){
  const agents=Object.entries(d.agents||{}).sort((a,b)=>b[1]-a[1]).slice(0,10);
  document.getElementById('agent-count').textContent=agents.length;
  document.getElementById('agent-list').innerHTML=agents.map(([name,count],i)=>{
    const c=COLORS[i%COLORS.length];
    return `<div class="agent-item"><div class="agent-avatar" style="background:${c}22;color:${c}">${name.split(' ').map(p=>p[0]).join('').slice(0,2).toUpperCase()}</div><span class="agent-name">${name}</span><span class="agent-count">${count} events</span></div>`;
  }).join('');
}

function renderSources(d){
  const sources=Object.entries(d.sources||{}).sort((a,b)=>b[1]-a[1]).slice(0,10);
  const max=Math.max(...sources.map(s=>s[1]),1);
  document.getElementById('source-count').textContent=sources.length;
  document.getElementById('source-list').innerHTML=sources.map(([path,count])=>{
    const pct=Math.round((count/max)*100);
    return `<div class="source-item"><div class="source-bar" style="width:${pct}%"></div><span class="source-path" title="${path}">${path.split('/').pop()}</span><span class="source-count">${count}×</span></div>`;
  }).join('');
}

function renderRoomSelect(d){
  const sel=document.getElementById('room-select');
  const all=[...new Set(Object.values(d.rooms_by_wing).flatMap(r=>Object.keys(r)))].sort();
  sel.innerHTML=all.map(r=>`<option value="${r}">${r.replace(/_/g,' ')}</option>`).join('');
  sel.addEventListener('change',()=>showSample(sel.value));
}

function showSample(room){
  document.getElementById('sample-content').textContent=(currentData.room_samples||{})[room]||'No content found for this room.';
}

loadData();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print(f"Starting MemPalace Dashboard → http://localhost:{PORT}")
    http.server.HTTPServer(("", PORT), Handler).serve_forever()