import React from "react";
import { Link } from "react-router-dom";
import CinematicBackdrop from "../Components/CinematicBackdrop";

const features = [
  {
    title: "Personalized recommendations",
    description:
      "Collaborative filtering and content signals ranked from your likes, ratings, and reviews.",
  },
  {
    title: "Clear explanations",
    description:
      "Each pick can include a short reason grounded in your taste — not generic popularity copy.",
  },
  {
    title: "Watchlist and reviews",
    description:
      "Save films, leave reviews, and let those interactions reshape what shows up next.",
  },
  {
    title: "Hidden gems and Surprise Me",
    description:
      "Browse underrated titles or pull a few unexpected picks when you want something new.",
  },
];

const steps = [
  {
    title: "Tell us what you like",
    description: "Pick genres and a few favorites during onboarding, or start from scratch.",
  },
  {
    title: "Get a ranked queue",
    description: "Recommendations update as you like, rate, and review films.",
  },
  {
    title: "Dig deeper",
    description: "Use genre browse, deep cuts, and Surprise Me when you want variety.",
  },
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-black text-white">
      <CinematicBackdrop />

      <div className="relative z-10">
        <nav className="flex items-center justify-between px-6 py-6 sm:px-10">
          <Link
            to="/"
            className="text-2xl font-extrabold tracking-tight bg-gradient-to-r from-teal-300 via-yellow-100 to-blue-200 bg-clip-text text-transparent"
          >
            cine.<span className="text-white">ai</span>
          </Link>
          <Link
            to="/get-started"
            className="rounded-full border border-teal-400/50 px-5 py-2 text-sm text-teal-200 transition hover:border-teal-400 hover:bg-teal-500/10"
          >
            Sign in
          </Link>
        </nav>

        <section className="flex min-h-[78vh] flex-col items-center justify-center px-6 pb-16 pt-8 text-center">
          <h1 className="mb-5 max-w-3xl text-4xl font-light tracking-wide text-white sm:text-5xl lg:text-6xl">
            Movie recommendations that learn from how you watch
          </h1>
          <p className="mb-10 max-w-xl text-base text-gray-400 sm:text-lg font-light">
            Rate films, leave reviews, and get a queue shaped by your taste — with reasons you can actually read.
          </p>
          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <Link
              to="/get-started"
              className="rounded-full bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 px-9 py-3 text-sm font-semibold text-black shadow-lg transition hover:scale-[1.02]"
            >
              Get started
            </Link>
            <a
              href="#features"
              className="rounded-full border border-teal-700 px-9 py-3 text-sm font-medium text-teal-200 transition hover:border-teal-500 hover:bg-teal-500/10"
            >
              See features
            </a>
          </div>
        </section>

        <section id="features" className="border-t border-teal-700/30 px-6 py-20 sm:px-10">
          <div className="mx-auto max-w-5xl">
            <h2 className="mb-3 text-2xl font-light tracking-wide text-white sm:text-3xl">
              What you get
            </h2>
            <p className="mb-12 max-w-2xl text-gray-400 font-light">
              Built around interactions — not a trending feed.
            </p>
            <div className="grid gap-x-10 gap-y-10 sm:grid-cols-2">
              {features.map((item) => (
                <div key={item.title}>
                  <h3 className="mb-2 text-base font-medium text-teal-200">{item.title}</h3>
                  <p className="text-sm leading-relaxed text-gray-400">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-t border-teal-700/30 px-6 py-20 sm:px-10">
          <div className="mx-auto max-w-5xl">
            <h2 className="mb-12 text-2xl font-light tracking-wide text-white sm:text-3xl">
              How it works
            </h2>
            <div className="grid gap-10 sm:grid-cols-3">
              {steps.map((item, i) => (
                <div key={item.title}>
                  <p className="mb-2 text-xs tracking-widest text-teal-400/80">
                    {String(i + 1).padStart(2, "0")}
                  </p>
                  <h3 className="mb-2 text-base font-medium text-white">{item.title}</h3>
                  <p className="text-sm leading-relaxed text-gray-400">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-t border-teal-700/30 px-6 py-20 text-center sm:px-10">
          <h2 className="mb-4 text-2xl font-light tracking-wide text-white sm:text-3xl">
            Start with a few films you like
          </h2>
          <p className="mx-auto mb-8 max-w-md text-gray-400 font-light">
            Create an account and your recommendations improve as you interact.
          </p>
          <Link
            to="/get-started"
            className="inline-block rounded-full bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 px-10 py-3.5 text-sm font-semibold text-black shadow-lg transition hover:scale-[1.02]"
          >
            Get started
          </Link>
        </section>

        <footer className="border-t border-teal-700/20 px-6 py-8 text-center text-xs text-gray-500 sm:px-10">
          cine.ai
        </footer>
      </div>
    </div>
  );
}
