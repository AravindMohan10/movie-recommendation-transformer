import React, { useMemo } from "react";
import { getShowcaseQueueForToday } from "../data/landingShowcase";

export default function LandingPreview() {
  const queue = useMemo(() => getShowcaseQueueForToday(), []);
  const featured = queue.movies[0];

  return (
    <div className="landing-preview rounded-2xl p-5 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-teal-400/80">{queue.theme}</p>
          <p className="mt-1 text-sm text-gray-300">Ranked for tonight</p>
        </div>
        <span className="shrink-0 rounded-full border border-teal-500/30 bg-teal-500/10 px-3 py-1 text-xs text-teal-200">
          {queue.confidence}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3.5">
        {queue.movies.map((movie, index) => (
          <div
            key={movie.id}
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
            <div className="px-2.5 py-2.5">
              <p className="truncate text-xs font-medium text-white">{movie.title}</p>
              {movie.meta && (
                <p className="mt-0.5 truncate text-[10px] text-gray-500">{movie.meta}</p>
              )}
              {index === 0 && (
                <p className="mt-1 text-[10px] text-teal-300/90">Top pick</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-xl border border-teal-700/30 bg-black/50 px-4 py-3.5">
        <p className="mb-1.5 text-[10px] uppercase tracking-[0.16em] text-teal-400/75">
          Why {featured.title}
        </p>
        <p className="text-sm leading-relaxed text-gray-300">{featured.reason}</p>
      </div>
    </div>
  );
}
