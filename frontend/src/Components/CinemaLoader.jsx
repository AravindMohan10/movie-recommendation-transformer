import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './CinemaLoader.css';

const LOADING_TEXTS = [
  "Popcorn's ready. Curating your picks…",
  "Rolling cameras. Finding your next favorite…",
  "Lights, camera, recommendations…",
  "Syncing with cinephiles like you…",
  "Scanning 50,000+ titles for you…",
  "Director's cut incoming…",
  "Bypassing the algorithm fatigue…",
  "Matching you with hidden gems…",
  "Consulting the taste gods…",
  "Loading the good stuff…",
  "Adjusting the lens on your taste profile…",
  "Splicing together your perfect lineup…",
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
        {/* Director's slate */}
        <motion.div
          className="cinema-loader__slate"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="cinema-loader__slate-top" />
          <div className="cinema-loader__slate-board">
            <span className="cinema-loader__slate-scene">SCENE 1</span>
            <span className="cinema-loader__slate-dot">·</span>
            <span className="cinema-loader__slate-take">TAKE 1</span>
          </div>
          <div className="cinema-loader__slate-rec">
            <span className="cinema-loader__slate-rec-dot" />
            REC
          </div>
        </motion.div>

        {/* Popcorn kettle + popping kernels */}
        <motion.div
          className="cinema-loader__popcorn"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <div className="cinema-loader__kettle">
            <div className="cinema-loader__kettle-body" />
            <div className="cinema-loader__kettle-handle" />
            <div className="cinema-loader__kettle-top" />
            {/* Popping kernels - positioned around kettle opening */}
            {[
              { x: 15, y: 45 }, { x: 40, y: 40 }, { x: 65, y: 42 }, { x: 88, y: 46 },
              { x: 25, y: 28 }, { x: 52, y: 25 }, { x: 75, y: 30 },
            ].map((pos, i) => (
              <div
                key={i}
                className="cinema-loader__kernel"
                style={{
                  '--delay': `${i * 0.12}s`,
                  '--kernel-x': `${pos.x}%`,
                  '--kernel-y': `${pos.y}%`,
                }}
              >
                🍿
              </div>
            ))}
          </div>
        </motion.div>

        {/* Rotating text */}
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

        {/* Subtle skeleton preview */}
        <div className="cinema-loader__skeleton-row">
          {[1, 2, 3].map((i) => (
            <div key={i} className="cinema-loader__skeleton-card" />
          ))}
        </div>
      </div>
    </div>
  );
}
