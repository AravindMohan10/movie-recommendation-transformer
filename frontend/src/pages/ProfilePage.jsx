import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { User, ArrowLeft, MessageSquare, Bookmark, Loader2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { getMyReviews } from "../Utils/api";
import { getWatchlist } from "../Utils/api";

export default function ProfilePage() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const [reviewsCount, setReviewsCount] = useState(0);
  const [watchlistCount, setWatchlistCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    setLoading(true);
    Promise.all([getMyReviews(), getWatchlist()])
      .then(([r, w]) => {
        setReviewsCount(r.total ?? (r.reviews?.length ?? 0));
        setWatchlistCount(w.total ?? (w.watchlist?.length ?? 0));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isAuthenticated, user]);

  if (authLoading || !isAuthenticated || !user) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-teal-200">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-2xl mx-auto px-6 py-12">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-teal-400 hover:text-teal-300 mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <div className="flex items-center gap-4 mb-10">
          <div className="w-16 h-16 rounded-full bg-gradient-to-r from-teal-400 to-blue-500 flex items-center justify-center text-white text-2xl font-bold">
            {user.username?.[0]?.toUpperCase() || "U"}
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">{user.username}</h1>
            <p className="text-gray-400 text-sm">{user.email}</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-teal-400 animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <Link
              to="/my-reviews"
              className="flex items-center gap-3 p-4 rounded-xl border border-teal-500/20 bg-white/5 hover:bg-white/[0.07] transition-colors"
            >
              <MessageSquare className="w-6 h-6 text-teal-400" />
              <div>
                <p className="text-2xl font-semibold text-white">{reviewsCount}</p>
                <p className="text-sm text-gray-400">Reviews</p>
              </div>
            </Link>
            <Link
              to="/watchlist"
              className="flex items-center gap-3 p-4 rounded-xl border border-teal-500/20 bg-white/5 hover:bg-white/[0.07] transition-colors"
            >
              <Bookmark className="w-6 h-6 text-teal-400" />
              <div>
                <p className="text-2xl font-semibold text-white">{watchlistCount}</p>
                <p className="text-sm text-gray-400">Watchlist</p>
              </div>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
