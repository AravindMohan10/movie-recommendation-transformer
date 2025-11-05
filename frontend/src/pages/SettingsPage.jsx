import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Settings, ArrowLeft } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { getOnboardingStatus, resetOnboarding } from "../Utils/api";
import { useNavigate } from "react-router-dom";

export default function SettingsPage() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [onboardingStatus, setOnboardingStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    setLoadingStatus(true);
    getOnboardingStatus()
      .then(setOnboardingStatus)
      .catch(() => {})
      .finally(() => setLoadingStatus(false));
  }, [isAuthenticated, user]);

  const handleResetOnboarding = async () => {
    setError("");
    setResetting(true);
    try {
      await resetOnboarding();
      // Send user to dashboard to complete onboarding flow
      navigate("/dashboard");
    } catch (e) {
      setError(e?.message || "Failed to reset onboarding.");
    } finally {
      setResetting(false);
    }
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
      <div className="max-w-2xl mx-auto px-6 py-12">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-teal-400 hover:text-teal-300 mb-8 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <div className="flex items-center gap-3 mb-10">
          <div className="w-12 h-12 rounded-xl bg-teal-500/20 flex items-center justify-center">
            <Settings className="w-6 h-6 text-teal-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-white">Settings</h1>
            <p className="text-gray-400 text-sm">Preferences and account</p>
          </div>
        </div>

        <div className="rounded-2xl border border-teal-500/20 bg-white/5 p-6">
          <h2 className="text-lg font-semibold text-white mb-2">Preferences</h2>
          <p className="text-gray-400 text-sm mb-4">
            Update your onboarding preferences any time.
          </p>
          <div className="rounded-xl border border-teal-500/10 bg-black/30 p-4 mb-4">
            {loadingStatus ? (
              <p className="text-gray-500 text-sm">Loading preferences…</p>
            ) : onboardingStatus?.data?.preferences ? (
              <div className="text-sm text-gray-300 space-y-2">
                <div>
                  <span className="text-gray-500">Genres:</span>{" "}
                  {(onboardingStatus.data.preferences.genres || []).join(", ") || "—"}
                </div>
                <div>
                  <span className="text-gray-500">Favorite movies:</span>{" "}
                  {(onboardingStatus.data.preferences.favorite_movies || []).join(", ") || "—"}
                </div>
                <div>
                  <span className="text-gray-500">Moods:</span>{" "}
                  {(onboardingStatus.data.preferences.mood_preferences || []).join(", ") || "—"}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No preferences saved yet.</p>
            )}
          </div>
          {error ? <p className="text-rose-400 text-sm mb-3">{error}</p> : null}
          <button
            type="button"
            onClick={handleResetOnboarding}
            disabled={resetting}
            className="px-4 py-2 rounded-lg bg-teal-500/20 border border-teal-500/40 text-teal-200 hover:bg-teal-500/30 transition-colors disabled:opacity-60"
          >
            {resetting ? "Preparing onboarding…" : "Update preferences"}
          </button>
        </div>
      </div>
    </div>
  );
}
