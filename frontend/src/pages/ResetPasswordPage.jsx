// src/pages/ResetPasswordPage.jsx
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { verifyResetToken, resetPassword } from "../Utils/api";
import CinematicBackdrop from "../Components/CinematicBackdrop";
import GlassOrb from "../Components/GlassOrb";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();
  
  const [form, setForm] = useState({
    newPassword: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [tokenValid, setTokenValid] = useState(false);

  useEffect(() => {
    // Verify token on mount
    if (token) {
      console.log("🔑 Token received from URL:", token);
      console.log("🔑 Token length:", token.length);
      verifyToken();
    } else {
      setError("No reset token provided. Please use the link from your email.");
      setVerifying(false);
    }
  }, [token]);

  const verifyToken = async () => {
    try {
      console.log("🔍 Verifying token...");
      await verifyResetToken(token);
      console.log("✅ Token verified successfully");
      setTokenValid(true);
    } catch (err) {
      console.error("❌ Token verification failed:", err);
      setError(err.message || "Invalid or expired reset token. Please request a new one.");
    } finally {
      setVerifying(false);
    }
  };

  const handleChange = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    
    if (!form.newPassword || !form.confirmPassword) {
      setError("Please fill in all fields.");
      return;
    }

    if (form.newPassword.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    if (form.newPassword !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      await resetPassword(token, form.newPassword);
      setSuccess(true);
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate("/get-started", { replace: true });
      }, 3000);
    } catch (err) {
      setError(err.message || "Failed to reset password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (verifying) {
    return (
      <div className="relative min-h-screen w-full overflow-hidden font-sans text-white">
        <CinematicBackdrop />
        <div className="absolute inset-0 flex items-center justify-center z-20">
          <div className="text-center">
            <div className="w-12 h-12 border-2 border-teal-400 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <div className="text-lg text-teal-200 font-light">Verifying reset token...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden font-sans text-white">
      {/* Cinematic background */}
      <CinematicBackdrop />
      
      {/* Center Glass Orb */}
      <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
        <GlassOrb />
      </div>

      {/* Logo */}
      <Link
        to="/"
        className="fixed top-7 left-8 z-40 text-2xl font-extrabold bg-gradient-to-r from-teal-300 via-yellow-100 to-blue-200 bg-clip-text text-transparent select-none hover:opacity-80 transition-opacity"
        style={{ textDecoration: "none", letterSpacing: "-0.5px" }}
      >
        cine.<span className="text-white">ai</span>
      </Link>

      {/* Reset Password Box */}
      <div className="relative z-20 w-full min-h-screen flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md p-8 rounded-3xl bg-black/70 backdrop-blur-2xl shadow-2xl border border-teal-700/50"
          style={{
            boxShadow: "0 8px 32px rgba(0, 255, 233, 0.1), 0 2px 16px rgba(255, 255, 255, 0.05)"
          }}
        >
          {!tokenValid || error ? (
            <>
              <h2 className="text-3xl sm:text-4xl font-extrabold mb-2 text-center" style={{
                background: "linear-gradient(95deg, #ff6b6b 10%, #ee5a6f 50%, #ff4757 90%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                letterSpacing: "-1px",
                filter: "drop-shadow(0 4px 12px rgba(255, 107, 107, 0.3))",
              }}>
                Invalid Token
              </h2>
              
              <p className="text-center text-slate-300/80 text-sm mb-8">
                {error || "This reset link is invalid or has expired."}
              </p>

              <div className="rounded-xl p-6 bg-red-900/30 border border-red-500/50 text-red-200 backdrop-blur-sm text-center mb-6">
                <div className="text-4xl mb-3">🔒</div>
                <div className="text-sm mb-4">
                  Please request a new password reset link.
                </div>
              </div>

              <div className="flex gap-4">
                <Link
                  to="/forgot-password"
                  className="flex-1 text-center font-bold py-3 rounded-xl shadow-lg transition-all bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 text-gray-900 tracking-wide disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Request New Link
                </Link>
                <Link
                  to="/get-started"
                  className="flex-1 text-center font-semibold py-3 rounded-xl border border-teal-400/30 text-teal-200 hover:border-teal-300 hover:text-white transition-all"
                >
                  Back to Login
                </Link>
              </div>
            </>
          ) : success ? (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center"
            >
              <div className="text-6xl mb-4">✅</div>
              <h2 className="text-3xl sm:text-4xl font-extrabold mb-4" style={{
                background: "linear-gradient(95deg, #00ffd5 10%, #fcff6c 50%, #8ed6ff 90%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                letterSpacing: "-1px",
              }}>
                Password Reset!
              </h2>
              
              <div className="rounded-xl p-6 bg-green-900/30 border border-green-500/50 text-green-200 backdrop-blur-sm text-center mb-6">
                <div className="font-semibold mb-2">Your password has been successfully reset.</div>
                <div className="text-sm text-green-200/80">
                  Redirecting to login page...
                </div>
              </div>

              <Link
                to="/get-started"
                className="inline-block font-bold py-3 px-6 rounded-xl shadow-lg transition-all bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 text-gray-900 tracking-wide"
              >
                Go to Login
              </Link>
            </motion.div>
          ) : (
            <>
              <h2 className="text-3xl sm:text-4xl font-extrabold mb-2 text-center" style={{
                background: "linear-gradient(95deg, #00ffd5 10%, #fcff6c 50%, #8ed6ff 90%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                letterSpacing: "-1px",
                filter: "drop-shadow(0 4px 12px rgba(1, 255, 233, 0.3))",
              }}>
                Reset Password
              </h2>
              
              <p className="text-center text-slate-300/80 text-sm mb-8">
                Enter your new password below.
              </p>

              <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <input
                    type="password"
                    name="newPassword"
                    placeholder="New password"
                    className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                    value={form.newPassword}
                    onChange={handleChange}
                    autoComplete="new-password"
                    disabled={loading}
                    required
                  />
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 }}
                >
                  <input
                    type="password"
                    name="confirmPassword"
                    placeholder="Confirm new password"
                    className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    autoComplete="new-password"
                    disabled={loading}
                    required
                  />
                </motion.div>

                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="rounded-xl p-4 text-center text-sm bg-red-900/30 border border-red-500/50 text-red-200 backdrop-blur-sm"
                  >
                    {error}
                  </motion.div>
                )}

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={loading}
                  className="mt-2 font-bold py-4 rounded-xl shadow-lg transition-all bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 text-gray-900 tracking-wide text-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                  style={{
                    boxShadow: "0 0 20px 4px rgba(1, 255, 233, 0.2), 0 4px 16px rgba(255, 255, 255, 0.1)",
                    letterSpacing: "-.5px",
                  }}
                >
                  {loading ? (
                    <div className="flex items-center justify-center">
                      <div className="w-5 h-5 border-2 border-gray-900 border-t-transparent rounded-full animate-spin mr-2"></div>
                      Resetting password...
                    </div>
                  ) : (
                    "Reset Password"
                  )}
                </motion.button>
              </form>

              <div className="mt-6 text-center">
                <Link
                  to="/get-started"
                  className="text-teal-300 hover:text-teal-200 font-semibold underline decoration-teal-400/50 underline-offset-2 hover:decoration-teal-300 transition-colors"
                >
                  ← Back to Login
                </Link>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
