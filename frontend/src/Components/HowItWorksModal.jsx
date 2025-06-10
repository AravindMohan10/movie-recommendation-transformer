import React from "react";
import { motion } from "framer-motion";
import { X, HelpCircle } from "lucide-react";

const sections = [
  {
    title: "Cold start",
    body: "With no likes or reviews yet, we fall back to popular or highly rated movies. Once you like, review, or add to your watchlist, we personalize.",
  },
  {
    title: "CF baseline",
    body: "Collaborative filtering (matrix factorization) recommends from similar users’ preferences. It’s the core of our scoring.",
  },
  {
    title: "Where RAG enters",
    body: "We run a RAG index over movie reviews (Chroma). We inject RAG-retrieved movies into the candidate set and rerank by review similarity. Your liked movies and your review text shape the RAG query.",
  },
  {
    title: "What we persist",
    body: "Likes, dislikes, favorites, reviews, and watchlist. These feed both CF and RAG.",
  },
  {
    title: "What’s not LLM-driven",
    body: "Recommendation scores come from CF + RAG. The LLM (Groq) only summarizes your taste for RAG queries; it doesn’t score movies.",
  },
];

export default function HowItWorksModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      onClick={onClose}
      className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.96, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl max-h-[85vh] rounded-2xl overflow-hidden border border-teal-500/30 bg-gradient-to-b from-[#1a1a1a] to-[#0a0a0a] shadow-2xl flex flex-col"
      >
          <div className="p-6 border-b border-teal-500/20 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center">
                  <HelpCircle className="w-5 h-5 text-teal-400" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">How recommendations work</h2>
                  <p className="text-sm text-gray-400 mt-0.5">System boundaries & what we use</p>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {sections.map((s, i) => (
              <div key={s.title}>
                <h3 className="text-sm font-semibold text-teal-300 uppercase tracking-wide mb-1.5">
                  {s.title}
                </h3>
                <p className="text-gray-300 text-sm leading-relaxed">{s.body}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </motion.div>
  );
}
