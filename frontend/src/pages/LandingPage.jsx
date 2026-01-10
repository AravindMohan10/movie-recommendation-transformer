import React, { useEffect, useState } from "react";
import { motion, useAnimation } from "framer-motion";
import { Link } from "react-router-dom";
import CinematicBackdrop from "../Components/CinematicBackdrop";
import GlassOrb from "../Components/GlassOrb";
import { getRandomMovies } from "../Utils/api";

const fallbackPosters = [
  "https://image.tmdb.org/t/p/w300/8UlWHLMpgZm9bx6QYh0NFoq67TZ.jpg",
  "https://image.tmdb.org/t/p/w300/q719jXXEzOoYaps6babgKnONONX.jpg",
  "https://image.tmdb.org/t/p/w300/6KErczPBROQty7QoIsaa6wJYXZi.jpg",
  "https://image.tmdb.org/t/p/w300/2CAL2433ZeIihfX1Hb2139CX0pW.jpg",
  "https://image.tmdb.org/t/p/w300/xBHvZcjRiWyobQ9kxBhO6B2dtRI.jpg",
];

export default function LandingPage() {
  const [showArrow, setShowArrow] = useState(true);
  const arrowControls = useAnimation();
  const [posters, setPosters] = useState(fallbackPosters);

  useEffect(() => {
    getRandomMovies(12)
      .then((data) => {
        const urls = (data.movies || []).map((m) => m.poster_url).filter(Boolean);
        if (urls.length) setPosters(urls);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const onScroll = () => {
      if (window.scrollY > window.innerHeight * 0.2) {
        setShowArrow(false);
        arrowControls.start({ opacity: 0, y: 30, pointerEvents: "none" });
      } else {
        setShowArrow(true);
        arrowControls.start({ opacity: 1, y: 0 });
      }
    };
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, [arrowControls]);

  const featureData = [
    { icon: "🎯", title: "CF + RAG", desc: "Collaborative filtering plus RAG over reviews. No documentaries, quality picks." },
    { icon: "⭐", title: "Rate & Review", desc: "Likes and reviews feed both CF and RAG for better personalization." },
    { icon: "🔄", title: "24h Refresh", desc: "Recommendations refresh every 24h; no same movie twice." },
    { icon: "📊", title: "Confidence & Why", desc: "Per-movie confidence and “Why recommended?” so you see the thinking." },
  ];

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden font-sans text-white">
      {/* Cinematic, animated gradient background */}
      <CinematicBackdrop />

      {/* Center Glass Orb for Cinematic Depth */}
      <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
        <GlassOrb />
      </div>

      {/* Main content overlays – above backdrop (z-50) */}
      <div className="relative z-50">
        {/* Hero Section */}
        <section className="relative flex flex-col min-h-screen items-center justify-center pb-24 pt-12 px-4">
          <Link
            to="/get-started"
            className="absolute top-8 right-8 px-6 py-2 rounded-full text-sm font-semibold bg-gradient-to-r from-teal-400 to-blue-500 text-white shadow-lg hover:from-teal-500 hover:to-blue-600 transition-all"
          >
            Sign In / Login
          </Link>

          <Link
            to="/"
            className="absolute top-8 left-8 text-2xl font-extrabold bg-gradient-to-r from-teal-300 to-blue-200 bg-clip-text text-transparent tracking-tight select-none"
          >
            cine.<span className="text-white">ai</span>
          </Link>

          {/* Cinematic OG Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1 }}
            className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-extrabold text-center mb-7 leading-tight"
            style={{
              background:
                "linear-gradient(95deg, #00ffd5 10%, #fcff6c 50%, #8ed6ff 90%, #fff 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              filter: "drop-shadow(0 6px 32px #01ffe9bb)",
              textShadow: "0 4px 28px #25252580, 0 1px 14px #ffffff13",
            }}
          >
            Movies that fit your life—
            <span style={{ color: "#fff", WebkitTextFillColor: "white" }}>
              before you click play.
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 1 }}
            className="max-w-2xl mx-auto text-xl sm:text-2xl text-center text-gray-300 mb-14 font-medium"
          >
            Collaborative filtering + RAG over reviews. Like, review, and add to your watchlist—we personalize from your taste.
          </motion.p>

          {/* Scroll Arrow */}
          <motion.div
            className="absolute left-1/2 -translate-x-1/2 bottom-12 flex flex-col items-center"
            animate={arrowControls}
            initial={{ opacity: 1, y: 0 }}
          >
            {showArrow && (
              <>
                <span className="text-xs text-gray-300 mb-1">
                  Scroll to explore
                </span>
                <motion.svg
                  animate={{ y: [0, 14, 0] }}
                  transition={{ repeat: Infinity, duration: 1.6 }}
                  className="w-7 h-7 text-gray-300/60"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.2}
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 9l-7 7-7-7"
                  />
                </motion.svg>
              </>
            )}
          </motion.div>
        </section>

        <section className="relative w-full pt-16 pb-24 px-4">
          <motion.h3
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4, duration: 0.8 }}
            className="text-xl sm:text-2xl font-semibold text-center text-teal-300 mb-4"
          >
            Sample Picks — Good Movies, Any Genre
          </motion.h3>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 1 }}
            className="relative overflow-hidden w-full max-w-4xl mx-auto"
          >
            <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-black to-transparent z-10" />
            <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-black to-transparent z-10" />
            <div className="flex animate-marquee gap-4">
              {posters.concat(posters).map((src, idx) => (
                <img
                  key={idx}
                  src={src}
                  alt="Movie poster"
                  onError={(e) => { e.target.onerror = null; e.target.src = "https://via.placeholder.com/160x240/1a1a1a/666666?text=Movie"; }}
                  className="w-40 h-60 object-cover rounded-lg shadow-xl"
                />
              ))}
            </div>
          </motion.div>
        </section>

        {/* Features */}
        <section className="relative w-full pt-16 pb-24 px-4">
          <motion.h2
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-3xl sm:text-4xl font-extrabold text-center mb-14 text-teal-300"
          >
            Why cine.ai?
          </motion.h2>
          <div className="flex flex-wrap justify-center gap-8">
            {featureData.map((f, i) => (
              <motion.div
                key={i}
                whileHover={{ scale: 1.04, y: -4 }}
                initial={{ opacity: 0, y: 32 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.16 + i * 0.1, duration: 0.7 }}
                className="w-60 p-6 flex flex-col items-center bg-black/60 border border-teal-500/30 rounded-2xl hover:border-teal-400/50"
              >
                <span className="text-3xl mb-3">{f.icon}</span>
                <h3 className="text-lg font-semibold mb-2 text-white">
                  {f.title}
                </h3>
                <p className="text-teal-200 text-sm text-center">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Comparison Table */}
        <section className="relative w-full pt-16 pb-24 px-4">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-center mb-10 text-teal-300">
            How We Stack Up
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full max-w-4xl mx-auto bg-black/60 text-gray-300 border-collapse rounded-xl overflow-hidden border border-teal-500/20">
              <thead className="bg-teal-900/40 text-teal-200">
                <tr>
                  <th className="p-4 text-left">Feature</th>
                  <th className="p-4 text-left">cine.ai</th>
                  <th className="p-4 text-left">Other Sites</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Time to First Play", "~2 suggestions", "5+ suggestions"],
                  ["Personalization", "High", "Low"],
                  ["Feedback Loop", "Instant", "Delayed"],
                ].map((row, idx) => (
                  <motion.tr
                    key={idx}
                    className="border-t border-teal-700"
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.2 * idx, duration: 0.6 }}
                  >
                    <td className="p-4">{row[0]}</td>
                    <td className="p-4">{row[1]}</td>
                    <td className="p-4">{row[2]}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Get Started */}
        <section className="relative flex flex-col items-center justify-center py-16">
          <motion.h2
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-3xl font-extrabold text-center mb-6 text-white"
          >
            Ready to Watch Smarter?
          </motion.h2>
          <Link
            to="/get-started"
            className="px-12 py-4 rounded-full text-lg font-bold bg-gradient-to-r from-teal-400 to-blue-500 text-white shadow-xl hover:from-teal-500 hover:to-blue-600 transition-all"
          >
            Get Started
          </Link>
        </section>
      </div>
    </div>
  );
}