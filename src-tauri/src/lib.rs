mod commands;
mod db;

use commands::{memory, network, security, system};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            // System
            system::get_system_stats,
            system::list_processes,
            system::kill_process,
            system::run_script,
            system::list_directory,
            system::read_file,
            system::write_file,
            system::delete_path,
            system::rename_path,
            system::create_directory,
            system::search_files,
            system::get_home_dir,
            system::launch_app,
            system::get_clipboard,
            system::set_clipboard,
            // Security
            security::nmap_scan,
            security::check_ip_reputation,
            security::get_open_ports,
            security::analyze_processes,
            security::check_dns_leak,
            security::get_vpn_status,
            security::get_firewall_rules,
            security::check_password_strength,
            security::check_url_safety,
            security::get_security_log,
            // Network
            network::ping_host,
            network::traceroute,
            network::dns_lookup,
            network::whois_lookup,
            network::scan_local_network,
            network::get_active_connections,
            network::get_network_interfaces,
            network::check_ssl_cert,
            network::get_http_headers,
            // Memory
            memory::save_message,
            memory::load_recent_messages,
            memory::clear_messages,
            memory::set_memory,
            memory::get_all_memories,
            memory::delete_memory,
            memory::set_profile,
            memory::get_profile,
            memory::add_task,
            memory::get_tasks,
            memory::complete_task,
            memory::delete_task,
            memory::add_scheduled_task,
            memory::get_scheduled_tasks,
            memory::delete_scheduled_task,
            memory::toggle_scheduled_task,
            memory::save_clipboard_entry,
            memory::get_clipboard_history,
            memory::clear_clipboard_history,
        ])
        .run(tauri::generate_context!())
        .expect("Error while running T");
}
