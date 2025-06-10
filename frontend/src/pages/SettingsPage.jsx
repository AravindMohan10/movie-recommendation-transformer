import React from "react";
import { Link } from "react-router-dom";
import { Settings, ArrowLeft } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function SettingsPage() {
  const { user, isAuthenticated, loading: authLoading } = useAuth();

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
          <p className="text-gray-400 text-sm">
            More options (notifications, theme, etc.) can be added here later.
          </p>
          <p className="text-gray-500 text-xs mt-2">
            For now, use Profile to view your stats or Dashboard to manage recommendations.
          </p>
        </div>
      </div>
    </div>
  );
}
