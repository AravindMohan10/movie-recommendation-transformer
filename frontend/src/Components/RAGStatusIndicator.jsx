import React, { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export default function RAGStatusIndicator() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("cineai_token");
    if (!token) return;
    fetch(`${API_BASE}/debug/rag-status`, {
      credentials: "include",
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus({ available: false }));
  }, []);

  if (!status) return null;

  return (
    <div
      className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/50 border border-teal-500/20"
      title={status.available ? `RAG index: ${status.index_count ?? 0} movies` : "RAG unavailable"}
    >
      <div
        className={`w-1.5 h-1.5 rounded-full ${status.available ? "bg-teal-400" : "bg-amber-500"}`}
      />
      <span className="text-xs text-teal-200">
        {status.available ? "RAG + CF" : "CF only"}
      </span>
    </div>
  );
}
