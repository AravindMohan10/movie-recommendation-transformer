import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './HolographicGallery.css';

const SurpriseMeModal = ({ isOpen, onClose, movies, loading, onLike, onDislike, onFavorite, onReview, onShare, onToggleWatchlist, isInWatchlist, userInteractions = {} }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  if (!isOpen) return null;

  const currentMovie = movies[currentIndex] || null;

  const nextMovie = () => {
    setCurrentIndex((prev) => (prev + 1) % movies.length);
  };

  const prevMovie = () => {
    setCurrentIndex((prev) => (prev - 1 + movies.length) % movies.length);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          >
            {/* Modal Content - Matching holographic card style */}
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              className="relative w-full max-w-4xl max-h-[90vh] rounded-2xl overflow-hidden"
              style={{
                background: 'linear-gradient(145deg, #1a1a1a, #0a0a0a)',
                border: isHovered ? '1px solid #01ffe9' : '1px solid #333',
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
                boxShadow: isHovered 
                  ? '0 25px 50px rgba(0, 0, 0, 0.5), 0 0 0 2px rgba(1, 255, 233, 0.2), 0 0 30px rgba(1, 255, 233, 0.3)'
                  : 'none',
                transform: isHovered ? 'translateY(-4px)' : 'none'
              }}
            >
              {/* Holographic glow effect - only on hover */}
              {isHovered && (
                <div
                  className="absolute top-0 left-0 right-0 bottom-0 pointer-events-none z-0"
                  style={{
                    background: 'linear-gradient(45deg, transparent 30%, rgba(1, 255, 233, 0.1) 50%, transparent 70%)',
                    animation: 'glow-sweep 2s ease-in-out infinite',
                    opacity: 1,
                    transition: 'opacity 0.3s ease'
                  }}
                />
              )}
              {/* Card reflection on hover */}
              {isHovered && (
                <div
                  className="absolute top-0 left-0 right-0 bottom-0 pointer-events-none z-0"
                  style={{
                    background: 'linear-gradient(135deg, transparent 0%, rgba(255, 255, 255, 0.05) 50%, transparent 100%)',
                    opacity: 1,
                    transition: 'opacity 0.3s ease'
                  }}
                />
              )}
              {/* Close Button - Matching gallery style */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 z-50 p-2 rounded-full backdrop-blur-sm border border-cyan-400/30 hover:border-cyan-400/50 transition-colors flex items-center justify-center"
                style={{
                  background: 'rgba(0, 0, 0, 0.8)',
                  color: '#01ffe9'
                }}
                aria-label="Close"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>

              {/* Header - Matching gallery style */}
              <div className="p-6 border-b relative z-10" style={{ borderColor: 'rgba(1, 255, 233, 0.2)' }}>
                <h2 className="text-3xl font-bold mb-2" style={{ color: '#01ffe9' }}>
                  🎬 Surprise Me!
                </h2>
                <p className="text-gray-400 mt-2">
                  Discover {movies.length} high-quality films worth watching
                </p>
              </div>

              {/* Content */}
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] relative z-10">
                {loading ? (
                  <div className="flex items-center justify-center py-20">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2" style={{ borderColor: '#01ffe9', borderTopColor: 'transparent' }}></div>
                  </div>
                ) : movies.length === 0 ? (
                  <div className="text-center py-20 text-gray-400">
                    No surprises found. Try again later!
                  </div>
                ) : currentMovie ? (
                  <motion.div
                    key={currentIndex}
                    initial={{ opacity: 0, x: 50 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -50 }}
                    className="flex flex-col md:flex-row gap-6"
                  >
                    {/* Movie Poster - Matching gallery style */}
                    <div className="flex-shrink-0 relative overflow-hidden rounded-xl" style={{ background: '#1a1a1a' }}>
                      {currentMovie.poster || currentMovie.image ? (
                        <>
                          <img
                            src={currentMovie.poster || currentMovie.image}
                            alt={currentMovie.title}
                            className="w-full md:w-64 h-auto rounded-xl"
                            style={{ maxHeight: '400px', objectFit: 'cover' }}
                            onError={(e) => { e.target.onerror = null; e.target.src = "https://via.placeholder.com/256x384/1a1a1a/666666?text=No+Poster"; }}
                          />
                          {/* Poster overlay effect matching gallery */}
                          <div 
                            className="absolute inset-0 pointer-events-none rounded-xl"
                            style={{
                              background: 'linear-gradient(to bottom, transparent 0%, rgba(0, 0, 0, 0.3) 50%, rgba(0, 0, 0, 0.7) 100%)'
                            }}
                          />
                        </>
                      ) : (
                        <div className="w-full md:w-64 h-96 flex items-center justify-center rounded-xl" style={{ background: 'linear-gradient(145deg, #1a1a1a, #0a0a0a)' }}>
                          <span className="text-gray-500">No Poster</span>
                        </div>
                      )}
                    </div>

                    {/* Movie Info */}
                    <div className="flex-1 space-y-4">
                      <div>
                        <h3 className="text-3xl font-bold mb-2" style={{ color: '#ffffff' }}>
                          {currentMovie.title}
                        </h3>
                        {currentMovie.director && (
                          <p className="text-lg" style={{ color: '#01ffe9' }}>
                            Directed by {currentMovie.director}
                          </p>
                        )}
                      </div>

                      {/* Rating Badge - Matching gallery style */}
                      <div className="flex items-center gap-4">
                        <div 
                          className="px-4 py-2 rounded-full backdrop-blur-sm border"
                          style={{
                            background: 'rgba(0, 0, 0, 0.8)',
                            borderColor: 'rgba(1, 255, 233, 0.3)',
                            color: '#01ffe9'
                          }}
                        >
                          <span className="font-bold text-lg">
                            ⭐ {currentMovie.rating?.toFixed(1) || currentMovie.vote_average?.toFixed(1) || 'N/A'}
                          </span>
                        </div>
                        {currentMovie.vote_count && (
                          <span className="text-gray-400 text-sm">
                            {currentMovie.vote_count.toLocaleString()} ratings
                          </span>
                        )}
                      </div>

                      {/* Explanation - Matching gallery style */}
                      {currentMovie.explanation && (
                        <div 
                          className="p-4 rounded-lg backdrop-blur-sm border"
                          style={{
                            background: 'rgba(1, 255, 233, 0.1)',
                            borderColor: 'rgba(1, 255, 233, 0.2)'
                          }}
                        >
                          <p className="text-sm" style={{ color: '#01ffe9' }}>
                            {currentMovie.explanation}
                          </p>
                        </div>
                      )}

                      {/* Overview */}
                      {currentMovie.overview && (
                        <div>
                          <p className="text-gray-300 leading-relaxed">
                            {currentMovie.overview}
                          </p>
                        </div>
                      )}

                      {/* Action Buttons - Exact same as gallery cards */}
                      <div className="flex gap-2 pt-4 justify-center flex-wrap" style={{ 
                        display: 'flex', 
                        gap: '0.5rem', 
                        justifyContent: 'center',
                        paddingTop: '1rem'
                      }}>
                        {/* Get interaction state for this movie */}
                        {(() => {
                          const movieId = currentMovie.movie_id || currentMovie.id;
                          const idStr = String(movieId);
                          const idInt = parseInt(movieId);
                          const movieInteractions = userInteractions[idStr] || userInteractions[idInt] || {};
                          const isLiked = Boolean(movieInteractions.like);
                          const isDisliked = Boolean(movieInteractions.dislike);
                          const isFavorited = Boolean(movieInteractions.favorite);
                          const inWatchlist = isInWatchlist && isInWatchlist(movieId);
                          
                          // Button styles matching gallery - circular buttons with same dimensions
                          const baseButtonStyle = {
                            width: '44px',
                            height: '44px',
                            borderRadius: '50%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                            border: '1px solid',
                            borderStyle: 'solid'
                          };
                          
                          const likeStyle = {
                            ...baseButtonStyle,
                            background: isLiked ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: isLiked ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            WebkitBackdropFilter: isLiked ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            borderColor: isLiked ? 'rgba(34, 197, 94, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                            color: isLiked ? '#4ade80' : '#ffffff',
                            boxShadow: isLiked ? '0 0 30px rgba(34, 197, 94, 0.4), 0 0 60px rgba(34, 197, 94, 0.2), inset 0 0 20px rgba(34, 197, 94, 0.1)' : 'none'
                          };
                          
                          const dislikeStyle = {
                            ...baseButtonStyle,
                            background: isDisliked ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: isDisliked ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            WebkitBackdropFilter: isDisliked ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            borderColor: isDisliked ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                            color: isDisliked ? '#f87171' : '#ffffff',
                            boxShadow: isDisliked ? '0 0 30px rgba(239, 68, 68, 0.4), 0 0 60px rgba(239, 68, 68, 0.2), inset 0 0 20px rgba(239, 68, 68, 0.1)' : 'none'
                          };
                          
                          const favoriteStyle = {
                            ...baseButtonStyle,
                            background: isFavorited ? 'rgba(251, 191, 36, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: isFavorited ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            WebkitBackdropFilter: isFavorited ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            borderColor: isFavorited ? 'rgba(251, 191, 36, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                            color: isFavorited ? '#fcd34d' : '#ffffff',
                            boxShadow: isFavorited ? '0 0 30px rgba(251, 191, 36, 0.4), 0 0 60px rgba(251, 191, 36, 0.2), inset 0 0 20px rgba(251, 191, 36, 0.1)' : 'none'
                          };
                          
                          const watchlistStyle = {
                            ...baseButtonStyle,
                            background: inWatchlist ? 'rgba(147, 51, 234, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: inWatchlist ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            WebkitBackdropFilter: inWatchlist ? 'blur(10px) saturate(180%)' : 'blur(10px)',
                            borderColor: inWatchlist ? 'rgba(147, 51, 234, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                            color: inWatchlist ? '#a78bfa' : '#ffffff',
                            boxShadow: inWatchlist ? '0 0 30px rgba(147, 51, 234, 0.4), 0 0 60px rgba(147, 51, 234, 0.2), inset 0 0 20px rgba(147, 51, 234, 0.1)' : 'none'
                          };
                          
                          const reviewStyle = {
                            ...baseButtonStyle,
                            background: 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: 'blur(10px)',
                            WebkitBackdropFilter: 'blur(10px)',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            color: '#ffffff'
                          };
                          
                          const shareStyle = {
                            ...baseButtonStyle,
                            background: 'rgba(255, 255, 255, 0.1)',
                            backdropFilter: 'blur(10px)',
                            WebkitBackdropFilter: 'blur(10px)',
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            color: '#ffffff'
                          };
                          
                          return (
                            <>
                              {/* Like Button */}
                              <button
                                type="button"
                                className={`action-button like ${isLiked ? 'active' : ''}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (onLike) onLike(currentMovie.title);
                                }}
                                title={isLiked ? 'Liked' : 'Like'}
                                style={likeStyle}
                              >
                                <svg width="22" height="22" viewBox="0 0 24 24" fill={isLiked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/>
                                </svg>
                              </button>
                              
                              {/* Dislike Button */}
                              <button
                                type="button"
                                className={`action-button dislike ${isDisliked ? 'active' : ''}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (onDislike) onDislike(currentMovie.title);
                                }}
                                title={isDisliked ? 'Disliked' : 'Dislike'}
                                style={dislikeStyle}
                              >
                                <svg width="22" height="22" viewBox="0 0 24 24" fill={isDisliked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <line x1="18" y1="6" x2="6" y2="18"/>
                                  <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                              </button>
                              
                              {/* Favorite Button */}
                              <button
                                type="button"
                                className={`action-button favorite ${isFavorited ? 'active' : ''}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (onFavorite) onFavorite(currentMovie.title);
                                }}
                                title={isFavorited ? 'Remove from Favorites' : 'Add to Favorites'}
                                style={favoriteStyle}
                              >
                                <svg width="22" height="22" viewBox="0 0 24 24" fill={isFavorited ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/>
                                </svg>
                              </button>
                              
                              {/* Watchlist Button */}
                              {onToggleWatchlist && (
                                <button
                                  type="button"
                                  className={`action-button watchlist ${inWatchlist ? 'active' : ''}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onToggleWatchlist(currentMovie);
                                  }}
                                  title={inWatchlist ? 'Remove from Watchlist' : 'Add to Watchlist'}
                                  style={watchlistStyle}
                                >
                                  <svg width="22" height="22" viewBox="0 0 24 24" fill={inWatchlist ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z"/>
                                  </svg>
                                </button>
                              )}
                              
                              {/* Review Button */}
                              {onReview && (
                                <button
                                  type="button"
                                  className="action-button review"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onReview(currentMovie);
                                  }}
                                  title="Review"
                                  style={reviewStyle}
                                >
                                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M7 9H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V11a2 2 0 0 0-2-2h-2"/>
                                    <rect x="3" y="3" width="12" height="8" rx="2"/>
                                  </svg>
                                </button>
                              )}
                              
                              {/* Share Button */}
                              {onShare && (
                                <button
                                  type="button"
                                  className="action-button share"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onShare(currentMovie);
                                  }}
                                  title="Share"
                                  style={shareStyle}
                                >
                                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>
                                    <polyline points="16 6 12 2 8 6"/>
                                    <line x1="12" y1="2" x2="12" y2="15"/>
                                  </svg>
                                </button>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  </motion.div>
                ) : null}
              </div>

              {/* Navigation - Matching gallery style */}
              {movies.length > 1 && (
                <div 
                  className="p-6 border-t flex items-center justify-between relative z-10"
                  style={{ borderColor: 'rgba(1, 255, 233, 0.2)' }}
                >
                  {/* Previous Button */}
                  <button
                    onClick={prevMovie}
                    disabled={loading}
                    className="px-6 py-2 rounded-lg transition-colors backdrop-blur-sm border disabled:opacity-50"
                    style={{
                      background: 'rgba(0, 0, 0, 0.5)',
                      borderColor: 'rgba(1, 255, 233, 0.3)',
                      color: '#01ffe9'
                    }}
                  >
                    ← Previous
                  </button>

                  {/* Dots Indicator */}
                  <div className="flex gap-2">
                    {movies.map((_, index) => (
                      <button
                        key={index}
                        onClick={() => setCurrentIndex(index)}
                        className="rounded-full transition-all"
                        style={{
                          width: index === currentIndex ? '32px' : '8px',
                          height: '8px',
                          background: index === currentIndex ? '#01ffe9' : 'rgba(255, 255, 255, 0.3)'
                        }}
                        aria-label={`Go to movie ${index + 1}`}
                      />
                    ))}
                  </div>

                  {/* Next Button */}
                  <button
                    onClick={nextMovie}
                    disabled={loading}
                    className="px-6 py-2 rounded-lg transition-colors backdrop-blur-sm border disabled:opacity-50"
                    style={{
                      background: 'rgba(0, 0, 0, 0.5)',
                      borderColor: 'rgba(1, 255, 233, 0.3)',
                      color: '#01ffe9'
                    }}
                  >
                    Next →
                  </button>
                </div>
              )}
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SurpriseMeModal;

