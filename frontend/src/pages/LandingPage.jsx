import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Film, ListChecks, MessageSquare, Shuffle, Sparkles } from "lucide-react";
import CinematicBackdrop from "../Components/CinematicBackdrop";
import LandingPreview from "../Components/LandingPreview";
import { getRandomMovies, wakeBackend } from "../Utils/api";
import "./LandingPage.css";

const features = [
  {
    icon: Sparkles,
    title: "Ranked recommendations",
    description: "Your queue is rebuilt from likes, ratings, and reviews — not a trending list.",
  },
  {
    icon: MessageSquare,
    title: "Readable reasons",
    description: "Each pick can show why it fits your taste, based on what you've actually watched.",
  },
  {
    icon: ListChecks,
    title: "Watchlist + reviews",
    description: "Save films, write reviews, and let those signals feed back into the next batch.",
  },
  {
    icon: Shuffle,
    title: "Hidden gems & Surprise Me",
    description: "Browse underrated titles or pull a short list when you want something off-path.",
  },
];

const steps = [
  {
    n: "01",
    title: "Set your taste",
    description: "Pick genres and a few favorites in onboarding, or start cold and train as you go.",
  },
  {
    n: "02",
    title: "Get a queue",
    description: "Recommendations refresh as you interact. Likes and reviews move the ranking.",
  },
  {
    n: "03",
    title: "Browse deeper",
    description: "Genre browse, deep cuts, and Surprise Me when you want variety beyond the main feed.",
  },
];

const FALLBACK_POSTERS = [
  { id: 1, title: "Inception", poster_url: "https://image.tmdb.org/t/p/w342/8UlWHLMpgZm9bx6QYh0NFoq67TZ.jpg" },
  { id: 2, title: "Interstellar", poster_url: "https://image.tmdb.org/t/p/w342/6ELJEzQJ3Y45HczvreC3dg0GV5R.jpg" },
  { id: 3, title: "The Dark Knight", poster_url: "https://image.tmdb.org/t/p/w342/2CAL2433ZeIihfX1Hb2139CX0pW.jpg" },
  { id: 4, title: "The Matrix", poster_url: "https://image.tmdb.org/t/p/w342/6KErczPBROQty7QoIsaa6wJYXZi.jpg" },
  { id: 5, title: "Pulp Fiction", poster_url: "https://image.tmdb.org/t/p/w342/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg" },
  { id: 6, title: "Parasite", poster_url: "https://image.tmdb.org/t/p/w342/7IiTTgloJzvGI1WAMzqwXlbVJ1H.jpg" },
  { id: 7, title: "Blade Runner 2049", poster_url: "https://image.tmdb.org/t/p/w342/gajvaN1LiSV1KNwwZoGirIK3zQ0.jpg" },
  { id: 8, title: "Arrival", poster_url: "https://image.tmdb.org/t/p/w342/x2FJ7tcl6DVMsisWHmpIHZMpYM8.jpg" },
];

export default function LandingPage() {
  const [posters, setPosters] = useState(FALLBACK_POSTERS);

  useEffect(() => {
    wakeBackend();
    getRandomMovies(8)
      .then((data) => {
        if (data?.movies?.length) setPosters(data.movies);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-black text-white">
      <CinematicBackdrop />

      <div className="pointer-events-none fixed inset-0 z-[1] opacity-25">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_82%,rgba(1,255,233,0.28),transparent_52%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_82%_18%,rgba(252,255,108,0.22),transparent_50%)]" />
      </div>

      <div className="relative z-10">
        <header className="landing-nav">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 lg:px-10">
            <Link
              to="/"
              className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-teal-300 via-yellow-100 to-blue-200 bg-clip-text text-transparent"
            >
              cine.<span className="text-white">ai</span>
            </Link>

            <nav className="hidden items-center gap-8 text-sm text-gray-400 md:flex">
              <a href="#features" className="transition hover:text-teal-200">Features</a>
              <a href="#how-it-works" className="transition hover:text-teal-200">How it works</a>
            </nav>

            <div className="flex items-center gap-3">
              <Link
                to="/get-started"
                className="hidden rounded-full border border-teal-700/60 px-4 py-2 text-sm text-teal-200 transition hover:border-teal-500 hover:bg-teal-500/10 sm:inline-block"
              >
                Sign in
              </Link>
              <Link
                to="/get-started"
                className="rounded-full bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 px-5 py-2 text-sm font-semibold text-black shadow-lg transition hover:brightness-105"
              >
                Get started
              </Link>
            </div>
          </div>
        </header>

        <section className="mx-auto max-w-7xl px-6 pb-20 pt-14 lg:px-10 lg:pb-28 lg:pt-20">
          <div className="landing-hero-grid">
            <div>
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-teal-700/40 bg-black/50 px-3 py-1 text-xs text-teal-200/90">
                <Film className="h-3.5 w-3.5" />
                50k+ films indexed
              </p>

              <h1 className="mb-5 max-w-xl text-4xl font-light leading-[1.12] tracking-wide text-white sm:text-5xl lg:text-[3.35rem]">
                Find your next film without the endless scroll
              </h1>

              <p className="mb-8 max-w-lg text-base leading-relaxed text-gray-400 sm:text-lg">
                CineAI ranks movies from your likes and reviews, then shows why each pick fits — so choosing what to watch takes minutes, not an hour.
              </p>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  to="/get-started"
                  className="inline-flex justify-center rounded-full bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 px-8 py-3 text-sm font-semibold text-black shadow-lg transition hover:brightness-105"
                >
                  Create free account
                </Link>
                <a
                  href="#features"
                  className="inline-flex justify-center rounded-full border border-teal-700/70 px-8 py-3 text-sm font-medium text-teal-200 transition hover:border-teal-500 hover:bg-teal-500/10"
                >
                  See what&apos;s inside
                </a>
              </div>

              <dl className="mt-10 grid max-w-md grid-cols-3 gap-4 border-t border-teal-800/30 pt-8">
                <div>
                  <dt className="text-[11px] uppercase tracking-wider text-gray-500">Signals</dt>
                  <dd className="mt-1 text-sm text-gray-200">Likes & reviews</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wider text-gray-500">Refresh</dt>
                  <dd className="mt-1 text-sm text-gray-200">Daily queue</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wider text-gray-500">Explain</dt>
                  <dd className="mt-1 text-sm text-gray-200">Per-pick reasons</dd>
                </div>
              </dl>
            </div>

            <div className="mx-auto w-full max-w-md lg:max-w-none">
              <LandingPreview movies={posters} />
            </div>
          </div>
        </section>

        <section className="border-y border-teal-800/25 bg-black/40 py-10">
          <div className="mx-auto max-w-7xl px-6 lg:px-10">
            <div className="mb-5 flex items-end justify-between gap-4">
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] text-teal-400/75">From the catalog</p>
                <h2 className="mt-1 text-lg font-light text-white sm:text-xl">Films in rotation tonight</h2>
              </div>
              <p className="hidden text-xs text-gray-500 sm:block">Pulled live from the library</p>
            </div>
            <div className="landing-fade-edges">
              <div className="landing-poster-row">
                {posters.map((movie) => (
                  <figure key={movie.id || movie.title} className="landing-poster">
                    <img src={movie.poster_url} alt={movie.title} loading="lazy" />
                  </figure>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="mx-auto max-w-7xl px-6 py-20 lg:px-10 lg:py-28">
          <div className="mb-12 max-w-2xl">
            <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-teal-400/75">Features</p>
            <h2 className="text-3xl font-light tracking-wide text-white sm:text-4xl">
              Built for people who actually pick films
            </h2>
            <p className="mt-4 text-gray-400">
              Not a popularity feed. A working queue you can trust, refine, and return to.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            {features.map(({ icon: Icon, title, description }) => (
              <article key={title} className="landing-feature-card rounded-2xl p-6">
                <div className="mb-4 inline-flex rounded-lg border border-teal-700/40 bg-teal-500/10 p-2.5 text-teal-300">
                  <Icon className="h-5 w-5" strokeWidth={1.75} />
                </div>
                <h3 className="mb-2 text-base font-medium text-white">{title}</h3>
                <p className="text-sm leading-relaxed text-gray-400">{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="border-t border-teal-800/25 bg-black/30">
          <div className="mx-auto max-w-7xl px-6 py-20 lg:px-10 lg:py-28">
            <div className="mb-12 max-w-xl">
              <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-teal-400/75">How it works</p>
              <h2 className="text-3xl font-light tracking-wide text-white sm:text-4xl">
                Three steps to a queue that sticks
              </h2>
            </div>

            <div className="grid gap-8 md:grid-cols-3">
              {steps.map((step) => (
                <article key={step.n} className="landing-step">
                  <p className="mb-3 font-mono text-xs text-teal-400/80">{step.n}</p>
                  <h3 className="mb-2 text-lg font-medium text-white">{step.title}</h3>
                  <p className="text-sm leading-relaxed text-gray-400">{step.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-20 lg:px-10 lg:py-24">
          <div className="landing-cta-panel rounded-3xl px-8 py-12 text-center sm:px-12 sm:py-14">
            <h2 className="mx-auto mb-4 max-w-lg text-2xl font-light tracking-wide text-white sm:text-3xl">
              Start with three films you already love
            </h2>
            <p className="mx-auto mb-8 max-w-md text-sm text-gray-400 sm:text-base">
              Free to use. Your queue gets sharper every time you rate or review something.
            </p>
            <Link
              to="/get-started"
              className="inline-flex rounded-full bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 px-10 py-3.5 text-sm font-semibold text-black shadow-lg transition hover:brightness-105"
            >
              Get started
            </Link>
          </div>
        </section>

        <footer className="border-t border-teal-800/20 px-6 py-8 text-center text-xs text-gray-600">
          <p>cine.ai — movie recommendations from your taste, not the crowd</p>
        </footer>
      </div>
    </div>
  );
}
