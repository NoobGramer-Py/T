import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./ErrorBoundary";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  // StrictMode removed — causes Three.js WebGL double-mount crash in dev
  <React.Fragment>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.Fragment>
);
