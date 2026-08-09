"""
Centralized Configuration System for T AI Operating System.
Provides strongly-typed system settings, environment variable parsing,
feature flags, security policy toggles, and model selection.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelConfig:
    provider: str = os.getenv("LLM_PROVIDER", "grok")
    model_name: str = os.getenv("LLM_MODEL", "grok-2-latest")
    api_key: Optional[str] = os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    endpoint: Optional[str] = os.getenv("LLM_ENDPOINT", None)

    # Multi-provider credentials
    xai_api_key: Optional[str] = os.getenv("XAI_API_KEY")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    cerebras_api_key: Optional[str] = os.getenv("CEREBRAS_API_KEY")
    openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    github_api_key: Optional[str] = os.getenv("GITHUB_MODELS_API_KEY", os.getenv("GITHUB_TOKEN"))
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Routing settings
    local_preferred: bool = os.getenv("LOCAL_PREFERRED", "false").lower() == "true"
    fallback_order: list[str] = field(default_factory=lambda: [
        "grok", "gemini", "groq", "cerebras", "openrouter", "github", "ollama"
    ])
    local_default_model: str = os.getenv("LOCAL_DEFAULT_MODEL", "qwen3:14b")
    local_reasoning_model: str = os.getenv("LOCAL_REASONING_MODEL", "qwen3:30b")
    cooldown_seconds: float = float(os.getenv("PROVIDER_COOLDOWN_SECONDS", "60.0"))



@dataclass
class SecurityConfig:
    require_user_confirmation: bool = os.getenv("SECURITY_REQUIRE_CONFIRMATION", "true").lower() == "true"
    allowed_execution_tools: list[str] = field(default_factory=lambda: [
        "file_read", "file_write", "terminal_command", "http_request", "device_control"
    ])
    audit_log_path: str = os.getenv("SECURITY_AUDIT_LOG", "logs/audit.jsonl")
    sandbox_mode: bool = os.getenv("SECURITY_SANDBOX_MODE", "false").lower() == "true"


@dataclass
class NetworkConfig:
    host: str = os.getenv("T_HOST", "127.0.0.1")
    port: int = int(os.getenv("T_PORT", "7891"))
    node_id: str = os.getenv("NODE_ID", "host-primary")
    distributed_peers: list[str] = field(default_factory=lambda: [])


@dataclass
class VoiceConfig:
    stt_provider: str = os.getenv("STT_PROVIDER", "whisper")
    tts_provider: str = os.getenv("TTS_PROVIDER", "kokoro")
    sample_rate: int = int(os.getenv("VOICE_SAMPLE_RATE", "16000"))
    wake_word: str = os.getenv("WAKE_WORD", "T")


@dataclass
class FeatureFlags:
    vision_enabled: bool = True
    hardware_devices_enabled: bool = True
    distributed_networking: bool = True
    autonomous_planning: bool = True
    simulation_mode: bool = True


@dataclass
class SystemConfig:
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    data_dir: str = os.getenv("DATA_DIR", "./data")
    model: ModelConfig = field(default_factory=ModelConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    features: FeatureFlags = field(default_factory=FeatureFlags)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "environment": self.environment,
            "log_level": self.log_level,
            "model": {
                "provider": self.model.provider,
                "model_name": self.model.model_name,
                "temperature": self.model.temperature,
            },
            "security": {
                "require_user_confirmation": self.security.require_user_confirmation,
                "sandbox_mode": self.security.sandbox_mode,
            },
            "network": {
                "host": self.network.host,
                "port": self.network.port,
                "node_id": self.network.node_id,
            },
            "features": {
                "vision": self.features.vision_enabled,
                "hardware": self.features.hardware_devices_enabled,
                "distributed": self.features.distributed_networking,
                "planning": self.features.autonomous_planning,
                "simulation": self.features.simulation_mode,
            }
        }


# Global Singleton Configuration Instance
config = SystemConfig()
