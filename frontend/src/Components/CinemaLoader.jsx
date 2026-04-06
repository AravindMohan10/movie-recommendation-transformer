import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './CinemaLoader.css';

const LOADING_TEXTS = [
  "Curating your next watch…",
  "Reading your recent taste signals…",
  "Balancing familiar picks with discovery…",
  "Composing a better lineup for tonight…",
  "Finalizing your recommendation set…",
];

export default function CinemaLoader() {
  const [textIndex, setTextIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTextIndex((prev) => (prev + 1) % LOADING_TEXTS.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="cinema-loader">
      <div className="cinema-loader__content">
        <motion.div
          className="cinema-loader__pulse-ring"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35 }}
        />

        <AnimatePresence mode="wait">
          <motion.p
            key={textIndex}
            className="cinema-loader__text"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.3 }}
          >
            {LOADING_TEXTS[textIndex]}
          </motion.p>
        </AnimatePresence>

        <div className="cinema-loader__skeleton-row">
          {[1, 2, 3].map((i) => (
            <div key={i} className="cinema-loader__skeleton-card">
              <div className="cinema-loader__skeleton-poster" />
              <div className="cinema-loader__skeleton-meta">
                <div className="cinema-loader__skeleton-line cinema-loader__skeleton-line--title" />
                <div className="cinema-loader__skeleton-line cinema-loader__skeleton-line--sub" />
                <div className="cinema-loader__skeleton-line cinema-loader__skeleton-line--sub-short" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
