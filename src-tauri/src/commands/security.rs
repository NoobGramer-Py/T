use serde::Serialize;
use sysinfo::System;
use std::process::Command;

// ─── Helpers ─────────────────────────────────────────────────────────────────

/// Standard base64url encoding (no padding) — required by VirusTotal API v3.
fn base64url_encode(input: &[u8]) -> String {
    const TABLE: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
    let mut out = String::with_capacity((input.len() * 4 + 2) / 3);
    let mut i   = 0;
    while i < input.len() {
        let b0 = input[i] as u32;
        let b1 = if i + 1 < input.len() { input[i + 1] as u32 } else { 0 };
        let b2 = if i + 2 < input.len() { input[i + 2] as u32 } else { 0 };
        out.push(TABLE[((b0 >> 2) & 63) as usize] as char);
        out.push(TABLE[(((b0 << 4) | (b1 >> 4)) & 63) as usize] as char);
        if i + 1 < input.len() { out.push(TABLE[(((b1 << 2) | (b2 >> 6)) & 63) as usize] as char); }
        if i + 2 < input.len() { out.push(TABLE[(b2 & 63) as usize] as char); }
        i += 3;
    }
    out
}

// ─── Input validation ─────────────────────────────────────────────────────────

fn validate_target(target: &str) -> Result<(), String> {
    if target.chars().any(|c| matches!(c, ';' | '&' | '|' | '`' | '$' | '>' | '<' | '\n')) {
        return Err("Invalid target: shell metacharacters not allowed".into());
    }
    Ok(())
}

// ─── Nmap Scan ────────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct PortInfo {
    pub port:    u16,
    pub state:   String,
    pub service: String,
    pub version: String,
}

#[derive(Serialize)]
pub struct NmapResult {
    pub host:     String,
    pub ports:    Vec<PortInfo>,
    pub os_guess: String,
}

#[tauri::command]
pub fn nmap_scan(target: String, flags: String) -> Result<NmapResult, String> {
    validate_target(&target)?;
    let flag_parts: Vec<&str> = flags.split_whitespace().collect();
    let mut args = vec!["-oX", "-"];
    args.extend(flag_parts.iter().copied());
    args.push(&target);

    let out = Command::new("nmap").args(&args).output()
        .map_err(|e| format!("nmap not found: {}", e))?;
    if !out.status.success() {
        return Err(format!("nmap error: {}", String::from_utf8_lossy(&out.stderr)));
    }
    parse_nmap_xml(&String::from_utf8_lossy(&out.stdout), &target)
}

fn parse_nmap_xml(xml: &str, target: &str) -> Result<NmapResult, String> {
    let mut ports    = Vec::new();
    let mut os_guess = String::new();

    for line in xml.lines() {
        let line = line.trim();
        if line.starts_with("<port ") {
            let port_num = extract_attr(line, "portid")
                .and_then(|v| v.parse::<u16>().ok()).unwrap_or(0);
            ports.push(PortInfo { port: port_num, state: "open".into(), service: String::new(), version: String::new() });
        }
        if line.contains("<state ") {
            if let Some(last) = ports.last_mut() {
                last.state = extract_attr(line, "state").unwrap_or("unknown".into());
            }
        }
        if line.contains("<service ") {
            if let Some(last) = ports.last_mut() {
                last.service = extract_attr(line, "name").unwrap_or_default();
                let product  = extract_attr(line, "product").unwrap_or_default();
                let version  = extract_attr(line, "version").unwrap_or_default();
                last.version = format!("{} {}", product, version).trim().to_string();
            }
        }
        if line.contains("<osmatch ") && os_guess.is_empty() {
            os_guess = extract_attr(line, "name").unwrap_or_default();
        }
    }

    ports.retain(|p| p.state == "open");
    Ok(NmapResult { host: target.to_string(), ports, os_guess })
}

fn extract_attr(line: &str, attr: &str) -> Option<String> {
    let search = format!("{}=\"", attr);
    let start  = line.find(&search)? + search.len();
    let end    = line[start..].find('"')? + start;
    Some(line[start..end].to_string())
}

// ─── IP Reputation ────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct IpReputationResult {
    pub ip:         String,
    pub reputation: String,
    pub detail:     String,
}

#[tauri::command]
pub async fn check_ip_reputation(ip: String, api_key: String) -> Result<IpReputationResult, String> {
    validate_target(&ip)?;

    if api_key.is_empty() {
        return Ok(IpReputationResult {
            ip,
            reputation: "unknown".into(),
            detail: "No AbuseIPDB API key configured. Add it in Settings → Profile.".into(),
        });
    }

    let client = reqwest::Client::new();
    let res = client
        .get(format!("https://api.abuseipdb.com/api/v2/check?ipAddress={}&maxAgeInDays=90", ip))
        .header("Key", &api_key)
        .header("Accept", "application/json")
        .send().await
        .map_err(|e| e.to_string())?;

    let body: serde_json::Value = res.json().await.map_err(|e| e.to_string())?;
    let score = body["data"]["abuseConfidenceScore"].as_u64().unwrap_or(0);
    let reputation = if score == 0 { "clean" } else if score < 50 { "suspicious" } else { "malicious" };

    Ok(IpReputationResult {
        ip,
        reputation: reputation.into(),
        detail: format!("Abuse confidence: {}%", score),
    })
}

// ─── Open Port Scanner ────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct PortEntry {
    pub port:    u16,
    pub service: String,
}

const COMMON_PORTS: &[(u16, &str)] = &[
    (21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"), (53, "DNS"),
    (80, "HTTP"), (110, "POP3"), (143, "IMAP"), (443, "HTTPS"), (445, "SMB"),
    (3306, "MySQL"), (3389, "RDP"), (5432, "PostgreSQL"), (6379, "Redis"),
    (8080, "HTTP-Alt"), (8443, "HTTPS-Alt"), (27017, "MongoDB"),
];

#[tauri::command]
pub async fn get_open_ports(host: String) -> Result<Vec<PortEntry>, String> {
    validate_target(&host)?;
    use tokio::net::TcpStream;
    use tokio::time::{timeout, Duration};

    let mut open = Vec::new();
    for &(port, service) in COMMON_PORTS {
        let addr = format!("{}:{}", host, port);
        if timeout(Duration::from_millis(500), TcpStream::connect(&addr)).await
            .map(|r| r.is_ok()).unwrap_or(false)
        {
            open.push(PortEntry { port, service: service.to_string() });
        }
    }
    Ok(open)
}

// ─── Process Audit ────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct ProcessAuditEntry {
    pub pid:       u32,
    pub name:      String,
    pub suspicion: String,
    pub reason:    String,
}

const SUSPICIOUS_NAMES: &[&str] = &[
    "mimikatz", "meterpreter", "netcat", "nc.exe", "ncat", "psexec",
    "wce.exe", "fgdump", "pwdump", "gsecdump", "procdump", "cobaltstrike",
    "beacon.exe", "havoc", "sliver", "cobalt",
];

#[tauri::command]
pub fn analyze_processes() -> Result<Vec<ProcessAuditEntry>, String> {
    let mut sys = System::new_all();
    sys.refresh_all();
    let mut flagged = Vec::new();

    for process in sys.processes().values() {
        let name      = process.name().to_string_lossy().to_lowercase();
        let cpu       = process.cpu_usage();
        let (level, reason) = if SUSPICIOUS_NAMES.iter().any(|s| name.contains(s)) {
            ("critical", format!("Matches known malicious tool: {}", name))
        } else if cpu > 85.0 {
            ("suspicious", format!("Unusually high CPU: {:.1}%", cpu))
        } else {
            continue;
        };
        flagged.push(ProcessAuditEntry {
            pid:       process.pid().as_u32(),
            name:      process.name().to_string_lossy().to_string(),
            suspicion: level.to_string(),
            reason,
        });
    }
    Ok(flagged)
}

// ─── DNS Leak Check ───────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct DnsLeakResult {
    pub leaking: bool,
    pub servers: Vec<String>,
}

#[tauri::command]
pub async fn check_dns_leak() -> Result<DnsLeakResult, String> {
    let client = reqwest::Client::new();
    let res = client.get("https://bash.ws/dnsleak/test/random?json")
        .send().await.map_err(|e| e.to_string())?;
    let body: Vec<serde_json::Value> = res.json().await.map_err(|e| e.to_string())?;
    let servers: Vec<String> = body.iter()
        .filter_map(|e| e["ip"].as_str().map(String::from))
        .collect();
    Ok(DnsLeakResult { leaking: servers.len() > 1, servers })
}

// ─── VPN Status ───────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct VpnStatus {
    pub connected: bool,
    pub provider:  String,
    pub ip:        String,
    pub location:  String,
}

#[tauri::command]
pub async fn get_vpn_status() -> Result<VpnStatus, String> {
    let client = reqwest::Client::new();
    let body: serde_json::Value = client.get("https://ipapi.co/json/")
        .send().await.map_err(|e| e.to_string())?
        .json().await.map_err(|e| e.to_string())?;

    let org     = body["org"].as_str().unwrap_or("").to_string();
    let ip      = body["ip"].as_str().unwrap_or("").to_string();
    let city    = body["city"].as_str().unwrap_or("").to_string();
    let country = body["country_name"].as_str().unwrap_or("").to_string();
    let vpn_kws = ["vpn", "nordvpn", "expressvpn", "mullvad", "proton", "tunnel", "surfshark", "openvpn", "wireguard"];
    let connected = vpn_kws.iter().any(|k| org.to_lowercase().contains(k));

    Ok(VpnStatus { connected, provider: org, ip, location: format!("{}, {}", city, country) })
}

// ─── Firewall Rules ───────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct FirewallRule {
    pub name:      String,
    pub direction: String,
    pub action:    String,
    pub enabled:   bool,
    pub protocol:  String,
    pub port:      String,
}

#[tauri::command]
pub fn get_firewall_rules() -> Result<Vec<FirewallRule>, String> {
    if cfg!(target_os = "windows") {
        let out = Command::new("powershell")
            .args(["-NoProfile", "-Command",
                "Get-NetFirewallRule | Where-Object {$_.Enabled -eq 'True'} | Select-Object -First 50 DisplayName,Direction,Action,Enabled | ConvertTo-Json"])
            .output()
            .map_err(|e| e.to_string())?;

        let json_str = String::from_utf8_lossy(&out.stdout);
        let parsed: serde_json::Value = serde_json::from_str(&json_str)
            .unwrap_or(serde_json::Value::Array(vec![]));

        let rules = match parsed {
            serde_json::Value::Array(arr) => arr,
            single => vec![single],
        };

        Ok(rules.iter().filter_map(|r| {
            Some(FirewallRule {
                name:      r["DisplayName"].as_str()?.to_string(),
                direction: r["Direction"].as_str().unwrap_or("").to_string(),
                action:    r["Action"].as_str().unwrap_or("").to_string(),
                enabled:   r["Enabled"].as_bool().unwrap_or(true),
                protocol:  String::new(),
                port:      String::new(),
            })
        }).collect())
    } else {
        // Linux: parse iptables
        let out = Command::new("iptables").args(["-L", "-n", "--line-numbers"])
            .output().map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout);
        let rules = stdout.lines()
            .filter(|l| l.starts_with(|c: char| c.is_ascii_digit()))
            .map(|l| FirewallRule {
                name:      l.to_string(),
                direction: "INPUT".into(),
                action:    "ACCEPT".into(),
                enabled:   true,
                protocol:  String::new(),
                port:      String::new(),
            }).collect();
        Ok(rules)
    }
}

// ─── Password Strength ────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct PasswordStrength {
    pub score:    u8,       // 0–4
    pub label:    String,
    pub feedback: Vec<String>,
    pub entropy:  f64,
}

#[tauri::command]
pub fn check_password_strength(password: String) -> Result<PasswordStrength, String> {
    let mut feedback = Vec::new();
    let mut score    = 0u8;

    let has_lower   = password.chars().any(|c| c.is_ascii_lowercase());
    let has_upper   = password.chars().any(|c| c.is_ascii_uppercase());
    let has_digit   = password.chars().any(|c| c.is_ascii_digit());
    let has_special = password.chars().any(|c| !c.is_alphanumeric());
    let length      = password.len();

    if length >= 8  { score += 1; } else { feedback.push("Use at least 8 characters".into()); }
    if length >= 12 { score += 1; } else { feedback.push("12+ characters significantly increases strength".into()); }
    if has_lower && has_upper { score += 1; } else { feedback.push("Mix uppercase and lowercase letters".into()); }
    if has_digit  { score += 1; } else { feedback.push("Add at least one number".into()); }
    if has_special {
        if score < 4 { score = score.saturating_add(1).min(4); }
    } else {
        feedback.push("Add special characters (!@#$%^&*)".into());
    }
    score = score.min(4);

    // Rough entropy calculation
    let charset_size = [has_lower, has_upper, has_digit, has_special]
        .iter()
        .zip([26u32, 26, 10, 32])
        .map(|(b, s)| if *b { s } else { 0 })
        .sum::<u32>() as f64;
    let entropy = if charset_size > 0.0 {
        length as f64 * charset_size.log2()
    } else { 0.0 };

    // Common weak patterns
    if password.to_lowercase().contains("password") { feedback.push("Do not use the word 'password'".into()); score = 0; }
    if password.chars().all(|c| c.is_ascii_digit())  { feedback.push("Do not use numbers only".into()); score = score.min(1); }

    let label = match score {
        0 => "Very Weak",
        1 => "Weak",
        2 => "Fair",
        3 => "Strong",
        _ => "Very Strong",
    }.to_string();

    Ok(PasswordStrength { score, label, feedback, entropy })
}

// ─── URL Safety Check ─────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct UrlSafetyResult {
    pub url:    String,
    pub safe:   bool,
    pub detail: String,
}

#[tauri::command]
pub async fn check_url_safety(url: String, virustotal_key: String) -> Result<UrlSafetyResult, String> {
    if virustotal_key.is_empty() {
        return Ok(UrlSafetyResult {
            url,
            safe:   true,
            detail: "No VirusTotal API key configured. Add it in Settings.".into(),
        });
    }

    // Base64url-encode the URL (VirusTotal API v3 requirement)
    let encoded = base64url_encode(url.as_bytes());

    let client = reqwest::Client::new();
    let res = client
        .get(format!("https://www.virustotal.com/api/v3/urls/{}", encoded))
        .header("x-apikey", &virustotal_key)
        .send().await
        .map_err(|e| e.to_string())?;

    if res.status().as_u16() == 404 {
        return Ok(UrlSafetyResult { url, safe: true, detail: "URL not in VirusTotal database (likely clean)".into() });
    }

    let body: serde_json::Value = res.json().await.map_err(|e| e.to_string())?;
    let stats = &body["data"]["attributes"]["last_analysis_stats"];
    let malicious  = stats["malicious"].as_u64().unwrap_or(0);
    let suspicious = stats["suspicious"].as_u64().unwrap_or(0);
    let harmless   = stats["harmless"].as_u64().unwrap_or(0);

    let safe   = malicious == 0 && suspicious == 0;
    let detail = format!("Malicious: {} | Suspicious: {} | Clean: {}", malicious, suspicious, harmless);

    Ok(UrlSafetyResult { url, safe, detail })
}

// ─── Security Event Log ───────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct SecurityEvent {
    pub time:    String,
    pub level:   String,
    pub source:  String,
    pub message: String,
}

#[tauri::command]
pub fn get_security_log() -> Result<Vec<SecurityEvent>, String> {
    if cfg!(target_os = "windows") {
        let out = Command::new("powershell")
            .args(["-NoProfile", "-Command",
                "Get-EventLog -LogName Security -Newest 30 -ErrorAction SilentlyContinue | Select-Object TimeGenerated,EntryType,Source,Message | ConvertTo-Json"])
            .output()
            .map_err(|e| e.to_string())?;

        let json_str = String::from_utf8_lossy(&out.stdout);
        let parsed: serde_json::Value = serde_json::from_str(&json_str)
            .unwrap_or(serde_json::Value::Array(vec![]));

        let entries = match parsed {
            serde_json::Value::Array(arr) => arr,
            single => vec![single],
        };

        Ok(entries.iter().filter_map(|e| {
            Some(SecurityEvent {
                time:    e["TimeGenerated"].as_str().unwrap_or("").to_string(),
                level:   e["EntryType"].as_str().unwrap_or("Info").to_string(),
                source:  e["Source"].as_str().unwrap_or("").to_string(),
                message: e["Message"].as_str().unwrap_or("").chars().take(200).collect(),
            })
        }).collect())
    } else {
        // Linux: tail auth.log
        match Command::new("tail").args(["-n", "30", "/var/log/auth.log"]).output() {
            Ok(out) => {
                let lines = String::from_utf8_lossy(&out.stdout);
                Ok(lines.lines().map(|l| SecurityEvent {
                    time:    String::new(),
                    level:   "Info".into(),
                    source:  "auth.log".into(),
                    message: l.to_string(),
                }).collect())
            }
            Err(_) => Ok(vec![]),
        }
    }
}
