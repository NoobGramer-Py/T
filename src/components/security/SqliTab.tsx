import { useState } from "react";
import { useOffensive } from "../../hooks/useBridge";

const J   = "#00d4ff";
const DIM = "rgba(0,212,255,0.35)";
const W   = "#ff6600";

function Btn({ label, onClick, disabled = false, glow = false }: {
  label: string; onClick: () => void; disabled?: boolean; glow?: boolean;
}) {
  const c = glow ? "#00ff88" : J;
  return (
    <button onClick={onClick} disabled={disabled} style={{
      padding: "6px 16px", fontSize: 8, letterSpacing: 2,
      background: `rgba(${glow ? "0,255,136" : "0,212,255"},0.07)`,
      border: `1px solid ${disabled ? "rgba(0,212,255,0.08)" : c + "55"}`,
      color: disabled ? "rgba(0,212,255,0.2)" : c,
      borderRadius: 3, cursor: disabled ? "not-allowed" : "pointer",
      fontFamily: "inherit", whiteSpace: "nowrap" as const,
    }}>{label}</button>
  );
}

function Input({ label, value, onChange, placeholder = "", mono = false }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; mono?: boolean;
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 4 }}>{label}</div>
      <input value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} style={{
          width: "100%", background: "rgba(0,212,255,0.03)",
          border: "1px solid rgba(0,212,255,0.12)", borderRadius: 3,
          padding: "6px 10px", color: "rgba(160,244,255,0.9)",
          fontSize: 10, fontFamily: mono ? "monospace" : "inherit",
          outline: "none", caretColor: J,
        }} />
    </div>
  );
}

type Mode = "quick" | "forms" | "login" | "post" | "dump" | "waf";

export function SqliTab() {
  const off = useOffensive();
  const [mode,      setMode]      = useState<Mode>("quick");
  const [url,       setUrl]       = useState("");
  const [userField, setUserField] = useState("username");
  const [passField, setPassField] = useState("password");
  const [postData,  setPostData]  = useState("");
  const [cookie,    setCookie]    = useState("");
  const [db,        setDb]        = useState("");
  const [table,     setTable]     = useState("");

  const dispatch = (tool: string, params: Record<string, unknown>) =>
    off.dispatch(tool, params);

  const MODES: { id: Mode; label: string; desc: string }[] = [
    { id: "quick",  label: "QUICK SCAN",     desc: "Fast detection — low noise" },
    { id: "forms",  label: "FORM SCAN",      desc: "Auto-detect and test all forms on page" },
    { id: "login",  label: "LOGIN BYPASS",   desc: "Test if login can be bypassed" },
    { id: "post",   label: "POST REQUEST",   desc: "Test a POST endpoint with custom data" },
    { id: "dump",   label: "DUMP DATA",      desc: "Extract databases / tables after finding injection" },
    { id: "waf",    label: "WAF DETECT",     desc: "Detect firewall before testing" },
  ];

  const outputText = off.streamLines.map(l => l.chunk).join("\n");

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>

      {/* Header */}
      <div style={{
        padding: "12px 20px 0",
        borderBottom: "1px solid rgba(0,212,255,0.08)", flexShrink: 0,
      }}>
        <div style={{ fontSize: 9, letterSpacing: 6, color: DIM, marginBottom: 6 }}>
          T · SQL INJECTION TESTING
        </div>
        <div style={{ fontSize: 8, color: "rgba(255,102,0,0.55)", marginBottom: 10 }}>
          ⚠ Test only on systems you own or have explicit written permission to test
        </div>

        {/* Mode tabs */}
        <div style={{ display: "flex", gap: 2, overflowX: "auto" }}>
          {MODES.map(m => (
            <button key={m.id} onClick={() => setMode(m.id)} style={{
              padding: "5px 12px", fontSize: 7, letterSpacing: 2,
              background: "transparent", border: "none", whiteSpace: "nowrap",
              borderBottom: `2px solid ${mode === m.id ? J : "transparent"}`,
              color: mode === m.id ? J : DIM,
              cursor: "pointer", fontFamily: "inherit",
            }}>{m.label}</button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* Left — controls */}
        <div style={{
          width: 320, flexShrink: 0, padding: "16px 20px",
          borderRight: "1px solid rgba(0,212,255,0.07)",
          overflowY: "auto",
        }}>
          <div style={{
            fontSize: 9, color: "rgba(0,212,255,0.45)",
            marginBottom: 16, lineHeight: 1.7,
            background: "rgba(0,212,255,0.02)",
            border: "1px solid rgba(0,212,255,0.07)",
            borderRadius: 3, padding: "10px 12px",
          }}>
            {MODES.find(m => m.id === mode)?.desc}
          </div>

          {/* QUICK */}
          {mode === "quick" && (
            <>
              <Input label="TARGET URL (with parameter)" value={url} onChange={setUrl}
                placeholder="https://yoursite.com/search?q=test" mono />
              <div style={{ fontSize: 8, color: DIM, marginBottom: 12, lineHeight: 1.6 }}>
                The URL must contain a parameter (after ?) to test.<br />
                E.g. ?id=1 or ?search=test
              </div>
              <Btn label="▶ QUICK SCAN" glow onClick={() => dispatch("sqli_quick", { url })}
                disabled={!url} />
            </>
          )}

          {/* FORMS */}
          {mode === "forms" && (
            <>
              <Input label="PAGE URL" value={url} onChange={setUrl}
                placeholder="https://yoursite.com/login" mono />
              <div style={{ fontSize: 8, color: DIM, marginBottom: 12, lineHeight: 1.6 }}>
                T will crawl the page, find all forms (login, search, contact)
                and test each one automatically.
              </div>
              <Btn label="▶ SCAN ALL FORMS" glow onClick={() => dispatch("sqli_forms", { url })}
                disabled={!url} />
            </>
          )}

          {/* LOGIN BYPASS */}
          {mode === "login" && (
            <>
              <Input label="LOGIN PAGE URL" value={url} onChange={setUrl}
                placeholder="https://yoursite.com/login" mono />
              <Input label="USERNAME FIELD NAME" value={userField} onChange={setUserField}
                placeholder="username" mono />
              <Input label="PASSWORD FIELD NAME" value={passField} onChange={setPassField}
                placeholder="password" mono />
              <div style={{ fontSize: 8, color: DIM, marginBottom: 12, lineHeight: 1.6 }}>
                Field names are the HTML input name= attributes.<br />
                Inspect the form to find them.
              </div>
              <Btn label="▶ TEST LOGIN BYPASS" glow
                onClick={() => dispatch("sqli_login", { url, user_field: userField, pass_field: passField })}
                disabled={!url} />

              {/* Manual payloads reference */}
              <div style={{
                marginTop: 16,
                background: "rgba(0,212,255,0.02)",
                border: "1px solid rgba(0,212,255,0.07)",
                borderRadius: 3, padding: "12px 14px",
              }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 10 }}>
                  MANUAL PAYLOADS — paste into login form
                </div>
                {[
                  ["' OR 1=1--",         "Basic bypass"],
                  ["admin'--",           "Login as admin"],
                  ["' OR '1'='1",        "Always true"],
                  ["1' OR '1'='1",       "Numeric"],
                  ["' OR 1=1#",          "MySQL comment"],
                ].map(([payload, desc]) => (
                  <div key={payload} style={{ marginBottom: 6 }}>
                    <code style={{ fontSize: 9, color: "#a0f4ff", fontFamily: "monospace" }}>
                      {payload}
                    </code>
                    <span style={{ fontSize: 8, color: DIM, marginLeft: 8 }}>← {desc}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* POST */}
          {mode === "post" && (
            <>
              <Input label="ENDPOINT URL" value={url} onChange={setUrl}
                placeholder="https://yoursite.com/api/search" mono />
              <Input label="POST DATA" value={postData} onChange={setPostData}
                placeholder="id=1&category=news" mono />
              <Input label="SESSION COOKIE (optional)" value={cookie} onChange={setCookie}
                placeholder="PHPSESSID=abc123; token=xyz" mono />
              <div style={{ fontSize: 8, color: DIM, marginBottom: 12, lineHeight: 1.6 }}>
                Copy POST data from browser DevTools → Network tab.<br />
                Add session cookie if endpoint requires login.
              </div>
              <Btn label="▶ TEST POST ENDPOINT" glow
                onClick={() => dispatch("sqli_post", { url, data: postData, cookie })}
                disabled={!url || !postData} />
            </>
          )}

          {/* DUMP */}
          {mode === "dump" && (
            <>
              <Input label="VULNERABLE URL" value={url} onChange={setUrl}
                placeholder="https://yoursite.com/page?id=1" mono />
              <div style={{ marginBottom: 12 }}>
                <Btn label="LIST ALL DATABASES" onClick={() => dispatch("sqli_dump_dbs", { url })}
                  disabled={!url} />
              </div>
              <div style={{
                borderTop: "1px solid rgba(0,212,255,0.06)", paddingTop: 14, marginBottom: 14,
              }}>
                <div style={{ fontSize: 7, letterSpacing: 3, color: DIM, marginBottom: 10 }}>
                  DUMP SPECIFIC TABLE
                </div>
                <Input label="DATABASE NAME" value={db} onChange={setDb} placeholder="myapp_db" mono />
                <Input label="TABLE NAME" value={table} onChange={setTable} placeholder="users" mono />
                <Btn label="DUMP TABLE" glow
                  onClick={() => dispatch("sqli_dump_table", { url, db, table })}
                  disabled={!url || !db || !table} />
              </div>
              <div style={{
                background: "rgba(255,102,0,0.04)", border: "1px solid rgba(255,102,0,0.15)",
                borderRadius: 3, padding: "10px 12px", fontSize: 8,
                color: "rgba(255,102,0,0.7)", lineHeight: 1.7,
              }}>
                ⚠ Only run dump after confirming injection exists.<br />
                Common tables to check: users, accounts, admin, customers
              </div>
            </>
          )}

          {/* WAF */}
          {mode === "waf" && (
            <>
              <Input label="TARGET URL" value={url} onChange={setUrl}
                placeholder="https://yoursite.com" mono />
              <div style={{ fontSize: 8, color: DIM, marginBottom: 12, lineHeight: 1.6 }}>
                Detects Web Application Firewalls (Cloudflare, ModSecurity, etc.)
                before injection testing. A WAF may block SQLmap or ban your IP.
              </div>
              <Btn label="▶ DETECT WAF" glow
                onClick={() => dispatch("sqli_waf", { url })} disabled={!url} />
            </>
          )}

        </div>

        {/* Right — output */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{
            padding: "8px 16px", flexShrink: 0,
            borderBottom: "1px solid rgba(0,212,255,0.06)",
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontSize: 7, letterSpacing: 4, color: DIM }}>OUTPUT</span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {!off.lastDone && off.streamLines.length > 0 && (
                <span style={{ fontSize: 8, color: W, animation: "data-flicker 1.5s ease infinite" }}>
                  RUNNING...
                </span>
              )}
              <button onClick={() => off.clearStream()} style={{
                fontSize: 7, letterSpacing: 2, padding: "3px 8px",
                background: "transparent", border: "1px solid rgba(0,212,255,0.1)",
                color: DIM, cursor: "pointer", fontFamily: "inherit", borderRadius: 2,
              }}>CLEAR</button>
            </div>
          </div>

          <div style={{
            flex: 1, overflowY: "auto", padding: "12px 16px",
            fontFamily: "monospace", fontSize: 10, lineHeight: 1.7,
          }}>
            {!outputText ? (
              <div style={{ color: DIM, fontStyle: "italic", padding: "20px 0" }}>
                Select a mode and run a test — output streams here live.
              </div>
            ) : (
              outputText.split("\n").map((line, i) => {
                const color =
                  line.includes("[CRITICAL]") || line.includes("injectable") ? "#00ff88" :
                  line.includes("[ERROR]")    || line.includes("[FAIL]")      ? "#ff3300" :
                  line.includes("[WARNING]")  || line.includes("[!]")         ? W :
                  line.includes("[INFO]")     || line.includes("[*]")         ? J :
                  line.startsWith("[T]")                                       ? "#a0f4ff" :
                  "rgba(0,212,255,0.7)";
                return (
                  <div key={i} style={{ color, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                    {line}
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
