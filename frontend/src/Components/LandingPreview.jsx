import React from "react";

const FALLBACK = [
  {
    id: 1,
    title: "Inception",
    poster_url: "https://image.tmdb.org/t/p/w342/8UlWHLMpgZm9bx6QYh0NFoq67TZ.jpg",
  },
  {
    id: 2,
    title: "Interstellar",
    poster_url: "https://image.tmdb.org/t/p/w342/6ELJEzQJ3Y45HczvreC3dg0GV5R.jpg",
  },
  {
    id: 3,
    title: "The Dark Knight",
    poster_url: "https://image.tmdb.org/t/p/w342/2CAL2433ZeIihfX1Hb2139CX0pW.jpg",
  },
];

export default function LandingPreview({ movies = [] }) {
  const list = movies.length >= 3 ? movies.slice(0, 3) : FALLBACK;
  const featured = list[0];

  return (
    <div className="landing-preview rounded-2xl p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-teal-400/80">Your queue</p>
          <p className="text-sm text-gray-300">Ranked for tonight</p>
        </div>
        <span className="rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-xs text-teal-200">
          High confidence
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {list.map((movie, index) => (
          <div
            key={movie.id || movie.title}
            className={`landing-preview-card overflow-hidden rounded-xl ${index === 0 ? "is-featured" : ""}`}
          >
            <div className="aspect-[2/3] bg-zinc-900">
              <img
                src={movie.poster_url}
                alt={movie.title}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            </div>
            <div className="px-2.5 py-2">
              <p className="truncate text-xs font-medium text-white">{movie.title}</p>
              {index === 0 && (
                <p className="mt-0.5 text-[10px] text-teal-300/90">Top pick</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-teal-700/30 bg-black/50 px-4 py-3">
        <p className="mb-1 text-[10px] uppercase tracking-[0.16em] text-teal-400/75">Why this pick</p>
        <p className="text-sm leading-relaxed text-gray-300">
          You tend to save slow-burn thrillers with moral tension.{" "}
          <span className="text-white">{featured?.title}</span> sits in that lane — same restraint, higher stakes.
        </p>
      </div>
    </div>
  );
}
