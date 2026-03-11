use serde::Serialize;
use sysinfo::System;
use std::process::Command;
use std::sync::Arc;

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

// ─── IP Intelligence ──────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct IpIntelResult {
    pub ip:           String,
    pub hostname:     String,
    pub country:      String,
    pub region:       String,
    pub city:         String,
    pub org:          String,
    pub asn:          String,
    pub isp:          String,
    pub latitude:     f64,
    pub longitude:    f64,
    pub abuse_score:  u32,
    pub abuse_detail: String,
    pub open_ports:   Vec<u16>,
}

#[tauri::command]
pub async fn ip_intel(ip: String, abuse_key: String) -> Result<IpIntelResult, String> {
    validate_target(&ip)?;

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    // ── Geo + ASN via ipapi.co (free, no key) ─────────────────────────────────
    let geo_url = format!("https://ipapi.co/{}/json/", ip);
    let geo: serde_json::Value = client
        .get(&geo_url)
        .header("User-Agent", "T-Assistant/1.0")
        .send().await.map_err(|e| e.to_string())?
        .json().await.map_err(|e| e.to_string())?;

    let country  = geo["country_name"].as_str().unwrap_or("").to_string();
    let region   = geo["region"].as_str().unwrap_or("").to_string();
    let city     = geo["city"].as_str().unwrap_or("").to_string();
    let org      = geo["org"].as_str().unwrap_or("").to_string();
    let asn      = geo["asn"].as_str().unwrap_or("").to_string();
    let isp      = geo["org"].as_str().unwrap_or("").to_string();
    let latitude  = geo["latitude"].as_f64().unwrap_or(0.0);
    let longitude = geo["longitude"].as_f64().unwrap_or(0.0);

    // ── Reverse DNS ───────────────────────────────────────────────────────────
    let hostname = {
        let cmd = if cfg!(target_os = "windows") {
            Command::new("powershell")
                .args(["-NoProfile", "-Command",
                    &format!("[System.Net.Dns]::GetHostEntry('{}').HostName", ip)])
                .output()
        } else {
            Command::new("host").arg(&ip).output()
        };
        match cmd {
            Ok(out) => {
                let s = String::from_utf8_lossy(&out.stdout).trim().to_string();
                if s.is_empty() { ip.clone() } else { s.lines().next().unwrap_or(&ip).to_string() }
            }
            Err(_) => ip.clone(),
        }
    };

    // ── AbuseIPDB (optional, only if key provided) ────────────────────────────
    let (abuse_score, abuse_detail) = if !abuse_key.is_empty() {
        let url = format!("https://api.abuseipdb.com/api/v2/check?ipAddress={}&maxAgeInDays=90", ip);
        match client.get(&url)
            .header("Key", &abuse_key)
            .header("Accept", "application/json")
            .send().await
        {
            Ok(resp) => {
                match resp.json::<serde_json::Value>().await {
                    Ok(v) => {
                        let score   = v["data"]["abuseConfidenceScore"].as_u64().unwrap_or(0) as u32;
                        let reports = v["data"]["totalReports"].as_u64().unwrap_or(0);
                        let detail  = format!("{} reports in last 90 days", reports);
                        (score, detail)
                    }
                    Err(_) => (0, "Parse error".into()),
                }
            }
            Err(_) => (0, "AbuseIPDB unavailable".into()),
        }
    } else {
        (0, "No AbuseIPDB key — set in Settings".into())
    };

    // ── Fast parallel port probe on common ports ─────────────────────────────
    let probe_ports: &[u16] = &[21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5900, 8080, 8443];
    let sem = Arc::new(tokio::sync::Semaphore::new(15));
    let mut handles = Vec::new();
    for &port in probe_ports {
        let ip_clone = ip.clone();
        let sem_clone = sem.clone();
        handles.push(tokio::spawn(async move {
            let _permit = sem_clone.acquire().await.unwrap();
            let addr = format!("{}:{}", ip_clone, port);
            let open = tokio::time::timeout(
                std::time::Duration::from_millis(600),
                tokio::net::TcpStream::connect(&addr),
            ).await.map(|r| r.is_ok()).unwrap_or(false);
            if open { Some(port) } else { None }
        }));
    }
    let mut open_ports = Vec::new();
    for h in handles {
        if let Ok(Some(port)) = h.await { open_ports.push(port); }
    }
    open_ports.sort_unstable();

    Ok(IpIntelResult {
        ip, hostname, country, region, city,
        org, asn, isp, latitude, longitude,
        abuse_score, abuse_detail, open_ports,
    })
}

// ─── Email OSINT ──────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct BreachEntry {
    pub name:         String,
    pub domain:       String,
    pub breach_date:  String,
    pub description:  String,
    pub data_classes: Vec<String>,
    pub pwn_count:    u64,
}

#[derive(Serialize)]
pub struct EmailOsintResult {
    pub email:       String,
    pub valid:       bool,
    pub domain:      String,
    pub mx_records:  Vec<String>,
    pub gravatar_url: Option<String>,
    pub breaches:    Vec<BreachEntry>,
    pub breach_count: usize,
    pub paste_count:  usize,
}

fn md5_hex(input: &str) -> String {
    // RFC 1321 MD5 — minimal inline implementation for Gravatar
    let bytes = input.as_bytes();
    let mut msg = bytes.to_vec();
    let bit_len = (bytes.len() as u64).wrapping_mul(8);
    msg.push(0x80);
    while msg.len() % 64 != 56 { msg.push(0); }
    msg.extend_from_slice(&bit_len.to_le_bytes());

    let mut h: [u32; 4] = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476];
    let s: [u32; 64] = [
        7,12,17,22,7,12,17,22,7,12,17,22,7,12,17,22,
        5, 9,14,20,5, 9,14,20,5, 9,14,20,5, 9,14,20,
        4,11,16,23,4,11,16,23,4,11,16,23,4,11,16,23,
        6,10,15,21,6,10,15,21,6,10,15,21,6,10,15,21,
    ];
    let k: [u32; 64] = [
        0xd76aa478,0xe8c7b756,0x242070db,0xc1bdceee,0xf57c0faf,0x4787c62a,0xa8304613,0xfd469501,
        0x698098d8,0x8b44f7af,0xffff5bb1,0x895cd7be,0x6b901122,0xfd987193,0xa679438e,0x49b40821,
        0xf61e2562,0xc040b340,0x265e5a51,0xe9b6c7aa,0xd62f105d,0x02441453,0xd8a1e681,0xe7d3fbc8,
        0x21e1cde6,0xc33707d6,0xf4d50d87,0x455a14ed,0xa9e3e905,0xfcefa3f8,0x676f02d9,0x8d2a4c8a,
        0xfffa3942,0x8771f681,0x6d9d6122,0xfde5380c,0xa4beea44,0x4bdecfa9,0xf6bb4b60,0xbebfbc70,
        0x289b7ec6,0xeaa127fa,0xd4ef3085,0x04881d05,0xd9d4d039,0xe6db99e5,0x1fa27cf8,0xc4ac5665,
        0xf4292244,0x432aff97,0xab9423a7,0xfc93a039,0x655b59c3,0x8f0ccc92,0xffeff47d,0x85845dd1,
        0x6fa87e4f,0xfe2ce6e0,0xa3014314,0x4e0811a1,0xf7537e82,0xbd3af235,0x2ad7d2bb,0xeb86d391,
    ];

    for chunk in msg.chunks(64) {
        let mut m = [0u32; 16];
        for (i, w) in m.iter_mut().enumerate() {
            *w = u32::from_le_bytes([chunk[i*4], chunk[i*4+1], chunk[i*4+2], chunk[i*4+3]]);
        }
        let (mut a, mut b, mut c, mut d) = (h[0], h[1], h[2], h[3]);
        for i in 0u32..64 {
            let (f, g) = match i {
                0..=15  => (( b & c) | (!b & d), i),
                16..=31 => (( d & b) | (!d & c), (5*i+1) % 16),
                32..=47 => (b ^ c ^ d, (3*i+5) % 16),
                _       => (c ^ (b | !d), (7*i) % 16),
            };
            let temp = d;
            d = c; c = b;
            b = b.wrapping_add(
                a.wrapping_add(f).wrapping_add(k[i as usize]).wrapping_add(m[g as usize])
                .rotate_left(s[i as usize])
            );
            a = temp;
        }
        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
    }

    let mut out = String::with_capacity(32);
    for word in &h {
        for byte in &word.to_le_bytes() {
            out.push_str(&format!("{:02x}", byte));
        }
    }
    out
}

#[tauri::command]
pub async fn email_osint(email: String, hibp_key: String) -> Result<EmailOsintResult, String> {
    // ── Basic validation ──────────────────────────────────────────────────────
    let parts: Vec<&str> = email.split('@').collect();
    let valid  = parts.len() == 2 && !parts[0].is_empty() && parts[1].contains('.');
    let domain = if valid { parts[1].to_string() } else { String::new() };

    if !valid {
        return Ok(EmailOsintResult {
            email, valid, domain,
            mx_records: vec![], gravatar_url: None,
            breaches: vec![], breach_count: 0, paste_count: 0,
        });
    }

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    // ── MX records ────────────────────────────────────────────────────────────
    let mx_records = {
        let cmd = if cfg!(target_os = "windows") {
            Command::new("powershell")
                .args(["-NoProfile", "-Command",
                    &format!("Resolve-DnsName -Type MX {} | Select-Object -ExpandProperty NameExchange", domain)])
                .output()
        } else {
            Command::new("dig").args(["+short", "MX", &domain]).output()
        };
        match cmd {
            Ok(out) => String::from_utf8_lossy(&out.stdout)
                .lines()
                .filter(|l| !l.trim().is_empty())
                .map(|l| l.trim().to_string())
                .collect(),
            Err(_) => vec![],
        }
    };

    // ── Gravatar ──────────────────────────────────────────────────────────────
    let hash         = md5_hex(&email.trim().to_lowercase());
    let gravatar_url = {
        let check_url = format!("https://www.gravatar.com/avatar/{}?d=404", hash);
        match client.get(&check_url).send().await {
            Ok(r) if r.status().is_success() =>
                Some(format!("https://www.gravatar.com/avatar/{}?s=200", hash)),
            _ => None,
        }
    };

    // ── HIBP breach lookup ────────────────────────────────────────────────────
    let (breaches, breach_count, paste_count) = if !hibp_key.is_empty() {
        let url = format!("https://haveibeenpwned.com/api/v3/breachedaccount/{}?truncateResponse=false", email);
        match client.get(&url)
            .header("hibp-api-key", &hibp_key)
            .header("User-Agent", "T-Assistant/1.0")
            .send().await
        {
            Ok(resp) => {
                let status = resp.status();
                if status.as_u16() == 404 {
                    // 404 = not found in any breach (good)
                    (vec![], 0, 0)
                } else if status.is_success() {
                    match resp.json::<serde_json::Value>().await {
                        Ok(arr) => {
                            let entries: Vec<BreachEntry> = arr.as_array()
                                .unwrap_or(&vec![])
                                .iter()
                                .map(|b| BreachEntry {
                                    name:        b["Name"].as_str().unwrap_or("").to_string(),
                                    domain:      b["Domain"].as_str().unwrap_or("").to_string(),
                                    breach_date: b["BreachDate"].as_str().unwrap_or("").to_string(),
                                    description: b["Description"].as_str().unwrap_or("").to_string(),
                                    pwn_count:   b["PwnCount"].as_u64().unwrap_or(0),
                                    data_classes: b["DataClasses"].as_array()
                                        .unwrap_or(&vec![])
                                        .iter()
                                        .filter_map(|v| v.as_str().map(|s| s.to_string()))
                                        .collect(),
                                })
                                .collect();
                            let count = entries.len();
                            (entries, count, 0)
                        }
                        Err(_) => (vec![], 0, 0),
                    }
                } else {
                    (vec![], 0, 0)
                }
            }
            Err(_) => (vec![], 0, 0),
        }
    } else {
        (vec![], 0, 0)
    };

    Ok(EmailOsintResult {
        email, valid, domain, mx_records,
        gravatar_url, breaches, breach_count, paste_count,
    })
}


// ─── Full Port Scanner ────────────────────────────────────────────────────────

/// Extended service name map for port scanner results.
const SERVICE_MAP: &[(u16, &str)] = &[
    (21,"FTP"),(22,"SSH"),(23,"Telnet"),(25,"SMTP"),(53,"DNS"),
    (80,"HTTP"),(110,"POP3"),(119,"NNTP"),(123,"NTP"),(135,"MSRPC"),
    (139,"NetBIOS"),(143,"IMAP"),(194,"IRC"),(443,"HTTPS"),(445,"SMB"),
    (465,"SMTPS"),(587,"SMTP"),(631,"IPP"),(993,"IMAPS"),(995,"POP3S"),
    (1433,"MSSQL"),(1723,"PPTP"),(3306,"MySQL"),(3389,"RDP"),
    (5432,"PostgreSQL"),(5900,"VNC"),(6379,"Redis"),(8080,"HTTP-Alt"),
    (8443,"HTTPS-Alt"),(8888,"HTTP-Alt2"),(9200,"Elasticsearch"),
    (27017,"MongoDB"),(27018,"MongoDB"),(50000,"DB2"),
];

#[derive(Serialize)]
pub struct FullScanResult {
    pub host:        String,
    pub open:        Vec<PortEntry>,
    pub scanned:     u32,
    pub duration_ms: u64,
}

#[tauri::command]
pub async fn full_port_scan(host: String, start_port: u16, end_port: u16) -> Result<FullScanResult, String> {
    validate_target(&host)?;

    if end_port < start_port {
        return Err("end_port must be >= start_port".into());
    }
    // Cap range to prevent runaway scans
    let range_size = (end_port as u32).saturating_sub(start_port as u32) + 1;
    if range_size > 10_000 {
        return Err("Range too large. Maximum 10 000 ports per scan.".into());
    }

    let started   = std::time::Instant::now();
    let sem       = Arc::new(tokio::sync::Semaphore::new(256));
    let mut handles = Vec::new();

    for port in start_port..=end_port {
        let host_clone = host.clone();
        let sem_clone  = sem.clone();
        handles.push(tokio::spawn(async move {
            let _permit = sem_clone.acquire().await.unwrap();
            let addr    = format!("{}:{}", host_clone, port);
            let open    = tokio::time::timeout(
                std::time::Duration::from_millis(500),
                tokio::net::TcpStream::connect(&addr),
            ).await.map(|r| r.is_ok()).unwrap_or(false);
            if open { Some(port) } else { None }
        }));
    }

    let mut open_ports: Vec<u16> = Vec::new();
    for h in handles {
        if let Ok(Some(port)) = h.await { open_ports.push(port); }
    }
    open_ports.sort_unstable();

    let open: Vec<PortEntry> = open_ports.iter().map(|&p| {
        let service = SERVICE_MAP.iter()
            .find(|&&(sp, _)| sp == p)
            .map(|(_, s)| s.to_string())
            .unwrap_or_default();
        PortEntry { port: p, service }
    }).collect();

    Ok(FullScanResult {
        host,
        open,
        scanned:     range_size,
        duration_ms: started.elapsed().as_millis() as u64,
    })
}

// ─── CVE Search ───────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct CveEntry {
    pub id:          String,
    pub description: String,
    pub severity:    String,
    pub cvss_score:  f64,
    pub published:   String,
    pub references:  Vec<String>,
}

#[tauri::command]
pub async fn cve_search(query: String) -> Result<Vec<CveEntry>, String> {
    if query.trim().is_empty() {
        return Ok(vec![]);
    }

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .map_err(|e| e.to_string())?;

    let encoded = query.trim().replace(' ', "%20");
    let url = format!(
        "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={}&resultsPerPage=15",
        encoded
    );

    let resp: serde_json::Value = client
        .get(&url)
        .header("User-Agent", "T-Assistant/1.0")
        .send().await.map_err(|e| e.to_string())?
        .json().await.map_err(|e| e.to_string())?;

    let items = resp["vulnerabilities"].as_array()
        .ok_or("Unexpected NVD response format")?;

    let results = items.iter().filter_map(|item| {
        let cve = &item["cve"];
        let id  = cve["id"].as_str()?.to_string();

        let description = cve["descriptions"].as_array()?
            .iter()
            .find(|d| d["lang"].as_str() == Some("en"))
            .and_then(|d| d["value"].as_str())
            .unwrap_or("")
            .to_string();

        // CVSS v3.1 preferred, fall back to v2
        let (cvss_score, severity) = {
            let m31 = &cve["metrics"]["cvssMetricV31"];
            let m30 = &cve["metrics"]["cvssMetricV30"];
            let m2  = &cve["metrics"]["cvssMetricV2"];
            let src = if m31.is_array() && !m31.as_array().unwrap().is_empty() { &m31[0] }
                      else if m30.is_array() && !m30.as_array().unwrap().is_empty() { &m30[0] }
                      else { &m2[0] };
            let score    = src["cvssData"]["baseScore"].as_f64().unwrap_or(0.0);
            let severity = src["cvssData"]["baseSeverity"]
                .as_str()
                .or_else(|| src["baseSeverity"].as_str())
                .unwrap_or("UNKNOWN")
                .to_string();
            (score, severity)
        };

        let published = cve["published"].as_str().unwrap_or("").to_string();

        let references: Vec<String> = cve["references"].as_array()
            .unwrap_or(&vec![])
            .iter()
            .filter_map(|r| r["url"].as_str().map(|s| s.to_string()))
            .take(3)
            .collect();

        Some(CveEntry { id, description, severity, cvss_score, published, references })
    }).collect();

    Ok(results)
}
