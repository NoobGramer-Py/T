"""
Report generator for T's autonomous engine.
Produces a clean HTML report from working memory at task completion.
"""

import time
from pathlib import Path
from .memory import WorkingMemory

REPORT_DIR = Path.home() / ".local" / "share" / "t-assistant" / "auto_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SEV_COLOR = {"critical": "#ff1a1a", "high": "#ff6600",
             "medium": "#ffb300", "low": "#00cc66", "info": "#00d4ff"}


def generate(mem: WorkingMemory, summary: str) -> str:
    """Generate HTML report from working memory. Returns file path."""

    date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mem.start_ts))
    dur_s    = int(time.time() - mem.start_ts)
    dur_str  = f"{dur_s // 60}m {dur_s % 60}s"

    # ── Steps table ───────────────────────────────────────────────────────────
    step_rows = ""
    for s in mem.steps:
        ts   = time.strftime("%H:%M:%S", time.localtime(s["ts"]))
        stat = s["status"].upper()
        col  = "#00ff88" if stat == "DONE" else "#ff4400" if stat == "ERROR" else "#ffb300"
        step_rows += f"""
        <tr>
          <td>{ts}</td>
          <td style="color:{col}">{stat}</td>
          <td>{s['name']}</td>
          <td style="font-family:monospace;font-size:9px">{s['tool']}</td>
          <td>{s['summary'][:200]}</td>
        </tr>"""

    # ── Findings ──────────────────────────────────────────────────────────────
    finding_blocks = ""
    for f in mem.findings[:50]:
        col = SEV_COLOR.get(f.severity, "#888")
        finding_blocks += f"""
        <div style="background:rgba(0,212,255,0.02);border:1px solid rgba(0,212,255,0.09);
                    border-left:3px solid {col};border-radius:3px;padding:10px 14px;margin-bottom:8px">
          <div style="display:flex;gap:10px;align-items:center;margin-bottom:6px">
            <span style="background:{col};color:#000;padding:1px 7px;border-radius:2px;
                         font-size:7px;letter-spacing:2px;font-weight:700">{f.severity.upper()}</span>
            <strong style="color:#a0f4ff">{f.key.replace('_',' ').upper()}</strong>
            <span style="color:rgba(0,212,255,0.4);font-size:9px">{f.step}</span>
          </div>
          <div style="font-size:10px;color:rgba(0,212,255,0.7);font-family:monospace;word-break:break-all">
            {str(f.value)[:300]}
          </div>
        </div>"""

    # ── Creds table ───────────────────────────────────────────────────────────
    cred_rows = ""
    for c in mem.creds[:30]:
        raw = c.get("raw", str(c))
        cred_rows += f"<tr><td style='font-family:monospace;color:#ff6600'>{raw[:200]}</td></tr>"

    # ── Social accounts ───────────────────────────────────────────────────────
    social_rows = ""
    for s in mem.social_accounts[:30]:
        platform = s.get("platform", str(s))
        social_rows += f"<tr><td style='color:#00d4ff'>{platform}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>T — Autonomous Task Report</title>
<style>
  :root {{ --j:#00d4ff; --bg:#000a15; --card:#040f1e; --border:rgba(0,212,255,0.12); --text:rgba(0,212,255,0.85); }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Courier New',monospace; padding:36px; }}
  h1 {{ font-size:24px; color:var(--j); letter-spacing:4px; margin-bottom:4px; text-shadow:0 0 20px var(--j); }}
  h2 {{ font-size:11px; letter-spacing:6px; color:rgba(0,212,255,0.4); margin:28px 0 14px;
        border-bottom:1px solid var(--border); padding-bottom:8px; }}
  .meta {{ font-size:10px; color:rgba(0,212,255,0.4); margin-bottom:24px; }}
  .summary {{ background:rgba(0,212,255,0.03); border:1px solid var(--border); border-radius:4px;
              padding:16px; font-size:11px; line-height:1.7; margin-bottom:24px;
              color:rgba(0,212,255,0.8); white-space:pre-wrap; }}
  .stats {{ display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:24px; }}
  .stat {{ background:var(--card); border:1px solid var(--border); border-radius:4px;
           padding:12px; text-align:center; }}
  .stat-num {{ font-size:22px; font-weight:700; }}
  .stat-label {{ font-size:7px; letter-spacing:3px; color:rgba(0,212,255,0.4); margin-top:3px; }}
  table {{ width:100%; border-collapse:collapse; font-size:10px; margin-bottom:20px; }}
  th {{ background:rgba(0,212,255,0.05); padding:7px 10px; text-align:left;
        font-size:7px; letter-spacing:3px; color:rgba(0,212,255,0.45);
        border-bottom:1px solid var(--border); }}
  td {{ padding:6px 10px; border-bottom:1px solid rgba(0,212,255,0.04); vertical-align:top; }}
  .flag {{ color:#00ff88; font-family:monospace; font-weight:700; font-size:13px; }}
  .watermark {{ text-align:center; margin-top:50px; font-size:7px;
                letter-spacing:6px; color:rgba(0,212,255,0.1); }}
</style>
</head>
<body>
<h1>T — AUTONOMOUS TASK REPORT</h1>
<div class="meta">
  Date: {date_str} &nbsp;|&nbsp; Duration: {dur_str} &nbsp;|&nbsp;
  Target: {mem.target} &nbsp;|&nbsp; Type: {mem.task_type.upper()} &nbsp;|&nbsp;
  Steps: {len(mem.steps)}
</div>

<h2>SUMMARY</h2>
<div class="summary">{summary}</div>

<h2>KEY METRICS</h2>
<div class="stats">
  <div class="stat"><div class="stat-num" style="color:#00d4ff">{len(mem.hosts)}</div><div class="stat-label">HOSTS</div></div>
  <div class="stat"><div class="stat-num" style="color:#a0f4ff">{len(mem.subdomains)}</div><div class="stat-label">SUBDOMAINS</div></div>
  <div class="stat"><div class="stat-num" style="color:#ff6600">{len(mem.vulns)}</div><div class="stat-label">VULNS</div></div>
  <div class="stat"><div class="stat-num" style="color:#ff3300">{len(mem.creds)}</div><div class="stat-label">CREDS</div></div>
  <div class="stat"><div class="stat-num" style="color:#00ff88">{len(mem.flags)}</div><div class="stat-label">FLAGS</div></div>
  <div class="stat"><div class="stat-num" style="color:#cc88ff">{len(mem.social_accounts)}</div><div class="stat-label">SOCIAL</div></div>
</div>

{f'''<h2>FLAGS CAPTURED</h2>
<div style="margin-bottom:20px">
{''.join(f'<div class="flag">▶ {fl}</div>' for fl in mem.flags)}
</div>''' if mem.flags else ''}

<h2>FINDINGS ({len(mem.findings)})</h2>
{finding_blocks or '<p style="font-size:10px;color:rgba(0,212,255,0.3)">No findings recorded.</p>'}

{f'''<h2>CREDENTIALS ({len(mem.creds)})</h2>
<table><tr><th>CREDENTIAL</th></tr>{cred_rows}</table>''' if mem.creds else ''}

{f'''<h2>SOCIAL ACCOUNTS ({len(mem.social_accounts)})</h2>
<table><tr><th>PLATFORM</th></tr>{social_rows}</table>''' if mem.social_accounts else ''}

<h2>EXECUTION TIMELINE ({len(mem.steps)} steps)</h2>
<table>
  <tr><th>TIME</th><th>STATUS</th><th>STEP</th><th>TOOL</th><th>SUMMARY</th></tr>
  {step_rows or '<tr><td colspan="5" style="color:rgba(0,212,255,0.3)">No steps recorded</td></tr>'}
</table>

<div class="watermark">GENERATED BY T · AUTONOMOUS ENGINE · AUTHORIZED USE ONLY</div>
</body>
</html>"""

    ts   = int(mem.start_ts)
    path = REPORT_DIR / f"auto_{mem.task_type}_{ts}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)
