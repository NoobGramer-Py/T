# T — Personal AI Assistant

J.A.R.V.I.S-inspired personal AI with cybersecurity, system control, and network intelligence.

---

## Prerequisites

| Tool | Install |
|---|---|
| Node.js 18+ | https://nodejs.org |
| Rust | https://rustup.rs |
| Nmap | https://nmap.org/download |
| Ollama (optional) | https://ollama.com |

### Tauri system deps (Linux)
```bash
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

---

## Setup

```bash
# 1. Install frontend dependencies
npm install

# 2. (Optional) Set your Groq API key — get one free at console.groq.com
# Create a .env file at project root:
echo "VITE_GROQ_API_KEY=your_key_here" > .env

# 3. (Optional) Pull an Ollama model for offline AI
ollama pull llama3.2

# 4. Run in development mode
npm run tauri dev

# 5. Build for production
npm run tauri build
```

---

## AI Providers

T auto-selects the best available provider:

| Provider | Speed | Limit | Requires |
|---|---|---|---|
| Groq | Very fast | 14,400 req/day | API key |
| Ollama | Moderate | Unlimited | Local install |

T auto-falls back to Ollama if Groq is unavailable, and vice versa.

---

## Modules

| Module | Hotkey | Description |
|---|---|---|
| CORE (Chat) | Nav `◎` | AI conversation interface |
| SEC | Nav `⬡` | Cybersecurity operations |
| SYS | Nav `⊞` | System monitor & control |
| NET | Nav `⊹` | Network intelligence |

---

## Security Notes

- Script execution always requires user confirmation
- Tool installation requires explicit approval
- All security actions are logged with timestamps
- T runs locally — no data leaves your machine except AI API calls
