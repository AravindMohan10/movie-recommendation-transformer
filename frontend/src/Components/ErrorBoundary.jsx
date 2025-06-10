import React from "react";

export default class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null, errorInfo: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo?.componentStack);
    this.setState({ errorInfo: errorInfo?.componentStack || null });
  }

  render() {
    if (this.state.hasError) {
      const { error, errorInfo } = this.state;
      const msg = error?.message || "Unknown error";
      return (
        <div
          className="min-h-screen flex flex-col items-center justify-center p-6"
          style={{ background: "#0a0a0a", color: "#e5e5e5" }}
        >
          <h1 className="text-xl font-semibold text-teal-300 mb-2">
            Something went wrong
          </h1>
          <p className="text-gray-400 text-sm mb-2 text-center max-w-md">
            The page flickered or crashed. Try refreshing.
          </p>
          <pre className="text-left text-xs text-red-300/80 bg-black/40 p-3 rounded mb-6 max-w-lg overflow-auto max-h-32">
            {msg}
          </pre>
          {errorInfo && (
            <pre className="text-left text-xs text-gray-500 mb-6 max-w-lg overflow-auto max-h-24">
              {errorInfo}
            </pre>
          )}
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg bg-teal-500/20 text-teal-300 hover:bg-teal-500/30 transition-colors"
          >
            Refresh page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
