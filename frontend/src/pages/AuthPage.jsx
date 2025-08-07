// src/pages/AuthPage.jsx
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { login, signup, getMe } from "../Utils/api";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import CinematicBackdrop from "../Components/CinematicBackdrop";
import GlassOrb from "../Components/GlassOrb";

export default function AuthPage() {
  const { user, loading: authLoading, login: authLogin, authError } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  // Redirect if already logged in
  useEffect(() => {
    if (!authLoading && user) {
      navigate("/dashboard", { replace: true });
    }
  }, [user, authLoading, navigate]);

  const handleChange = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "signup") {
        if (!form.username || !form.email || !form.password)
          throw new Error("All fields required.");
        if (form.password !== form.confirmPassword)
          throw new Error("Passwords do not match.");
        if (form.password.length < 6)
          throw new Error("Password must be at least 6 characters.");
        // Check byte length (bcrypt limit: 72 bytes)
        const passwordBytes = new TextEncoder().encode(form.password).length;
        if (passwordBytes > 72) {
          throw new Error(`Password is too long (${passwordBytes} bytes). Maximum 72 bytes. Use at most 64 characters to be safe.`);
        }
        if (form.password.length > 64) {
          throw new Error("Password must be at most 64 characters.");
        }

        await signup({
          username: form.username,
          email: form.email,
          password: form.password,
        });

        setMode("login");
        setForm({ username: "", email: "", password: "", confirmPassword: "" });
        setError("Signup successful! Please sign in.");
      } else {
        if (!form.username || !form.password)
          throw new Error("All fields required.");

        console.log('🔐 Attempting login with:', form.username);
        const loginData = await login(form.username, form.password);
        console.log('✅ Login response:', loginData);
        
        // After successful login, fetch user data
        try {
          const userData = await getMe();
          console.log('✅ User data fetched:', userData);
          authLogin(userData);
        } catch (userError) {
          console.error('❌ Failed to fetch user data:', userError);
          // Still proceed with login even if user data fetch fails
        }

        navigate("/dashboard", { replace: true });
      }
    } catch (err) {
      // Handle backend connection errors gracefully
      if (err.message.includes('Failed to connect') || err.message.includes('fetch')) {
        setError("Unable to connect to server. Please check if the backend is running.");
      } else {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="relative min-h-screen w-full overflow-hidden font-sans text-white">
        <CinematicBackdrop />
        <div className="absolute inset-0 flex items-center justify-center z-20">
          <div className="text-center">
            <div className="w-12 h-12 border-2 border-teal-400 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <div className="text-lg text-teal-200 font-light">Checking authentication...</div>
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

      {/* Back to landing page */}
      <Link
        to="/"
        className="fixed top-7 right-8 z-40 px-4 py-2 rounded-full text-sm font-semibold bg-gradient-to-r from-teal-400/20 via-yellow-300/20 to-blue-400/20 backdrop-blur-md border border-teal-400/30 text-teal-200 hover:border-teal-300 hover:text-white transition-all"
      >
        ← Back Home
      </Link>

      {/* Auth Box */}
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
            {mode === "login" ? "Welcome Back" : "Join cine.ai"}
          </h2>
          
          <p className="text-center text-slate-300/80 text-sm mb-8">
            {mode === "login" 
              ? "Sign in to discover your perfect movie matches"
              : "Create your account and start your cinematic journey"
            }
          </p>

          {/* Backend Connection Error */}
          {authError && (
            <div className="mb-4 p-4 bg-red-900/30 backdrop-blur-sm border border-red-500/50 rounded-xl text-red-200 text-sm">
              <div className="font-semibold mb-1 flex items-center gap-2">
                <span>⚠️</span>
                <span>Connection Issue</span>
              </div>
              <div className="mt-1">{authError}</div>
              <div className="mt-2 text-xs text-red-300/80">
                Make sure the backend server is running on http://localhost:8000
              </div>
            </div>
          )}

          <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
            {mode === "signup" && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
              >
                <input
                  type="email"
                  name="email"
                  placeholder="Email address"
                  className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                  value={form.email}
                  onChange={handleChange}
                  autoComplete="email"
                  disabled={loading}
                  required
                />
              </motion.div>
            )}

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
            >
              <input
                type="text"
                name="username"
                placeholder={mode === "login" ? "Username or Email" : "Choose a username"}
                className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                value={form.username}
                onChange={handleChange}
                autoComplete="username"
                disabled={loading}
                required
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <input
                type="password"
                name="password"
                placeholder="Password (max 64 characters)"
                maxLength={64}
                className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                value={form.password}
                onChange={handleChange}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                disabled={loading}
                required
              />
            </motion.div>

            {mode === "signup" && (
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25 }}
              >
                <input
                  type="password"
                  name="confirmPassword"
                  placeholder="Confirm password (max 64 characters)"
                  maxLength={64}
                  className="w-full p-4 rounded-xl bg-black/40 backdrop-blur-sm border border-teal-700/30 text-white placeholder-slate-400 focus:outline-none focus:border-teal-400 focus:ring-2 focus:ring-teal-400/30 transition-all font-medium"
                  value={form.confirmPassword}
                  onChange={handleChange}
                  autoComplete="new-password"
                  disabled={loading}
                  required
                />
              </motion.div>
            )}

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className={`rounded-xl p-4 text-center text-sm ${
                  error.includes("successful")
                    ? "bg-green-900/30 border border-green-500/50 text-green-200 backdrop-blur-sm"
                    : "bg-red-900/30 border border-red-500/50 text-red-200 backdrop-blur-sm"
                }`}
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
                  Please wait...
                </div>
              ) : (
                mode === "login" ? "Sign In" : "Create Account"
              )}
            </motion.button>
          </form>

          <div className="mt-8 text-center space-y-3">
            {mode === "login" && (
              <div>
                <Link
                  to="/forgot-password"
                  className="text-teal-300 hover:text-teal-200 font-semibold underline decoration-teal-400/50 underline-offset-2 hover:decoration-teal-300 transition-colors text-sm"
                >
                  Forgot password?
                </Link>
              </div>
            )}
            {mode === "login" ? (
              <>
                <span className="text-slate-400">New to cine.ai? </span>
                <button
                  onClick={() => { setMode("signup"); setError(""); }}
                  className="text-teal-300 hover:text-teal-200 font-semibold underline decoration-teal-400/50 underline-offset-2 hover:decoration-teal-300 transition-colors"
                  disabled={loading}
                >
                  Create an account
                </button>
              </>
            ) : (
              <>
                <span className="text-slate-400">Already have an account? </span>
                <button
                  onClick={() => { setMode("login"); setError(""); }}
                  className="text-teal-300 hover:text-teal-200 font-semibold underline decoration-teal-400/50 underline-offset-2 hover:decoration-teal-300 transition-colors"
                  disabled={loading}
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}