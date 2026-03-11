// Prevents a console window from opening on Windows in release builds
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use commands::{network, security, system};

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            // System
            system::get_system_stats,
            system::list_processes,
            system::kill_process,
            system::run_script,
            // Security
            security::nmap_scan,
            security::check_ip_reputation,
            security::get_open_ports,
            security::analyze_processes,
            security::check_dns_leak,
            security::get_vpn_status,
            // Network
            network::ping_host,
            network::traceroute,
            network::dns_lookup,
            network::whois_lookup,
            network::scan_local_network,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running T");
}
