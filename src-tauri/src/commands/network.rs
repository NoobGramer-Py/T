use serde::Serialize;
use std::process::Command;

fn validate_host(host: &str) -> Result<(), String> {
    if host.chars().any(|c| matches!(c, ';' | '&' | '|' | '`' | '\n' | '\r')) {
        return Err("Invalid host: illegal characters".into());
    }
    if host.is_empty() {
        return Err("Host cannot be empty".into());
    }
    Ok(())
}

// ─── Ping ─────────────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct PingResult {
    pub host:        String,
    pub avg_ms:      f64,
    pub min_ms:      f64,
    pub max_ms:      f64,
    pub packet_loss: u8,
    pub packets_sent: u8,
}

#[tauri::command]
pub fn ping_host(host: String, count: Option<u8>) -> Result<PingResult, String> {
    validate_host(&host)?;
    let n = count.unwrap_or(4).min(20).to_string();

    let (flag, c_flag) = if cfg!(target_os = "windows") { ("-n", n.as_str()) } else { ("-c", n.as_str()) };
    let out = Command::new("ping")
        .args([flag, c_flag, &host])
        .output()
        .map_err(|e| format!("ping failed: {}", e))?;

    let stdout = String::from_utf8_lossy(&out.stdout);
    parse_ping_output(&stdout, &host, count.unwrap_or(4))
}

fn parse_ping_output(output: &str, host: &str, sent: u8) -> Result<PingResult, String> {
    let mut avg_ms = 0.0f64;
    let mut min_ms = 0.0f64;
    let mut max_ms = 0.0f64;
    let mut packet_loss = 100u8;

    for line in output.lines() {
        let lower = line.to_lowercase();

        // Windows: "Minimum = 10ms, Maximum = 12ms, Average = 11ms"
        // Linux:   "rtt min/avg/max/mdev = 10.1/11.2/12.3/0.5 ms"
        if lower.contains("average") || lower.contains("avg") {
            if lower.contains('/') {
                // Linux format
                let parts: Vec<&str> = line.split('=').nth(1)
                    .unwrap_or("").split('/').collect();
                min_ms = parts.first().and_then(|s| s.trim().parse().ok()).unwrap_or(0.0);
                avg_ms = parts.get(1).and_then(|s| s.trim().parse().ok()).unwrap_or(0.0);
                max_ms = parts.get(2).and_then(|s| s.trim().parse().ok()).unwrap_or(0.0);
            } else {
                // Windows format
                avg_ms = extract_ms_value(line, "Average").unwrap_or(0.0);
                min_ms = extract_ms_value(line, "Minimum").unwrap_or(0.0);
                max_ms = extract_ms_value(line, "Maximum").unwrap_or(0.0);
            }
        }

        if lower.contains("loss") || lower.contains("lost") {
            packet_loss = extract_loss(line).unwrap_or(packet_loss);
        }
    }

    Ok(PingResult { host: host.to_string(), avg_ms, min_ms, max_ms, packet_loss, packets_sent: sent })
}

fn extract_ms_value(line: &str, label: &str) -> Option<f64> {
    let idx = line.to_lowercase().find(&label.to_lowercase())?;
    let after = &line[idx + label.len()..];
    let num_start = after.find(|c: char| c.is_ascii_digit())?;
    let num_str: String = after[num_start..].chars()
        .take_while(|c| c.is_ascii_digit() || *c == '.').collect();
    num_str.parse().ok()
}

fn extract_loss(line: &str) -> Option<u8> {
    let idx = line.find('%')?;
    let before = &line[..idx];
    let num_str: String = before.chars().rev()
        .take_while(|c| c.is_ascii_digit())
        .collect::<String>().chars().rev().collect();
    num_str.parse().ok()
}

// ─── Traceroute ───────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct HopInfo {
    pub hop:     u8,
    pub host:    String,
    pub ip:      String,
    pub ms:      f64,
    pub timeout: bool,
}

#[tauri::command]
pub fn traceroute(host: String) -> Result<Vec<HopInfo>, String> {
    validate_host(&host)?;

    let (cmd, args): (&str, Vec<&str>) = if cfg!(target_os = "windows") {
        ("tracert", vec!["-d", "-h", "30", &host])
    } else {
        ("traceroute", vec!["-m", "30", "-n", &host])
    };

    let out = Command::new(cmd).args(&args).output()
        .map_err(|e| format!("{} failed: {}", cmd, e))?;

    let stdout = String::from_utf8_lossy(&out.stdout);
    Ok(parse_traceroute(&stdout, cfg!(target_os = "windows")))
}

fn parse_traceroute(output: &str, is_windows: bool) -> Vec<HopInfo> {
    let mut hops = Vec::new();

    for line in output.lines() {
        let line = line.trim();
        if line.is_empty() { continue; }

        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() { continue; }

        // First token must be a hop number
        let hop: u8 = match parts[0].parse() {
            Ok(n) => n,
            Err(_) => continue,
        };

        // Timeout line: all * 
        let all_stars = parts[1..].iter().all(|&p| p == "*");
        if all_stars {
            hops.push(HopInfo { hop, host: "*".into(), ip: "*".into(), ms: 0.0, timeout: true });
            continue;
        }

        // Extract latency: first number followed by or near "ms"
        let ms = if is_windows {
            // Windows tracert: "  1    <1 ms    <1 ms    <1 ms  10.0.0.1"
            parts.iter()
                .filter_map(|p| p.trim_start_matches('<').parse::<f64>().ok())
                .next()
                .unwrap_or(0.0)
        } else {
            // Linux traceroute: "  1  10.0.0.1  0.543 ms  0.521 ms  0.501 ms"
            parts.iter()
                .zip(parts.iter().skip(1))
                .find_map(|(val, unit)| {
                    if *unit == "ms" { val.parse::<f64>().ok() } else { None }
                })
                .unwrap_or(0.0)
        };

        // Extract IP/host — last token that looks like an IP or hostname
        let ip_or_host = if is_windows {
            parts.last().unwrap_or(&"*").to_string()
        } else {
            parts.get(1).unwrap_or(&"*").to_string()
        };

        let (ip, hostname) = if ip_or_host.chars().next().map(|c| c.is_ascii_digit()).unwrap_or(false) {
            (ip_or_host.clone(), ip_or_host)
        } else {
            (ip_or_host.clone(), ip_or_host)
        };

        hops.push(HopInfo { hop, host: hostname, ip, ms, timeout: false });
    }

    hops
}

// ─── DNS Lookup ───────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct DnsResult {
    pub a:     Vec<String>,
    pub aaaa:  Vec<String>,
    pub mx:    Vec<String>,
    pub ns:    Vec<String>,
    pub txt:   Vec<String>,
    pub cname: Vec<String>,
}

#[tauri::command]
pub fn dns_lookup(domain: String) -> Result<DnsResult, String> {
    validate_host(&domain)?;

    let query = |record_type: &str| -> Vec<String> {
        let out = if cfg!(target_os = "windows") {
            Command::new("nslookup")
                .args([&format!("-type={}", record_type), &domain])
                .output()
        } else {
            Command::new("dig")
                .args([&domain, record_type, "+short"])
                .output()
                .or_else(|_| Command::new("nslookup")
                    .args([&format!("-type={}", record_type), &domain])
                    .output())
        };

        match out {
            Ok(o) if cfg!(target_os = "windows") => {
                parse_nslookup_type(&String::from_utf8_lossy(&o.stdout), record_type)
            }
            Ok(o) => {
                String::from_utf8_lossy(&o.stdout)
                    .lines()
                    .map(|l| l.trim().to_string())
                    .filter(|l| !l.is_empty() && !l.starts_with(';'))
                    .collect()
            }
            Err(_) => Vec::new(),
        }
    };

    Ok(DnsResult {
        a:     query("A"),
        aaaa:  query("AAAA"),
        mx:    query("MX"),
        ns:    query("NS"),
        txt:   query("TXT"),
        cname: query("CNAME"),
    })
}

fn parse_nslookup_type(output: &str, record_type: &str) -> Vec<String> {
    let mut results = Vec::new();
    // Skip lines with "Server:" or "Address:" at the top (name server lines)
    let mut past_header = false;

    for line in output.lines() {
        let line = line.trim();
        if line.starts_with("Name:") { past_header = true; }
        if !past_header { continue; }

        let marker = match record_type {
            "A" | "AAAA" => "Address:",
            "MX"         => "mail exchanger =",
            "NS"         => "nameserver =",
            "TXT"        => "text =",
            "CNAME"      => "canonical name =",
            _            => "Address:",
        };

        if line.contains(marker) {
            if let Some(val) = line.split(marker).nth(1) {
                let clean = val.trim().to_string();
                if !clean.is_empty() {
                    results.push(clean);
                }
            }
        }
    }
    results
}

// ─── Whois ────────────────────────────────────────────────────────────────────

#[tauri::command]
pub async fn whois_lookup(domain: String) -> Result<String, String> {
    validate_host(&domain)?;

    // Try system whois first
    if let Ok(out) = Command::new("whois").arg(&domain).output() {
        let result = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if !result.is_empty() && result.len() > 50 {
            return Ok(result);
        }
    }

    // Fallback: raw WHOIS via TCP port 43 to whois.iana.org
    let result = whois_tcp(&domain, "whois.iana.org").await;
    if result.is_ok() {
        return result;
    }
    let result2 = whois_tcp(&domain, "whois.verisign-grs.com").await;
    if result2.is_ok() {
        return result2;
    }
    Ok(format!("WHOIS unavailable for '{}'. Try installing the 'whois' system tool.", domain))
}

async fn whois_tcp(query: &str, server: &str) -> Result<String, String> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpStream;
    use tokio::time::{timeout, Duration};

    let addr = format!("{}:43", server);
    let mut stream = timeout(Duration::from_secs(8), TcpStream::connect(&addr))
        .await
        .map_err(|_| "Connection timeout")?
        .map_err(|e| e.to_string())?;

    stream.write_all(format!("{}\r\n", query).as_bytes())
        .await.map_err(|e| e.to_string())?;

    let mut buf = Vec::new();
    timeout(Duration::from_secs(8), stream.read_to_end(&mut buf))
        .await
        .map_err(|_| "Read timeout")?
        .map_err(|e| e.to_string())?;

    Ok(String::from_utf8_lossy(&buf).to_string())
}

// ─── Local Network Scan ───────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct DeviceInfo {
    pub ip:       String,
    pub mac:      String,
    pub hostname: String,
    pub vendor:   String,
}

#[tauri::command]
pub fn scan_local_network() -> Result<Vec<DeviceInfo>, String> {
    // Auto-detect gateway subnet
    let subnet = detect_local_subnet().unwrap_or_else(|| "192.168.1.0/24".to_string());

    let out = Command::new("nmap")
        .args(["-sn", &subnet])
        .output()
        .map_err(|e| format!("nmap failed: {}. Is nmap installed?", e))?;

    if !out.status.success() && out.stdout.is_empty() {
        return Err(String::from_utf8_lossy(&out.stderr).to_string());
    }

    Ok(parse_nmap_arp(&String::from_utf8_lossy(&out.stdout)))
}

fn detect_local_subnet() -> Option<String> {
    // Windows: ipconfig | Linux/Mac: ip route
    let out = if cfg!(target_os = "windows") {
        Command::new("powershell")
            .args(["-NoProfile", "-Command",
                "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notmatch '127|169'} | Select-Object -First 1).IPAddress"])
            .output().ok()?
    } else {
        Command::new("ip").args(["route", "get", "8.8.8.8"]).output()
            .or_else(|_| Command::new("route").args(["get", "8.8.8.8"]).output())
            .ok()?
    };

    let stdout = String::from_utf8_lossy(&out.stdout);

    if cfg!(target_os = "windows") {
        let ip = stdout.trim();
        if ip.is_empty() { return None; }
        // Convert "192.168.1.100" → "192.168.1.0/24"
        let parts: Vec<&str> = ip.split('.').collect();
        if parts.len() == 4 {
            return Some(format!("{}.{}.{}.0/24", parts[0], parts[1], parts[2]));
        }
    } else {
        // "192.168.1.100 via ... src 192.168.1.1"
        for line in stdout.lines() {
            if let Some(src_idx) = line.find("src ") {
                let ip = line[src_idx + 4..].split_whitespace().next()?;
                let parts: Vec<&str> = ip.split('.').collect();
                if parts.len() == 4 {
                    return Some(format!("{}.{}.{}.0/24", parts[0], parts[1], parts[2]));
                }
            }
        }
    }
    None
}

fn parse_nmap_arp(output: &str) -> Vec<DeviceInfo> {
    let mut devices = Vec::new();
    let mut current = DeviceInfo {
        ip: String::new(), mac: String::new(),
        hostname: String::new(), vendor: String::new(),
    };

    for line in output.lines() {
        let line = line.trim();

        if line.starts_with("Nmap scan report for") {
            if !current.ip.is_empty() {
                devices.push(std::mem::replace(&mut current, DeviceInfo {
                    ip: String::new(), mac: String::new(),
                    hostname: String::new(), vendor: String::new(),
                }));
            }
            // "Nmap scan report for hostname (ip)" OR "Nmap scan report for ip"
            if let Some(last) = line.split_whitespace().last() {
                let cleaned = last.trim_matches(['(', ')']);
                if cleaned.contains('.') {
                    current.ip = cleaned.to_string();
                    if line.contains('(') {
                        if let Some(h) = line.split("for ").nth(1).and_then(|s| s.split(" (").next()) {
                            current.hostname = h.trim().to_string();
                        }
                    }
                }
            }
        }

        if line.contains("MAC Address:") {
            // "MAC Address: AA:BB:CC:DD:EE:FF (Vendor Name)"
            if let Some(rest) = line.split("MAC Address: ").nth(1) {
                let parts: Vec<&str> = rest.splitn(2, ' ').collect();
                current.mac = parts.first().unwrap_or(&"").to_string();
                if let Some(vendor) = rest.split('(').nth(1).and_then(|s| s.split(')').next()) {
                    current.vendor = vendor.to_string();
                }
            }
        }
    }

    if !current.ip.is_empty() {
        devices.push(current);
    }
    devices
}

// ─── Active Connections ───────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct Connection {
    pub protocol:      String,
    pub local_addr:    String,
    pub remote_addr:   String,
    pub state:         String,
    pub pid:           String,
}

#[tauri::command]
pub fn get_active_connections() -> Result<Vec<Connection>, String> {
    let out = if cfg!(target_os = "windows") {
        Command::new("netstat").args(["-ano"]).output()
    } else {
        Command::new("ss").args(["-tunap"])
            .output()
            .or_else(|_| Command::new("netstat").args(["-tunap"]).output())
    };

    let out = out.map_err(|e| format!("netstat failed: {}", e))?;
    let stdout = String::from_utf8_lossy(&out.stdout);
    Ok(parse_netstat(&stdout, cfg!(target_os = "windows")))
}

fn parse_netstat(output: &str, is_windows: bool) -> Vec<Connection> {
    let mut conns = Vec::new();

    for line in output.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with("Proto") || line.starts_with("Active")
            || line.starts_with("Netid") || line.starts_with("State") { continue; }

        let parts: Vec<&str> = line.split_whitespace().collect();

        if is_windows && parts.len() >= 4 {
            // TCP  0.0.0.0:80  0.0.0.0:0  LISTENING  1234
            conns.push(Connection {
                protocol:    parts[0].to_string(),
                local_addr:  parts.get(1).unwrap_or(&"").to_string(),
                remote_addr: parts.get(2).unwrap_or(&"").to_string(),
                state:       parts.get(3).unwrap_or(&"").to_string(),
                pid:         parts.get(4).unwrap_or(&"—").to_string(),
            });
        } else if !is_windows && parts.len() >= 4 {
            // ss: Netid State Local Remote
            let proto = parts[0].to_string();
            let state = parts[1].to_string();
            let local = parts.get(4).or(parts.get(3)).unwrap_or(&"").to_string();
            let remote = parts.get(5).or(parts.get(4)).unwrap_or(&"").to_string();
            conns.push(Connection {
                protocol: proto, local_addr: local,
                remote_addr: remote, state, pid: String::new(),
            });
        }
    }
    conns
}

// ─── Network Interfaces ───────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct NetworkInterface {
    pub name:       String,
    pub ip_v4:      String,
    pub ip_v6:      String,
    pub mac:        String,
    pub status:     String,
    pub speed_mbps: String,
}

#[tauri::command]
pub fn get_network_interfaces() -> Result<Vec<NetworkInterface>, String> {
    if cfg!(target_os = "windows") {
        let out = Command::new("powershell")
            .args(["-NoProfile", "-Command",
                "Get-NetAdapter | ForEach-Object { $a = $_; $ip = (Get-NetIPAddress -InterfaceIndex $_.InterfaceIndex -ErrorAction SilentlyContinue); [PSCustomObject]@{Name=$a.Name;Status=$a.Status;MacAddress=$a.MacAddress;LinkSpeed=$a.LinkSpeed;IPv4=($ip | Where-Object {$_.AddressFamily -eq 'IPv4'} | Select-Object -ExpandProperty IPAddress -First 1);IPv6=($ip | Where-Object {$_.AddressFamily -eq 'IPv6'} | Select-Object -ExpandProperty IPAddress -First 1)} } | ConvertTo-Json"])
            .output()
            .map_err(|e| e.to_string())?;

        let json_str = String::from_utf8_lossy(&out.stdout);
        let parsed: serde_json::Value = serde_json::from_str(&json_str)
            .unwrap_or(serde_json::Value::Array(vec![]));

        let items = match parsed {
            serde_json::Value::Array(a) => a,
            single => vec![single],
        };

        Ok(items.iter().map(|i| NetworkInterface {
            name:       i["Name"].as_str().unwrap_or("").to_string(),
            ip_v4:      i["IPv4"].as_str().unwrap_or("—").to_string(),
            ip_v6:      i["IPv6"].as_str().unwrap_or("—").to_string(),
            mac:        i["MacAddress"].as_str().unwrap_or("—").to_string(),
            status:     i["Status"].as_str().unwrap_or("Unknown").to_string(),
            speed_mbps: i["LinkSpeed"].as_str().unwrap_or("—").to_string(),
        }).collect())
    } else {
        let out = Command::new("ip").args(["addr"]).output()
            .map_err(|e| e.to_string())?;
        let stdout = String::from_utf8_lossy(&out.stdout);
        Ok(parse_ip_addr(&stdout))
    }
}

fn parse_ip_addr(output: &str) -> Vec<NetworkInterface> {
    let mut interfaces = Vec::new();
    let mut current = NetworkInterface {
        name: String::new(), ip_v4: "—".into(), ip_v6: "—".into(),
        mac: "—".into(), status: "—".into(), speed_mbps: "—".into(),
    };

    for line in output.lines() {
        let line = line.trim();
        if line.starts_with(|c: char| c.is_ascii_digit()) {
            if !current.name.is_empty() {
                interfaces.push(std::mem::replace(&mut current, NetworkInterface {
                    name: String::new(), ip_v4: "—".into(), ip_v6: "—".into(),
                    mac: "—".into(), status: "—".into(), speed_mbps: "—".into(),
                }));
            }
            // "2: eth0: <BROADCAST,MULTICAST,UP> ..."
            if let Some(name) = line.split(':').nth(1) {
                current.name = name.trim().to_string();
            }
            if line.contains("UP") { current.status = "Up".into(); }
            else { current.status = "Down".into(); }
        }
        if line.starts_with("link/ether") {
            if let Some(mac) = line.split_whitespace().nth(1) {
                current.mac = mac.to_string();
            }
        }
        if line.starts_with("inet ") && !line.starts_with("inet6") {
            if let Some(ip) = line.split_whitespace().nth(1) {
                current.ip_v4 = ip.split('/').next().unwrap_or(ip).to_string();
            }
        }
        if line.starts_with("inet6 ") {
            if let Some(ip) = line.split_whitespace().nth(1) {
                if !ip.starts_with("fe80") {
                    current.ip_v6 = ip.split('/').next().unwrap_or(ip).to_string();
                }
            }
        }
    }

    if !current.name.is_empty() {
        interfaces.push(current);
    }
    interfaces
}

// ─── SSL Certificate ──────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct SslCertInfo {
    pub host:        String,
    pub valid:       bool,
    pub subject:     String,
    pub issuer:      String,
    pub not_before:  String,
    pub not_after:   String,
    pub days_left:   i64,
    pub san:         Vec<String>,
    pub version:     String,
}

#[tauri::command]
pub async fn check_ssl_cert(host: String) -> Result<SslCertInfo, String> {
    validate_host(&host)?;

    // Use openssl s_client to fetch cert info
    let out = Command::new("powershell")
        .args(["-NoProfile", "-Command", &format!(
            "$tcp = New-Object System.Net.Sockets.TcpClient('{}', 443); \
             $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream()); \
             $ssl.AuthenticateAsClient('{}'); \
             $cert = $ssl.RemoteCertificate; \
             [PSCustomObject]@{{Subject=$cert.Subject;Issuer=$cert.Issuer;NotBefore=$cert.NotBefore.ToString('o');NotAfter=$cert.NotAfter.ToString('o');Version=$cert.Version}} | ConvertTo-Json; \
             $ssl.Close(); $tcp.Close()", host, host)])
        .output()
        .or_else(|_| {
            // Linux fallback
            Command::new("bash")
                .args(["-c", &format!(
                    "echo | openssl s_client -connect {}:443 -servername {} 2>/dev/null | openssl x509 -text -noout 2>/dev/null",
                    host, host)])
                .output()
        })
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&out.stdout).to_string();

    if stdout.trim().is_empty() {
        return Err("Could not retrieve SSL certificate. Ensure host is reachable on port 443.".into());
    }

    // Try JSON parse (Windows)
    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&stdout) {
        let not_after_str = json["NotAfter"].as_str().unwrap_or("").to_string();
        let days_left = compute_days_left(&not_after_str);

        return Ok(SslCertInfo {
            host:       host.clone(),
            valid:      days_left > 0,
            subject:    json["Subject"].as_str().unwrap_or("").to_string(),
            issuer:     json["Issuer"].as_str().unwrap_or("").to_string(),
            not_before: json["NotBefore"].as_str().unwrap_or("").to_string(),
            not_after:  not_after_str,
            days_left,
            san:        vec![],
            version:    json["Version"].as_str().unwrap_or("").to_string(),
        });
    }

    // Parse openssl text output (Linux)
    let subject  = extract_ssl_field(&stdout, "Subject:");
    let issuer   = extract_ssl_field(&stdout, "Issuer:");
    let not_before = extract_ssl_field(&stdout, "Not Before:");
    let not_after  = extract_ssl_field(&stdout, "Not After :");
    let days_left  = compute_days_left(&not_after);
    let san = extract_san(&stdout);

    Ok(SslCertInfo {
        host, valid: days_left > 0, subject, issuer,
        not_before, not_after, days_left, san, version: String::new(),
    })
}

fn extract_ssl_field(text: &str, label: &str) -> String {
    text.lines()
        .find(|l| l.contains(label))
        .and_then(|l| l.split(label).nth(1))
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

fn extract_san(text: &str) -> Vec<String> {
    text.lines()
        .find(|l| l.contains("DNS:"))
        .map(|l| l.split(',').map(|s| s.trim().trim_start_matches("DNS:").to_string()).collect())
        .unwrap_or_default()
}

fn compute_days_left(date_str: &str) -> i64 {
    // Try ISO 8601 (PowerShell) and OpenSSL formats
    // We'll do a simple approximation: parse year/month/day
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;

    // Try to find a year 20XX in the string
    if let Some(year_pos) = date_str.find("20") {
        let year_str = &date_str[year_pos..year_pos + 4];
        if let Ok(year) = year_str.parse::<i64>() {
            // Very rough: use year boundary
            let approx_expiry = (year - 1970) * 365 * 86400;
            return (approx_expiry - now) / 86400;
        }
    }
    -1
}

// ─── HTTP Headers ─────────────────────────────────────────────────────────────

#[derive(Serialize)]
pub struct HttpHeaderResult {
    pub url:         String,
    pub status:      u16,
    pub status_text: String,
    pub headers:     Vec<(String, String)>,
}

#[tauri::command]
pub async fn get_http_headers(url: String) -> Result<HttpHeaderResult, String> {
    if !url.starts_with("http://") && !url.starts_with("https://") {
        return Err("URL must start with http:// or https://".into());
    }

    let client = reqwest::Client::builder()
        .redirect(reqwest::redirect::Policy::none())
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| e.to_string())?;

    let res = match client.head(&url).send().await {
        Ok(r) => r,
        Err(_) => client.get(&url).send().await
            .map_err(|e| format!("Request failed: {}", e))?,
    };

    let status = res.status().as_u16();
    let status_text = res.status().canonical_reason().unwrap_or("").to_string();
    let headers: Vec<(String, String)> = res.headers().iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
        .collect();

    Ok(HttpHeaderResult { url, status, status_text, headers })
}
