import { useEffect } from "react";
import { getSystemStats } from "../lib/tauri";
import { useTStore } from "../store";

export function useSystemStats(intervalMs = 2000): void {
  const setStats = useTStore((s) => s.setStats);

  useEffect(() => {
    const poll = async () => {
      try {
        const raw = await getSystemStats();
        setStats({
          cpuPercent:    raw.cpu_percent,
          ramPercent:    raw.ram_percent,
          diskPercent:   raw.disk_percent,
          uptime:        raw.uptime_secs,
          networkRxKbps: raw.net_rx_kbps,
          networkTxKbps: raw.net_tx_kbps,
        });
      } catch {
        // Silently ignore — stats are non-critical
      }
    };

    poll();
    const id = setInterval(poll, intervalMs);
    return () => clearInterval(id);
  }, [setStats, intervalMs]);
}
