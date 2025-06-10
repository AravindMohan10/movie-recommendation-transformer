import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, X, Star, PenLine, Loader2 } from "lucide-react";
import { getMovieReviews, submitReview } from "../Utils/api";
import ReviewModal from "./ReviewModal";

const MovieReviewsModal = ({
  isOpen,
  onClose,
  movie,
  existingReview: existingReviewProp,
  onReviewSubmitted,
}) => {
  const [data, setData] = useState({ reviews: [], movie_title: "" });
  const [loading, setLoading] = useState(false);
  const [showReviewForm, setShowReviewForm] = useState(false);
  const [myReview, setMyReview] = useState(existingReviewProp ?? null);

  useEffect(() => {
    if (!isOpen || !movie) return;
    setLoading(true);
    const id = movie.id ?? movie.movie_id;
    getMovieReviews(id)
      .then((res) => {
        setData({
          reviews: res.reviews ?? [],
          movie_title: res.movie_title ?? movie.title,
        });
        const own = (res.reviews ?? []).find((r) => r.is_you);
        setMyReview(own ?? null);
      })
      .catch(() => setData({ reviews: [], movie_title: movie.title }))
      .finally(() => setLoading(false));
  }, [isOpen, movie?.id, movie?.movie_id, movie?.title]);

  if (!isOpen) return null;

  const handleSubmitReview = async (movieId, rating, reviewText) => {
    await submitReview(movieId, rating, reviewText);
    setShowReviewForm(false);
    onReviewSubmitted?.();
    const id = movie?.id ?? movie?.movie_id;
    const res = await getMovieReviews(id);
    setData({
      reviews: res.reviews ?? [],
      movie_title: res.movie_title ?? movie?.title,
    });
    const own = (res.reviews ?? []).find((r) => r.is_you);
    setMyReview(own ?? null);
  };

  const others = (data.reviews ?? []).filter((r) => !r.is_you);

  return (
    <>
      <AnimatePresence>
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
            className="relative w-full max-w-2xl max-h-[85vh] rounded-2xl overflow-hidden border border-teal-500/30 bg-gradient-to-b from-[#1a1a1a] to-[#0a0a0a] shadow-2xl flex flex-col"
          >
            <div className="p-6 border-b border-teal-500/20 flex-shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center">
                    <MessageSquare className="w-5 h-5 text-teal-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-white">
                      Reviews — {data.movie_title || movie?.title}
                    </h2>
                    <p className="text-gray-400 text-sm">
                      Your review shapes better recommendations
                    </p>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
                </div>
              ) : (
                <>
                  <section>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-medium text-teal-200 uppercase tracking-wider">
                        Your review
                      </h3>
                      <button
                        onClick={() => setShowReviewForm(true)}
                        className="flex items-center gap-1.5 text-sm text-teal-400 hover:text-teal-300 transition-colors"
                      >
                        <PenLine className="w-4 h-4" />
                        {myReview ? "Edit" : "Write review"}
                      </button>
                    </div>
                    {myReview ? (
                      <div className="p-4 rounded-xl bg-teal-500/10 border border-teal-500/20">
                        <div className="flex items-center gap-2 mb-2">
                          <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                          <span className="text-white font-medium">
                            {myReview.rating}/10
                          </span>
                        </div>
                        <p className="text-gray-200 text-sm whitespace-pre-wrap">
                          {myReview.review_text || "No text."}
                        </p>
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl bg-white/5 border border-teal-500/10 text-gray-500 text-sm">
                        You haven’t reviewed this movie yet.
                      </div>
                    )}
                  </section>

                  <section>
                    <h3 className="text-sm font-medium text-teal-200 uppercase tracking-wider mb-3">
                      Other reviews
                    </h3>
                    {others.length === 0 ? (
                      <div className="p-4 rounded-xl bg-white/5 border border-teal-500/10 text-gray-500 text-sm">
                        No other reviews yet.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {others.map((r) => (
                          <div
                            key={r.id}
                            className="p-4 rounded-xl bg-white/5 border border-teal-500/10"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-teal-300 font-medium text-sm">
                                {r.username}
                              </span>
                              <div className="flex items-center gap-1">
                                <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                                <span className="text-white text-sm">
                                  {r.rating}/10
                                </span>
                              </div>
                            </div>
                            <p className="text-gray-300 text-sm whitespace-pre-wrap">
                              {r.review_text || "—"}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      </AnimatePresence>

      <ReviewModal
        isOpen={showReviewForm}
        onClose={() => setShowReviewForm(false)}
        movie={movie}
        existingReview={myReview}
        onSubmit={handleSubmitReview}
      />
    </>
  );
};

export default MovieReviewsModal;
