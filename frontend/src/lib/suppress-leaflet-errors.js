// Suprime el overlay rojo de runtime errors no críticos en dev.
// Solo aplica a errores conocidos de react-leaflet con React 19.
if (typeof window !== "undefined" && process.env.NODE_ENV !== "production") {
  const KNOWN_BENIGN = ["destroy is not a function"];

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

  window.addEventListener("unhandledrejection", (e) => {
    const msg = e.reason?.message || "";
    if (KNOWN_BENIGN.some((p) => msg.includes(p))) {
      e.preventDefault();
    }
  });
}
