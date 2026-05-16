"""
Pentest report generator for T's red team lab.
Produces a professional HTML report from the session log.
"""

import os
import time
from pathlib import Path
from .session_log import LabSession

REPORT_DIR = Path(os.path.expanduser("~/.local/share/t-assistant/reports"))
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SEVERITY_COLOR = {
    "critical": "#ff1a1a",
    "high":     "#ff6600",
    "medium":   "#ffb300",
    "low":      "#00cc66",
    "info":     "#00d4ff",
}


def generate_html(session: LabSession) -> str:
    """Generate a full HTML pentest report from session data."""
    date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(session.start_ts))
    dur_str  = session.duration_str()

    critical = sum(1 for f in session.findings if f["severity"] == "critical")
    high     = sum(1 for f in session.findings if f["severity"] == "high")
    medium   = sum(1 for f in session.findings if f["severity"] == "medium")
    low      = sum(1 for f in session.findings if f["severity"] in ("low", "info"))

    # ── Device table ──────────────────────────────────────────────────────────
    device_rows = ""
    for d in session.devices:
        ports = ", ".join(str(p) for p in d.get("open_ports", []))
        device_rows += f"""
        <tr>
          <td>{d['ip']}</td>
          <td>{d.get('hostname','—')}</td>
          <td>{d.get('device_type','unknown').upper()}</td>
          <td>{d.get('os_hint','—')}</td>
          <td class="mono">{ports or '—'}</td>
        </tr>"""

    # ── Findings ──────────────────────────────────────────────────────────────
    finding_cards = ""
    for f in sorted(session.findings, key=lambda x: ["critical","high","medium","low","info"].index(x["severity"])):
        color = SEVERITY_COLOR.get(f["severity"], "#888")
        finding_cards += f"""
        <div class="finding">
          <div class="finding-header" style="border-left:4px solid {color}">
            <span class="badge" style="background:{color}">{f['severity'].upper()}</span>
            <strong>{f['title']}</strong>
            <span class="device-tag">{f['device']}</span>
          </div>
          <p>{f['description']}</p>
          {f'<div class="remediation"><strong>Remediation:</strong> {f["remediation"]}</div>' if f.get("remediation") else ''}
        </div>"""

    # ── Credentials ───────────────────────────────────────────────────────────
    cred_rows = ""
    for c in session.creds:
        ts = time.strftime("%H:%M:%S", time.localtime(c["ts"]))
        cred_rows += f"""
        <tr>
          <td>{ts}</td>
          <td>{c['source']}</td>
          <td class="mono">{c['username']}</td>
          <td class="mono" style="color:#ff6600">{c['password']}</td>
          <td>{c.get('extra','')}</td>
        </tr>"""

    # ── Timeline ──────────────────────────────────────────────────────────────
    timeline_rows = ""
    for entry in session.log:
        ts    = time.strftime("%H:%M:%S", time.localtime(entry.ts))
        color = SEVERITY_COLOR.get(entry.severity, "#888")
        timeline_rows += f"""
        <tr>
          <td>{ts}</td>
          <td style="color:{color}">{entry.severity.upper()}</td>
          <td>{entry.step}</td>
          <td>{entry.action}</td>
          <td>{entry.result}</td>
        </tr>"""

    # ── Data accessed ─────────────────────────────────────────────────────────
    data_rows = ""
    for d in session.data_accessed:
        ts = time.strftime("%H:%M:%S", time.localtime(d["ts"]))
        data_rows += f"<tr><td>{ts}</td><td>{d['device']}</td><td>{d['data_type']}</td><td>{d['size']}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>T — Penetration Test Report</title>
<style>
  :root {{
    --j:#00d4ff; --bg:#000a15; --card:#040f1e;
    --border:rgba(0,212,255,0.12); --text:rgba(0,212,255,0.85);
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Courier New',monospace; padding:40px; }}
  h1 {{ font-size:28px; color:var(--j); letter-spacing:4px; margin-bottom:4px; text-shadow:0 0 20px var(--j); }}
  h2 {{ font-size:13px; letter-spacing:6px; color:rgba(0,212,255,0.45); margin:32px 0 16px; border-bottom:1px solid var(--border); padding-bottom:8px; }}
  h3 {{ font-size:11px; letter-spacing:4px; color:rgba(0,212,255,0.6); margin-bottom:12px; }}
  .meta {{ font-size:11px; color:rgba(0,212,255,0.4); margin-bottom:32px; }}
  .summary-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:32px; }}
  .stat {{ background:var(--card); border:1px solid var(--border); border-radius:4px; padding:16px; text-align:center; }}
  .stat-num {{ font-size:28px; font-weight:bold; }}
  .stat-label {{ font-size:8px; letter-spacing:4px; color:rgba(0,212,255,0.4); margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; font-size:10px; margin-bottom:24px; }}
  th {{ background:rgba(0,212,255,0.05); padding:8px 12px; text-align:left; font-size:8px; letter-spacing:3px; color:rgba(0,212,255,0.45); border-bottom:1px solid var(--border); }}
  td {{ padding:7px 12px; border-bottom:1px solid rgba(0,212,255,0.04); vertical-align:top; }}
  tr:hover td {{ background:rgba(0,212,255,0.02); }}
  .mono {{ font-family:monospace; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:2px; font-size:7px; letter-spacing:2px; color:#000; font-weight:700; margin-right:8px; }}
  .finding {{ background:var(--card); border:1px solid var(--border); border-radius:4px; padding:16px; margin-bottom:12px; }}
  .finding-header {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; font-size:12px; }}
  .device-tag {{ font-size:8px; color:rgba(0,212,255,0.4); margin-left:auto; }}
  .finding p {{ font-size:10px; line-height:1.65; color:rgba(0,212,255,0.65); }}
  .remediation {{ margin-top:8px; font-size:9px; color:rgba(0,255,136,0.6); background:rgba(0,255,136,0.03); border-left:2px solid rgba(0,255,136,0.3); padding:6px 10px; }}
  .timeline-table td:nth-child(2) {{ font-weight:bold; }}
  .watermark {{ text-align:center; margin-top:60px; font-size:8px; letter-spacing:6px; color:rgba(0,212,255,0.12); }}
</style>
</head>
<body>

<h1>T — PENETRATION TEST REPORT</h1>
<div class="meta">
  Date: {date_str} &nbsp;|&nbsp; Duration: {dur_str} &nbsp;|&nbsp;
  Scope: {session.target_ip or 'Home Lab'} &nbsp;|&nbsp;
  Devices: {len(session.devices)} &nbsp;|&nbsp; Authorized: YES
</div>

<h2>EXECUTIVE SUMMARY</h2>
<div class="summary-grid">
  <div class="stat"><div class="stat-num" style="color:#ff1a1a">{critical}</div><div class="stat-label">CRITICAL</div></div>
  <div class="stat"><div class="stat-num" style="color:#ff6600">{high}</div><div class="stat-label">HIGH</div></div>
  <div class="stat"><div class="stat-num" style="color:#ffb300">{medium}</div><div class="stat-label">MEDIUM</div></div>
  <div class="stat"><div class="stat-num" style="color:#00cc66">{low}</div><div class="stat-label">LOW / INFO</div></div>
</div>

<h2>NETWORK MAP — DISCOVERED DEVICES</h2>
<table>
  <tr><th>IP</th><th>HOSTNAME</th><th>TYPE</th><th>OS</th><th>OPEN PORTS</th></tr>
  {device_rows or '<tr><td colspan="5" style="color:rgba(0,212,255,0.3)">No devices discovered</td></tr>'}
</table>

<h2>FINDINGS</h2>
{finding_cards or '<p style="color:rgba(0,212,255,0.3);font-size:10px">No findings recorded.</p>'}

<h2>CREDENTIALS CAPTURED</h2>
<table>
  <tr><th>TIME</th><th>SOURCE</th><th>USERNAME</th><th>PASSWORD</th><th>NOTES</th></tr>
  {cred_rows or '<tr><td colspan="5" style="color:rgba(0,212,255,0.3)">No credentials captured</td></tr>'}
</table>

<h2>DATA ACCESSED</h2>
<table>
  <tr><th>TIME</th><th>DEVICE</th><th>DATA TYPE</th><th>SIZE</th></tr>
  {data_rows or '<tr><td colspan="4" style="color:rgba(0,212,255,0.3)">No data accessed</td></tr>'}
</table>

<h2>ATTACK TIMELINE</h2>
<table class="timeline-table">
  <tr><th>TIME</th><th>SEVERITY</th><th>PHASE</th><th>ACTION</th><th>RESULT</th></tr>
  {timeline_rows or '<tr><td colspan="5" style="color:rgba(0,212,255,0.3)">No actions logged</td></tr>'}
</table>

<h2>REMEDIATION CHECKLIST</h2>
<table>
  <tr><th>#</th><th>ACTION</th><th>PRIORITY</th></tr>
  <tr><td>1</td><td>Change all default router credentials immediately</td><td style="color:#ff1a1a">CRITICAL</td></tr>
  <tr><td>2</td><td>Disable WPS on your router — it cannot be patched, only disabled</td><td style="color:#ff1a1a">CRITICAL</td></tr>
  <tr><td>3</td><td>Update router firmware to latest version</td><td style="color:#ff6600">HIGH</td></tr>
  <tr><td>4</td><td>Enable full disk encryption on Android (Settings → Security)</td><td style="color:#ff6600">HIGH</td></tr>
  <tr><td>5</td><td>Disable USB Debugging when not actively using it</td><td style="color:#ff6600">HIGH</td></tr>
  <tr><td>6</td><td>Use a password manager — stop reusing passwords</td><td style="color:#ff6600">HIGH</td></tr>
  <tr><td>7</td><td>Enable 2FA on all accounts (Google, Facebook, email)</td><td style="color:#ff6600">HIGH</td></tr>
  <tr><td>8</td><td>Verify all installed apps — remove unknown/unrecognized ones</td><td style="color:#ffb300">MEDIUM</td></tr>
  <tr><td>9</td><td>Use a VPN on public networks</td><td style="color:#ffb300">MEDIUM</td></tr>
  <tr><td>10</td><td>Set up network monitoring (T's proactive engine covers this)</td><td style="color:#00cc66">LOW</td></tr>
</table>

<div class="watermark">GENERATED BY T · RED TEAM LAB · AUTHORIZED TESTING ONLY</div>
</body>
</html>"""

    return html


def save_report(session: LabSession) -> str:
    """Save report to disk. Returns path."""
    ts   = int(session.start_ts)
    path = REPORT_DIR / f"report_{ts}.html"
    path.write_text(generate_html(session), encoding="utf-8")
    return str(path)
