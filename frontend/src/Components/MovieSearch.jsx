import React, { useState, useEffect, useRef } from "react";
import { Search, ThumbsUp, Bookmark, Loader2 } from "lucide-react";
import { searchMovies } from "../Utils/api";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

function posterUrl(m) {
  if (m.poster_url) return m.poster_url;
  const p = m.poster_path;
  if (!p) return "https://via.placeholder.com/48x72/1a1a1a/666?text=No+Poster";
  return p.startsWith("http") ? p : `https://image.tmdb.org/t/p/w92${p.startsWith("/") ? p : `/${p}`}`;
}

function authHeaders() {
  const t = localStorage.getItem("cineai_token");
  return { Authorization: `Bearer ${t}`, "Content-Type": "application/json" };
}

export default function MovieSearch({ onLike, onWatchlist, isInWatchlist }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [source, setSource] = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [acting, setActing] = useState(null);
  const ref = useRef(null);

  useEffect(() => {
    const t = setTimeout(() => {
      if (!q || q.trim().length < 2) {
        setResults([]);
        setSource(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      searchMovies(q)
        .then((r) => {
          setResults(r.results || []);
          setSource(r.source || "catalog");
        })
        .catch(() => {
          setResults([]);
          setSource(null);
        })
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const like = async (m) => {
    const id = m.id ?? m.tmdb_id;
    if (!id || acting) return;
    setActing(id);
    try {
      const res = await fetch(`${API_BASE}/recommendations/interact`, {
        method: "POST",
        credentials: "include",
        headers: authHeaders(),
        body: JSON.stringify({ movie_id: id, action: "like" }),
      });
      if (res.ok) onLike?.();
    } catch (e) {}
    setActing(null);
  };

  const watchlist = async (m) => {
    const id = m.id ?? m.tmdb_id;
    if (!id || acting) return;
    setActing(id);
    try {
      const inList = isInWatchlist?.(id);
      const res = inList
        ? await fetch(`${API_BASE}/watchlist/remove/${id}`, {
            method: "DELETE",
            credentials: "include",
            headers: authHeaders(),
          })
        : await fetch(`${API_BASE}/watchlist/add?movie_id=${id}`, {
            method: "POST",
            credentials: "include",
            headers: authHeaders(),
          });
      if (res.ok) onWatchlist?.();
    } catch (e) {}
    setActing(null);
  };

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-black/50 border border-teal-500/30">
        <Search className="w-4 h-4 text-teal-400" />
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Search movies…"
          className="bg-transparent border-none outline-none text-white placeholder-gray-500 w-40 sm:w-52"
        />
        {loading && <Loader2 className="w-4 h-4 text-teal-400 animate-spin" />}
      </div>
      {open && (q.trim().length >= 2 || results.length > 0) && (
        <div className="absolute top-full left-0 mt-1 w-80 max-h-96 overflow-y-auto rounded-xl border border-teal-500/30 bg-black/95 shadow-xl z-50">
          {loading && results.length === 0 ? (
            <div className="p-4 text-center text-gray-400">Searching…</div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-gray-500 text-sm">No movies found</div>
          ) : (
            <>
              {source === "tmdb" && (
                <div className="px-3 py-2 text-xs text-teal-400/80 border-b border-teal-500/20">
                  Full TMDB catalog — e.g. Mission Impossible, any movie
                </div>
              )}
              {results.map((m) => {
                const id = m.id ?? m.tmdb_id;
                const inList = isInWatchlist?.(id);
                const busy = acting === id;
                return (
                  <div
                    key={id}
                    className="flex items-center gap-3 p-3 hover:bg-white/5 border-b border-teal-500/10 last:border-0"
                  >
                    <img
                      src={posterUrl(m)}
                      alt=""
                      className="w-10 h-14 object-cover rounded flex-shrink-0"
                      onError={(e) => { e.target.onerror = null; e.target.src = "https://via.placeholder.com/40x56/1a1a1a/666666?text=No+Poster"; }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-medium truncate">{m.title}</p>
                      {m.release_year && (
                        <p className="text-gray-500 text-xs">{m.release_year}</p>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => like(m)}
                        disabled={busy}
                        className="p-1.5 rounded-lg text-gray-400 hover:text-green-400 hover:bg-white/5 disabled:opacity-50"
                        title="Like"
                      >
                        <ThumbsUp className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => watchlist(m)}
                        disabled={busy}
                        className={`p-1.5 rounded-lg hover:bg-white/5 disabled:opacity-50 ${
                          inList ? "text-teal-400" : "text-gray-400 hover:text-teal-400"
                        }`}
                        title={inList ? "Remove from watchlist" : "Add to watchlist"}
                      >
                        <Bookmark
                          className="w-4 h-4"
                          fill={inList ? "currentColor" : "none"}
                        />
                      </button>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}
    </div>
  );
}
