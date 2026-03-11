import { Component, type ReactNode } from "react";

interface State { error: Error | null; }

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div style={{
        width: "100vw", height: "100vh",
        background: "#000409",
        display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center",
        padding: 40, fontFamily: "Courier New, monospace",
        color: "#ff4400",
      }}>
        <div style={{ fontSize: 12, letterSpacing: 6, marginBottom: 20, color: "#ffb300" }}>
          T · RUNTIME ERROR
        </div>
        <div style={{
          fontSize: 11, color: "#ff4400",
          background: "rgba(255,68,0,0.08)",
          border: "1px solid rgba(255,68,0,0.3)",
          borderRadius: 4, padding: 20,
          maxWidth: 700, width: "100%",
          whiteSpace: "pre-wrap", wordBreak: "break-all",
        }}>
          {error.message}
        </div>
        <div style={{
          marginTop: 20, fontSize: 9, color: "rgba(255,179,0,0.4)",
          whiteSpace: "pre-wrap", maxWidth: 700,
        }}>
          {error.stack}
        </div>
      </div>
    );
  }
}
