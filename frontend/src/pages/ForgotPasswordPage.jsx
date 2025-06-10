// src/pages/ForgotPasswordPage.jsx
import React, { useState } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { forgotPassword } from "../Utils/api";
import CinematicBackdrop from "../Components/CinematicBackdrop";
import GlassOrb from "../Components/GlassOrb";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess(false);
    
    if (!email) {
      setError("Please enter your email address.");
      return;
    }

    setLoading(true);

    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

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

      {/* Back to login */}
      <Link
        to="/get-started"
        className="fixed top-7 right-8 z-40 px-4 py-2 rounded-full text-sm font-semibold bg-gradient-to-r from-teal-400/20 via-yellow-300/20 to-blue-400/20 backdrop-blur-md border border-teal-400/30 text-teal-200 hover:border-teal-300 hover:text-white transition-all"
      >
        ← Back to Login
      </Link>

      {/* Forgot Password Box */}
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
          <h2 className="text-3xl sm:text-4xl font-extrabold mb-2 text-center" style={{
            background: "linear-gradient(95deg, #00ffd5 10%, #fcff6c 50%, #8ed6ff 90%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            letterSpacing: "-1px",
            filter: "drop-shadow(0 4px 12px rgba(1, 255, 233, 0.3))",
          }}>
            Forgot Password?
          </h2>
          
          <p className="text-center text-slate-300/80 text-sm mb-8">
            No worries! Enter your email address and we'll send you a link to reset your password.
          </p>

          {success ? (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl p-6 bg-green-900/30 border border-green-500/50 text-green-200 backdrop-blur-sm text-center"
            >
              <div className="text-4xl mb-3">✉️</div>
              <div className="font-semibold mb-2">Check your email!</div>
              <div className="text-sm text-green-200/80">
                If an account with that email exists, a password reset link has been sent.
                Please check your inbox and follow the instructions.
              </div>
              <div className="mt-4 text-xs text-green-200/60">
                {process.env.NODE_ENV === 'development' && 
                  "Check the backend console for the reset link in development mode"}
              </div>
              <button
                onClick={() => navigate("/get-started")}
                className="mt-4 text-teal-300 hover:text-teal-200 font-semibold underline decoration-teal-400/50 underline-offset-2 hover:decoration-teal-300 transition-colors"
              >
                Back to Login
              </button>
            </motion.div>
          ) : (
            <>
              <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  <input
                    type="email"
                    name="email"
                    placeholder="Enter your email address"
                    className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
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
                      Sending reset link...
                    </div>
                  ) : (
                    "Send Reset Link"
                  )}
                </motion.button>
              </form>

              <div className="mt-6 text-center">
                <span className="text-slate-400">Remember your password? </span>
                <Link
                  to="/get-started"
                  className="text-teal-300 hover:text-teal-200 font-semibold underline decoration-teal-400/50 underline-offset-2 hover:decoration-teal-300 transition-colors"
                >
                  Sign in
                </Link>
              </div>
            </>
          )}
        </motion.div>
      </div>
    </div>
  );
}
