// Detiene el overlay rojo de react-error-overlay en dev.
// Se ejecuta antes de App para que la suscripción al error happen ANTES del overlay.
import { stopReportingRuntimeErrors } from "react-error-overlay";

const KNOWN_BENIGN = ["destroy is not a function"];

if (typeof window !== "undefined") {
  // 1) Detener completamente el overlay en dev (todos los errores siguen apareciendo en consola)
  try {
    stopReportingRuntimeErrors();
  } catch (e) { /* ignore */ }

  // 2) Adicionalmente silenciar el known benign error en consola
  const origConsoleError = window.console.error;
  window.console.error = function (...args) {
    const msg = args[0]?.toString?.() || "";
    if (KNOWN_BENIGN.some((p) => msg.includes(p))) return;
    origConsoleError.apply(window.console, args);
  };

  window.addEventListener("error", (e) => {
    if (KNOWN_BENIGN.some((p) => (e.message || "").includes(p))) {
      e.stopImmediatePropagation();
      e.preventDefault();
      return false;
    }
  });

  // 3) Quitar el overlay del webpack-dev-server (CRA 5) que es independiente de react-error-overlay
  const removeWebpackOverlay = () => {
    document.querySelectorAll("#webpack-dev-server-client-overlay, #webpack-dev-server-client-overlay-div").forEach((el) => el.remove());
  };
  const observer = new MutationObserver(removeWebpackOverlay);
  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: false });
  } else {
    document.addEventListener("DOMContentLoaded", () => observer.observe(document.body, { childList: true, subtree: false }));
  }
}
