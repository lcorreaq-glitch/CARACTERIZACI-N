import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  componentDidCatch(error, info) {
    // Silently log; react-leaflet has known cleanup quirks with React 19 we can ignore
    // eslint-disable-next-line no-console
    console.warn("[ErrorBoundary]", error?.message);
  }
  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="dense-card p-8 text-center text-sm text-muted-foreground">
          Se produjo un error al renderizar este componente. Recargue la página o cambie de pestaña.
        </div>
      );
    }
    return this.props.children;
  }
}
