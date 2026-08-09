import { useEffect, useState } from "react";
import { useTStore } from "../../store";

interface ProviderStatus {
  id: string;
  name: string;
  configured: boolean;
  maskedKey: string;
}

export function ModelDashboard() {
  const {
    providerHealth,
    activeModel,
    activeProvider,
    routingReason,
    localPreferred,
    setLocalPreferred,
    setProviderHealth,
  } = useTStore();

  const [providers, setProviders] = useState<ProviderStatus[]>([
    { id: "grok", name: "Grok", configured: false, maskedKey: "" },
    { id: "gemini", name: "Gemini", configured: false, maskedKey: "" },
    { id: "groq", name: "Groq", configured: false, maskedKey: "" },
    { id: "cerebras", name: "Cerebras", configured: false, maskedKey: "" },
    { id: "openrouter", name: "OpenRouter", configured: false, maskedKey: "" },
    { id: "github", name: "GitHub", configured: false, maskedKey: "" },
    { id: "ollama", name: "Ollama", configured: true, maskedKey: "http://localhost:11434" },
  ]);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:7891/api/v1/models/status");
      if (res.ok) {
        const data = await res.json();
        if (data.providers) setProviders(data.providers);
        if (data.health) setProviderHealth(data.health);
        if (data.localPreferred !== undefined) setLocalPreferred(data.localPreferred);
      }
    } catch (e) {
      console.warn("Could not fetch model status from Brain REST API:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const toggleLocalPreferred = async () => {
    const nextVal = !localPreferred;
    setLocalPreferred(nextVal);
    try {
      await fetch("http://127.0.0.1:7891/api/v1/models/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ localPreferred: nextVal }),
      });
      fetchStatus();
    } catch (e) {
      console.warn("Failed to update local preferred setting:", e);
    }
  };

  const renderStatusBadge = (provId: string, isConfigured: boolean) => {
    const health = providerHealth[provId];
    if (!health) {
      return isConfigured ? (
        <span style={{ color: "#00ffcc", fontWeight: "bold" }}>● Available</span>
      ) : (
        <span style={{ color: "rgba(160,170,176,0.5)" }}>○ Not Configured</span>
      );
    }

    if (health.rateLimited || health.quotaStatus === "rate_limited") {
      return <span style={{ color: "#ffaa00", fontWeight: "bold" }}>◐ Rate Limited</span>;
    }
    if (health.quotaStatus === "quota_exceeded") {
      return <span style={{ color: "#ffaa00", fontWeight: "bold" }}>◐ Quota Exceeded</span>;
    }
    if (health.temporarilyUnavailable || health.quotaStatus === "unavailable") {
      return <span style={{ color: "#ff0033", fontWeight: "bold" }}>× Unavailable</span>;
    }
    if (health.quotaStatus === "not_configured" || !isConfigured) {
      return <span style={{ color: "rgba(160,170,176,0.5)" }}>○ Not Configured</span>;
    }

    return <span style={{ color: "#00ffcc", fontWeight: "bold" }}>● Available</span>;
  };

  return (
    <div className="ultron-panel ultron-corner-brackets" style={{ padding: 24, borderRadius: 2 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ fontSize: 12, letterSpacing: 3, color: "#ff0033", fontWeight: 700, fontFamily: "var(--font-header)" }}>
          MODEL SYSTEM & INTELLIGENT ROUTER
        </div>
        <button
          onClick={fetchStatus}
          disabled={loading}
          className="ultron-btn"
          style={{ fontSize: 10, padding: "4px 10px" }}
        >
          {loading ? "REFRESHING..." : "↻ REFRESH STATUS"}
        </button>
      </div>

      {/* Provider Status Table */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
        {providers.map((p) => {
          const health = providerHealth[p.id];
          return (
            <div
              key={p.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 12px",
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(255,0,51,0.12)",
                borderRadius: 2,
                fontFamily: "var(--font-mono)",
                fontSize: 12,
              }}
            >
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <span style={{ fontWeight: 700, color: "#ffffff", width: 100 }}>{p.name}</span>
                {p.maskedKey && (
                  <span style={{ fontSize: 10, color: "rgba(160,170,176,0.5)" }}>Key: {p.maskedKey}</span>
                )}
                {health?.missingModels && health.missingModels.length > 0 && (
                  <span style={{ fontSize: 10, color: "#ffaa00" }}>
                    Missing model: {health.missingModels.join(", ")}
                  </span>
                )}
              </div>
              <div>{renderStatusBadge(p.id, p.configured)}</div>
            </div>
          );
        })}
      </div>

      {/* Routing Metadata Box */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 12,
          padding: 14,
          background: "rgba(10,8,15,0.9)",
          border: "1px solid rgba(255,0,51,0.25)",
          borderRadius: 2,
          marginBottom: 16,
          fontFamily: "var(--font-mono)",
        }}
      >
        <div>
          <div style={{ fontSize: 9, color: "rgba(160,170,176,0.6)", letterSpacing: 2 }}>ACTIVE MODEL</div>
          <div style={{ fontSize: 13, color: "#00ffcc", fontWeight: 700, marginTop: 4 }}>
            {activeModel || "Grok-2 Latest"}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 9, color: "rgba(160,170,176,0.6)", letterSpacing: 2 }}>ACTIVE PROVIDER</div>
          <div style={{ fontSize: 13, color: "#ffffff", fontWeight: 700, marginTop: 4, textTransform: "capitalize" }}>
            {activeProvider || "xAI / Grok"}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 9, color: "rgba(160,170,176,0.6)", letterSpacing: 2 }}>ROUTING REASON</div>
          <div style={{ fontSize: 11, color: "#ff3355", marginTop: 4 }}>
            {routingReason || "Autonomous Provider Selection"}
          </div>
        </div>
      </div>

      {/* Preferences Toggle */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 8 }}>
        <div>
          <div style={{ fontSize: 11, color: "#ffffff", fontWeight: 700, fontFamily: "var(--font-tech)" }}>
            LOCAL-FIRST PREFERENCE
          </div>
          <div style={{ fontSize: 9, color: "rgba(160,170,176,0.6)", fontFamily: "var(--font-mono)" }}>
            Prefer Ollama local models first before routing to cloud providers
          </div>
        </div>
        <button
          onClick={toggleLocalPreferred}
          className={`ultron-btn ${localPreferred ? "ultron-btn-active" : ""}`}
          style={{ padding: "6px 16px" }}
        >
          {localPreferred ? "LOCAL FIRST ON" : "LOCAL FIRST OFF"}
        </button>
      </div>
    </div>
  );
}
