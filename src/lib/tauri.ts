const isTauri = () => "__TAURI_INTERNALS__" in window;

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (isTauri()) {
    const { invoke: tauriInvoke } = await import("@tauri-apps/api/core");
    return tauriInvoke<T>(cmd, args);
  }
  return mockInvoke<T>(cmd, args);
}

// ─── System ───────────────────────────────────────────────────────────────────

export interface SystemStatsResult {
  cpu_percent:  number;
  ram_percent:  number;
  disk_percent: number;
  uptime_secs:  number;
  net_rx_kbps:  number;
  net_tx_kbps:  number;
}

export const getSystemStats  = () => invoke<SystemStatsResult>("get_system_stats");
export const listProcesses   = () => invoke<{ pid: number; name: string; cpu: number; mem_mb: number }[]>("list_processes");
export const killProcess     = (pid: number) => invoke<void>("kill_process", { pid });
export const runScript       = (script: string, shell: "bash" | "powershell" | "python") => invoke<string>("run_script", { script, shell });

// ─── File Manager ─────────────────────────────────────────────────────────────

export interface FileEntry {
  name:     string;
  path:     string;
  is_dir:   boolean;
  size_kb:  number;
  modified: number;
}

export interface SearchResult {
  path:   string;
  name:   string;
  is_dir: boolean;
}

export const listDirectory   = (path: string)                  => invoke<FileEntry[]>("list_directory", { path });
export const readFile        = (path: string)                  => invoke<string>("read_file", { path });
export const writeFile       = (path: string, content: string) => invoke<void>("write_file", { path, content });
export const deletePath      = (path: string)                  => invoke<void>("delete_path", { path });
export const renamePath      = (from: string, to: string)      => invoke<void>("rename_path", { from, to });
export const createDirectory = (path: string)                  => invoke<void>("create_directory", { path });
export const searchFiles     = (root: string, query: string)   => invoke<SearchResult[]>("search_files", { root, query });
export const getHomeDir      = ()                              => invoke<string>("get_home_dir");
export const launchApp       = (name: string)                  => invoke<string>("launch_app", { name });
export const getClipboard    = ()                              => invoke<string>("get_clipboard");
export const setClipboard    = (content: string)               => invoke<void>("set_clipboard", { content });

// ─── Security ─────────────────────────────────────────────────────────────────

export interface NmapResult {
  host:     string;
  ports:    { port: number; state: string; service: string; version: string }[];
  os_guess: string;
}

export const nmapScan           = (target: string, flags: string) => invoke<NmapResult>("nmap_scan", { target, flags });
export const getOpenPorts       = (host: string) => invoke<{ port: number; service: string }[]>("get_open_ports", { host });
export const analyzeProcesses   = () => invoke<{ pid: number; name: string; suspicion: "clean" | "suspicious" | "critical"; reason: string }[]>("analyze_processes");
export const checkDnsLeak       = () => invoke<{ leaking: boolean; servers: string[] }>("check_dns_leak");
export const getVpnStatus       = () => invoke<{ connected: boolean; provider: string; ip: string; location: string }>("get_vpn_status");

// ─── Network ──────────────────────────────────────────────────────────────────

// ─── Network Commands ────────────────────────────────────────────────────────

export interface PingResult {
  host: string; avg_ms: number; min_ms: number; max_ms: number;
  packet_loss: number; packets_sent: number;
}
export interface HopInfo {
  hop: number; host: string; ip: string; ms: number; timeout: boolean;
}
export interface DnsResult {
  a: string[]; aaaa: string[]; mx: string[]; ns: string[]; txt: string[]; cname: string[];
}
export interface DeviceInfo {
  ip: string; mac: string; hostname: string; vendor: string;
}
export interface Connection {
  protocol: string; local_addr: string; remote_addr: string; state: string; pid: string;
}
export interface NetworkInterface {
  name: string; ip_v4: string; ip_v6: string; mac: string; status: string; speed_mbps: string;
}
export interface SslCertInfo {
  host: string; valid: boolean; subject: string; issuer: string;
  not_before: string; not_after: string; days_left: number; san: string[]; version: string;
}
export interface HttpHeaderResult {
  url: string; status: number; status_text: string; headers: [string, string][];
}

export const pingHost             = (host: string, count?: number) => invoke<PingResult>("ping_host", { host, count: count ?? 4 });
export const traceroute           = (host: string) => invoke<HopInfo[]>("traceroute", { host });
export const dnsLookup            = (domain: string) => invoke<DnsResult>("dns_lookup", { domain });
export const whoisLookup          = (domain: string) => invoke<string>("whois_lookup", { domain });
export const scanLocalNetwork     = () => invoke<DeviceInfo[]>("scan_local_network");
export const getActiveConnections = () => invoke<Connection[]>("get_active_connections");
export const getNetworkInterfaces = () => invoke<NetworkInterface[]>("get_network_interfaces");
export const checkSslCert         = (host: string) => invoke<SslCertInfo>("check_ssl_cert", { host });
export const getHttpHeaders       = (url: string) => invoke<HttpHeaderResult>("get_http_headers", { url });

// ─── Memory ───────────────────────────────────────────────────────────────────

export interface StoredMessage {
  id:        number;
  role:      "user" | "assistant";
  content:   string;
  timestamp: number;
}

export interface MemoryEntry {
  key:     string;
  value:   string;
  updated: number;
}

export interface ProfileEntry {
  key:   string;
  value: string;
}

export interface Task {
  id:         number;
  title:      string;
  detail:     string;
  status:     "open" | "done";
  created_at: number;
}

export interface ScheduledTask {
  id:          number;
  label:       string;
  command:     string;
  shell:       string;
  run_at:      number;
  repeat_secs: number;
  last_ran:    number;
  enabled:     boolean;
}

export interface ClipboardEntry {
  id:       number;
  content:  string;
  saved_at: number;
}

export const saveMessage           = (role: string, content: string, timestamp: number) => invoke<void>("save_message", { role, content, timestamp });
export const loadRecentMessages    = (limit: number) => invoke<StoredMessage[]>("load_recent_messages", { limit });
export const clearMessages         = () => invoke<void>("clear_messages");
export const setMemory             = (key: string, value: string) => invoke<void>("set_memory", { key, value });
export const getAllMemories         = () => invoke<MemoryEntry[]>("get_all_memories");
export const deleteMemory          = (key: string) => invoke<void>("delete_memory", { key });
export const setProfile            = (key: string, value: string) => invoke<void>("set_profile", { key, value });
export const getProfile            = () => invoke<ProfileEntry[]>("get_profile");
export const addTask               = (title: string, detail: string) => invoke<number>("add_task", { title, detail });
export const getTasks              = (statusFilter?: string) => invoke<Task[]>("get_tasks", { status_filter: statusFilter ?? null });
export const completeTask          = (id: number) => invoke<void>("complete_task", { id });
export const deleteTask            = (id: number) => invoke<void>("delete_task", { id });
export const addScheduledTask      = (label: string, command: string, shell: string, run_at: number, repeat_secs: number) => invoke<number>("add_scheduled_task", { label, command, shell, run_at, repeat_secs });
export const getScheduledTasks     = () => invoke<ScheduledTask[]>("get_scheduled_tasks");
export const deleteScheduledTask   = (id: number) => invoke<void>("delete_scheduled_task", { id });
export const toggleScheduledTask   = (id: number, enabled: boolean) => invoke<void>("toggle_scheduled_task", { id, enabled });
export const saveClipboardEntry    = (content: string) => invoke<void>("save_clipboard_entry", { content });
export const getClipboardHistory   = () => invoke<ClipboardEntry[]>("get_clipboard_history");
export const clearClipboardHistory = () => invoke<void>("clear_clipboard_history");


// ─── Phase 4 Security ─────────────────────────────────────────────────────────

export interface FirewallRule {
  name:      string;
  direction: string;
  action:    string;
  enabled:   boolean;
  protocol:  string;
  port:      string;
}

export interface PasswordStrength {
  score:    number;
  label:    string;
  feedback: string[];
  entropy:  number;
}

export interface UrlSafetyResult {
  url:    string;
  safe:   boolean;
  detail: string;
}

export interface SecurityEvent {
  time:    string;
  level:   string;
  source:  string;
  message: string;
}

export const getFirewallRules       = ()                                          => invoke<FirewallRule[]>("get_firewall_rules");
export const checkPasswordStrength  = (password: string)                          => invoke<PasswordStrength>("check_password_strength", { password });
export const checkUrlSafety         = (url: string, virustotal_key: string)       => invoke<UrlSafetyResult>("check_url_safety", { url, virustotal_key });
export const getSecurityLog         = ()                                          => invoke<SecurityEvent[]>("get_security_log");
// check_ip_reputation now requires api_key param
export const checkIpReputationV2    = (ip: string, api_key: string)               => invoke<{ ip: string; reputation: string; detail: string }>("check_ip_reputation", { ip, api_key });

// ─── Browser Stubs ────────────────────────────────────────────────────────────

function mockInvoke<T>(cmd: string, _args?: Record<string, unknown>): T {
  const mocks: Record<string, unknown> = {
    // System
    get_system_stats:    { cpu_percent: 42, ram_percent: 61, disk_percent: 54, uptime_secs: 86400, net_rx_kbps: 128, net_tx_kbps: 44 },
    list_processes:      [{ pid: 1234, name: "mock.exe", cpu: 2.1, mem_mb: 48 }],
    run_script:          "mock output",
    // File Manager
    list_directory:      [{ name: "Documents", path: "C:/Users/mock/Documents", is_dir: true, size_kb: 0, modified: 1700000000 }],
    read_file:           "mock file content",
    write_file:          null,
    delete_path:         null,
    rename_path:         null,
    create_directory:    null,
    search_files:        [{ path: "C:/mock/file.txt", name: "file.txt", is_dir: false }],
    get_home_dir:        "C:/Users/mock",
    launch_app:          "Launched: mock",
    get_clipboard:       "mock clipboard text",
    set_clipboard:       null,
    // Security
    nmap_scan:           { host: "mock", ports: [{ port: 80, state: "open", service: "http", version: "nginx 1.18" }], os_guess: "Windows 10" },
    check_ip_reputation: { ip: "1.2.3.4", reputation: "clean", detail: "No threats detected (mock)" },
    get_open_ports:      [{ port: 80, service: "HTTP" }, { port: 443, service: "HTTPS" }],
    analyze_processes:   [],
    check_dns_leak:      { leaking: false, servers: ["8.8.8.8", "8.8.4.4"] },
    get_vpn_status:      { connected: false, provider: "", ip: "203.0.113.1", location: "Karachi, Pakistan" },
    // Network
    ping_host:           { host: "mock", avg_ms: 14, packet_loss: 0 },
    traceroute:          [{ hop: 1, host: "192.168.1.1", ms: 2 }, { hop: 2, host: "10.0.0.1", ms: 8 }],
    dns_lookup:          { a: ["93.184.216.34"], mx: ["mail.example.com"], ns: ["ns1.example.com"] },
    whois_lookup:        "Domain: mock.example\nRegistrar: Mock Registrar\nCreated: 2020-01-01",
    scan_local_network:  [{ ip: "192.168.1.1", mac: "AA:BB:CC:DD:EE:FF", hostname: "router", vendor: "Cisco" }],
    // Memory
    save_message:          null, clear_messages:       null,
    load_recent_messages:  [],   get_all_memories:     [],
    set_memory:            null, delete_memory:        null,
    set_profile:           null, get_profile:          [],
    add_task:              1,    get_tasks:            [],
    complete_task:         null, delete_task:          null,
    add_scheduled_task:    1,    get_scheduled_tasks:  [],
    delete_scheduled_task: null, toggle_scheduled_task: null,
    save_clipboard_entry:  null, get_clipboard_history: [],
    clear_clipboard_history: null,
    // Phase 4 security
    get_firewall_rules:       [{ name: "Allow HTTP", direction: "Inbound", action: "Allow", enabled: true, protocol: "TCP", port: "80" }],
    check_password_strength:  { score: 3, label: "Strong", feedback: [], entropy: 60.5 },
    check_url_safety:         { url: "mock", safe: true, detail: "Malicious: 0 | Suspicious: 0 | Clean: 72 (mock)" },
    get_security_log:         [{ time: "2026-01-01", level: "Info", source: "Security", message: "Mock event" }],
    // Phase 5 security
    ip_intel:                 { ip: "1.1.1.1", hostname: "one.one.one.one", country: "Australia", region: "Queensland", city: "Brisbane", org: "AS13335 Cloudflare", asn: "AS13335", isp: "Cloudflare", latitude: -27.47, longitude: 153.02, abuse_score: 0, abuse_detail: "No reports (mock)", open_ports: [80, 443] },
    email_osint:              { email: "mock@example.com", valid: true, domain: "example.com", mx_records: ["mail.example.com"], gravatar_url: null, breaches: [], breach_count: 0, paste_count: 0 },
    cve_search:               [],
    full_port_scan:           { host: "mock", open: [{ port: 80, service: "HTTP" }, { port: 443, service: "HTTPS" }], scanned: 1024, duration_ms: 1200 },
    // Network
    get_active_connections:   [{ protocol: "TCP", local_addr: "127.0.0.1:3000", remote_addr: "0.0.0.0:0", state: "LISTEN", pid: "1234" }],
    get_network_interfaces:   [{ name: "Ethernet", ip_v4: "192.168.1.100", ip_v6: "", mac: "AA:BB:CC:DD:EE:FF", status: "up", speed_mbps: "1000" }],
    check_ssl_cert:           { host: "mock", valid: true, subject: "CN=mock.com", issuer: "Let's Encrypt", not_before: "2026-01-01", not_after: "2026-04-01", days_left: 21, san: ["mock.com"], version: "TLSv1.3" },
    get_http_headers:         { url: "https://mock.com", status: 200, status_text: "OK", headers: [["content-type", "text/html"], ["server", "nginx"]] },
  };
  return (mocks[cmd] ?? null) as T;
}

// ─── IP Intel ─────────────────────────────────────────────────────────────────

export interface IpIntelResult {
  ip:           string;
  hostname:     string;
  country:      string;
  region:       string;
  city:         string;
  org:          string;
  asn:          string;
  isp:          string;
  latitude:     number;
  longitude:    number;
  abuse_score:  number;
  abuse_detail: string;
  open_ports:   number[];
}

export const ipIntel = (ip: string, abuse_key: string) =>
  invoke<IpIntelResult>("ip_intel", { ip, abuse_key });

// ─── Email OSINT ──────────────────────────────────────────────────────────────

export interface BreachEntry {
  name:         string;
  domain:       string;
  breach_date:  string;
  description:  string;
  data_classes: string[];
  pwn_count:    number;
}

export interface EmailOsintResult {
  email:        string;
  valid:        boolean;
  domain:       string;
  mx_records:   string[];
  gravatar_url: string | null;
  breaches:     BreachEntry[];
  breach_count: number;
  paste_count:  number;
}

export const emailOsint = (email: string, hibp_key: string) =>
  invoke<EmailOsintResult>("email_osint", { email, hibp_key });

// ─── CVE Search ───────────────────────────────────────────────────────────────

export interface PortEntry {
  port:    number;
  service: string;
}

export interface FullScanResult {
  host:        string;
  open:        PortEntry[];
  scanned:     number;
  duration_ms: number;
}

export const fullPortScan = (host: string, start_port: number, end_port: number) =>
  invoke<FullScanResult>("full_port_scan", { host, start_port, end_port });

export interface CveEntry {
  id:          string;
  description: string;
  severity:    string;
  cvss_score:  number;
  published:   string;
  references:  string[];
}

export const cveSearch = (query: string) =>
  invoke<CveEntry[]>("cve_search", { query });

