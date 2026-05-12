import React from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import CinematicBackdrop from "../Components/CinematicBackdrop";

export default function LandingPage() {
  const festivalBoard = [
    {
      title: "A Separation",
      note: "Moral tension, intimate stakes, layered performances",
      meta: "Drama • Iran • 2011",
      tone: "from-[#17314a] to-[#0f1b2b]",
    },
    {
      title: "Memories of Murder",
      note: "Atmospheric dread with restrained, human investigation",
      meta: "Thriller • Korea • 2003",
      tone: "from-[#2f1f32] to-[#151019]",
    },
    {
      title: "In the Mood for Love",
      note: "Elegant longing, rhythm, and visual poetry",
      meta: "Romance • Hong Kong • 2000",
      tone: "from-[#3a2a1b] to-[#1c140d]",
    },
    {
      title: "Portrait of a Lady on Fire",
      note: "Silence, gaze, and emotional precision",
      meta: "Drama • France • 2019",
      tone: "from-[#2d3b2f] to-[#121a13]",
    },
  ];

  const recommendationMoments = [
    {
      title: "After Midnight",
      mood: "Quiet intensity",
      reason:
        "You gravitate toward character-driven tension and restrained storytelling. This one lands in that exact emotional register.",
    },
    {
      title: "The Last Platform",
      mood: "Visceral drama",
      reason:
        "Your recent likes favor grounded stakes and moral conflict. This recommendation follows the same tonal line with stronger pacing.",
    },
    {
      title: "Blue Hour Letters",
      mood: "Romantic melancholy",
      reason:
        "You repeatedly respond to reflective romance with emotional payoff. This pick matches that atmosphere without feeling repetitive.",
    },
  ];

  const principles = [
    {
      title: "Taste, not trends",
      description:
        "CineAI prioritizes your taste profile over generic popularity loops, so recommendations feel personal from the first sessions.",
    },
    {
      title: "Cinema as craft",
      description:
        "Suggestions consider tone, themes, and storytelling rhythm, not only surface-level genre tags.",
    },
    {
      title: "Living recommendations",
      description:
        "Every like, review, and skip reshapes your queue, so discovery keeps up with how your taste evolves.",
    },
  ];

  const journey = [
    {
      step: "01",
      title: "Signal your taste",
      description:
        "Rate, like, or review a few films. That first signal is enough to begin shaping your cinematic profile.",
    },
    {
      step: "02",
      title: "Build your profile",
      description:
        "CineAI interprets your interaction patterns and review semantics to map what truly resonates with you.",
    },
    {
      step: "03",
      title: "Watch with confidence",
      description:
        "Receive ranked picks with clear rationale so choosing what to watch feels fast, intentional, and rewarding.",
    },
  ];

  const trustPoints = [
    "Personalized from your own interaction history",
    "Balanced between familiarity and discovery",
    "Built to reduce decision fatigue",
  ];

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden text-white">
      <CinematicBackdrop />
      <div className="relative z-50">
        <section className="relative flex min-h-screen flex-col items-center justify-center px-6 pb-20 pt-12">
          <Link
            to="/get-started"
            className="absolute right-8 top-8 rounded-full border border-white/25 bg-black/30 px-5 py-2 text-sm font-medium text-white backdrop-blur transition hover:bg-white/15"
          >
            Sign in
          </Link>

          <Link
            to="/"
            className="absolute left-8 top-8 select-none text-2xl tracking-tight text-white"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            cine.ai
          </Link>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7 }}
            className="mb-5 text-center text-xs uppercase tracking-[0.24em] text-zinc-300"
          >
            Curated for your cinematic taste
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="mb-7 max-w-5xl text-center text-4xl leading-tight sm:text-6xl lg:text-7xl"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            Cinema is an art form.
            <br />
            Your recommendations should feel like curation, not noise.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.8 }}
            className="mx-auto mb-12 max-w-3xl text-center text-lg text-zinc-200 sm:text-xl"
          >
            CineAI learns how you watch and what resonates, then composes a queue aligned to your tone, storytelling rhythm, and cinematic preferences.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.6 }}
            className="mb-14 flex flex-col items-center gap-4 sm:flex-row"
          >
            <Link
              to="/get-started"
              className="rounded-full bg-[#f4e7cb] px-9 py-3 text-sm font-semibold text-black shadow-xl transition hover:bg-[#f8ecd4]"
            >
              Start your profile
            </Link>
            <a
              href="#how-it-works"
              className="rounded-full border border-white/25 bg-transparent px-9 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Explore the experience
            </a>
          </motion.div>

          <div className="mx-auto grid w-full max-w-5xl grid-cols-1 gap-3 rounded-2xl border border-white/15 bg-black/35 p-4 backdrop-blur sm:grid-cols-3">
            {trustPoints.map((point) => (
              <div key={point} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-center text-sm text-zinc-100">
                {point}
              </div>
            ))}
          </div>
        </section>

        <div className="mx-auto h-px w-[88%] max-w-6xl bg-gradient-to-r from-transparent via-white/25 to-transparent" />

        <section className="w-full px-6 pb-24 pt-6">
          <h2
            className="mb-3 text-center text-3xl text-white sm:text-4xl"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            Designed for people who care about cinema
          </h2>
          <p className="mx-auto mb-10 max-w-3xl text-center text-zinc-300">
            Built as a curation experience, not an endless feed, so every recommendation feels considered.
          </p>
          <div className="mx-auto grid w-full max-w-6xl gap-5 md:grid-cols-3">
            {principles.map((item) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5 }}
                className="rounded-2xl border border-white/15 bg-black/40 p-7 backdrop-blur"
              >
                <h3 className="mb-3 text-lg font-semibold text-white">{item.title}</h3>
                <p className="text-sm leading-6 text-zinc-300">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <div className="mx-auto h-px w-[88%] max-w-6xl bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        <section className="w-full px-6 pb-24 pt-4">
          <h2
            className="mb-10 text-center text-3xl text-white sm:text-4xl"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            Tonight&apos;s curation board
          </h2>
          <p className="mx-auto mb-8 max-w-3xl text-center text-zinc-300">
            Instead of noisy poster spam, you get a clear board of cinematic directions with intent, mood, and narrative texture.
          </p>
          <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 md:grid-cols-2">
            {festivalBoard.map((item, idx) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.45, delay: idx * 0.06 }}
                className={`relative overflow-hidden rounded-2xl border border-white/20 bg-gradient-to-br ${item.tone} p-6 shadow-2xl`}
                style={{ transform: idx % 2 === 0 ? "rotate(-0.6deg)" : "rotate(0.6deg)" }}
              >
                <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-zinc-300">Curator note</p>
                <h3
                  className="mb-3 text-2xl text-white"
                  style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
                >
                  {item.title}
                </h3>
                <p className="mb-4 text-sm leading-6 text-zinc-200">{item.note}</p>
                <p className="text-xs uppercase tracking-[0.12em] text-zinc-300">{item.meta}</p>
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent" />
              </motion.div>
            ))}
          </div>
        </section>

        <div className="mx-auto h-px w-[88%] max-w-6xl bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        <section id="how-it-works" className="w-full px-6 pb-24 pt-2">
          <h2
            className="mb-10 text-center text-3xl text-white sm:text-4xl"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            How your curation evolves
          </h2>
          <div className="mx-auto grid w-full max-w-6xl gap-5 md:grid-cols-3">
            {journey.map((item) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5 }}
                className="rounded-2xl border border-white/15 bg-black/35 p-7"
              >
                <p className="mb-3 text-xs font-semibold tracking-[0.18em] text-zinc-400">{item.step}</p>
                <h3 className="mb-3 text-lg font-semibold text-white">{item.title}</h3>
                <p className="text-sm leading-6 text-zinc-300">{item.description}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <div className="mx-auto h-px w-[88%] max-w-6xl bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        <section className="w-full px-6 pb-24 pt-2">
          <h2
            className="mb-10 text-center text-3xl text-white sm:text-4xl"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            Recommendation notes, like a human curator
          </h2>
          <div className="mx-auto grid w-full max-w-6xl gap-5 md:grid-cols-3">
            {recommendationMoments.map((card) => (
              <div key={card.title} className="rounded-2xl border border-white/15 bg-black/45 p-7 backdrop-blur">
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">{card.mood}</p>
                <h3 className="mb-2 text-xl font-bold text-white">{card.title}</h3>
                <p className="text-sm leading-6 text-zinc-300">{card.reason}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="mx-auto h-px w-[88%] max-w-6xl bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        <section className="flex flex-col items-center justify-center px-6 pb-24 pt-4">
          <motion.h2
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-3 text-center text-3xl text-white"
            style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}
          >
            Your next great watch is already in your profile.
          </motion.h2>
          <p className="mb-8 max-w-2xl text-center text-zinc-300">
            Start with a few films you love. CineAI will shape the rest into a recommendation experience that feels crafted and personal.
          </p>
          <Link
            to="/get-started"
            className="rounded-full bg-[#f4e7cb] px-12 py-4 text-base font-semibold text-black shadow-xl transition hover:bg-[#f8ecd4]"
          >
            Begin your curation
          </Link>
          <p className="mt-5 text-xs uppercase tracking-[0.2em] text-zinc-400">
            Crafted for people who love cinema
          </p>
        </section>
      </div>
    </div>
  );
}