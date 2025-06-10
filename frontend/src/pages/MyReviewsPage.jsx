import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { MessageSquare, Star, ArrowLeft, Loader2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { getMyReviews } from "../Utils/api";

export default function MyReviewsPage() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    setLoading(true);
    getMyReviews()
      .then((res) => setReviews(res.reviews ?? []))
      .catch((e) => {
        setError(e?.message ?? "Failed to load reviews");
        setReviews([]);
      })
      .finally(() => setLoading(false));
  }, [isAuthenticated, user]);

  const posterUrl = (r) => {
    const p = r.poster_path;
    if (!p) return `https://via.placeholder.com/92x138/1a1a1a/666?text=No+Poster`;
    return p.startsWith("http") ? p : `https://image.tmdb.org/t/p/w92${p}`;
  };

  if (authLoading || !isAuthenticated || !user) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-teal-200">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-teal-400 hover:text-teal-300 mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <div className="flex items-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-xl bg-teal-500/20 flex items-center justify-center">
            <MessageSquare className="w-6 h-6 text-teal-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">My Reviews</h1>
            <p className="text-gray-400 text-sm">
              Your ratings and reviews — they help us recommend similar movies
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="py-12 text-center text-red-400">{error}</div>
        ) : reviews.length === 0 ? (
          <div className="py-16 text-center rounded-2xl border border-teal-500/20 bg-white/5">
            <MessageSquare className="w-12 h-12 text-teal-500/50 mx-auto mb-4" />
            <p className="text-gray-400 mb-2">No reviews yet</p>
            <p className="text-gray-500 text-sm mb-6">
              Review movies from your recommendations to see them here.
            </p>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-teal-500/20 text-teal-400 hover:bg-teal-500/30 transition-colors"
            >
              Go to Dashboard
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {reviews.map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex gap-4 p-4 rounded-xl border border-teal-500/20 bg-white/5 hover:bg-white/[0.07] transition-colors"
              >
                <img
                  src={posterUrl(r)}
                  alt={r.movie_title}
                  className="w-[92px] h-[138px] object-cover rounded-lg flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-white truncate">{r.movie_title}</h3>
                  <div className="flex items-center gap-2 mt-1 text-teal-300">
                    <Star className="w-4 h-4 fill-current" />
                    <span className="text-sm font-medium">{r.rating}/10</span>
                  </div>
                  {r.review_text && (
                    <p className="mt-2 text-gray-300 text-sm line-clamp-3">{r.review_text}</p>
                  )}
                  {r.created_at && (
                    <p className="mt-2 text-gray-500 text-xs">
                      {new Date(r.created_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
