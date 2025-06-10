import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, X } from "lucide-react";

const ReviewModal = ({ isOpen, onClose, movie, existingReview, onSubmit }) => {
  const [rating, setRating] = useState(existingReview?.rating ?? 7);
  const [reviewText, setReviewText] = useState(existingReview?.review_text ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setRating(existingReview?.rating ?? 7);
      setReviewText(existingReview?.review_text ?? "");
      setError(null);
    }
  }, [isOpen, existingReview]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(movie?.id ?? movie?.movie_id, rating, reviewText.trim() || null);
      onClose?.();
    } catch (err) {
      setError(err?.message ?? "Failed to save review");
    } finally {
      setSubmitting(false);
    }
  };

  const posterUrl = movie?.poster_url || movie?.image || movie?.poster_path;
  const imgSrc = posterUrl?.startsWith("http")
    ? posterUrl
    : posterUrl
      ? `https://image.tmdb.org/t/p/w342${posterUrl}`
      : `https://via.placeholder.com/342x513/1a1a1a/666?text=No+Poster`;

  return (
    <AnimatePresence>
      {isOpen && (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[100] flex items-center justify-center p-4"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="relative w-full max-w-lg rounded-2xl overflow-hidden border border-teal-500/30 bg-gradient-to-b from-[#1a1a1a] to-[#0a0a0a] shadow-2xl"
        >
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center">
                  <MessageSquare className="w-5 h-5 text-teal-400" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">
                    {existingReview ? "Edit your review" : "Write a review"}
                  </h2>
                  <p className="text-gray-400 text-sm">{movie?.title}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex gap-4 mb-6">
              <img
                src={imgSrc}
                alt={movie?.title}
                className="w-24 h-36 object-cover rounded-lg"
              />
              <form onSubmit={handleSubmit} className="flex-1 flex flex-col gap-4">
                <div>
                  <label className="block text-sm font-medium text-teal-200 mb-2">
                    Rating (1–10)
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="0.5"
                    value={rating}
                    onChange={(e) => setRating(Number(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none bg-teal-900/50 accent-teal-400"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>1</span>
                    <span className="text-teal-400 font-medium">{rating}</span>
                    <span>10</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-teal-200 mb-2">
                    Your review
                  </label>
                  <textarea
                    value={reviewText}
                    onChange={(e) => setReviewText(e.target.value)}
                    placeholder="What did you think? Your review helps us recommend similar movies."
                    rows={4}
                    className="w-full px-3 py-2 rounded-lg bg-black/40 border border-teal-500/20 text-white placeholder-gray-500 focus:border-teal-400 focus:ring-1 focus:ring-teal-400/50 outline-none resize-none"
                  />
                </div>
                {error && (
                  <p className="text-sm text-red-400">{error}</p>
                )}
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 py-2.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-black font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {submitting ? (
                      <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    ) : (
                      <MessageSquare className="w-4 h-4" />
                    )}
                    {existingReview ? "Update review" : "Submit review"}
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2.5 rounded-lg border border-teal-500/30 text-teal-200 hover:bg-white/5 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </motion.div>
      </motion.div>
      )}
    </AnimatePresence>
  );
};

export default ReviewModal;
