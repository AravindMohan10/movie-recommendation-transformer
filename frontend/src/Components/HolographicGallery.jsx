import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import { devLog, devWarn, devError } from '../Utils/logger';
import './HolographicGallery.css';

const HolographicGallery = ({ movies, onLike, onDislike, onFavorite, onReview, userInteractions = {}, onShare, onToggleWatchlist, isInWatchlist }) => {
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const containerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const MOVIES_PER_SLIDE = 3;
  const numSlides = Math.max(1, Math.ceil(movies.length / MOVIES_PER_SLIDE));
  const currentSlide = Math.min(Math.floor(currentIndex / MOVIES_PER_SLIDE), numSlides - 1);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  
  // LOCAL STATE to track interactions - this will update immediately
  const [localInteractions, setLocalInteractions] = useState({});
  const [forceUpdate, setForceUpdate] = useState(0);
  
  // Sync prop changes to local state
  useEffect(() => {
    devLog('🔄 HolographicGallery: userInteractions prop changed:', userInteractions);
    setLocalInteractions(userInteractions);
    setForceUpdate(prev => prev + 1); // Force re-render
  }, [userInteractions]);
  
  // Update local state when prop changes
  useEffect(() => {
    if (Object.keys(userInteractions).length > 0) {
      devLog('🔄 Syncing props to local state');
      setLocalInteractions({ ...userInteractions });
    }
  }, [userInteractions]);

  const handleMouseDown = (e) => {
    setIsDragging(true);
    setStartX(e.pageX - containerRef.current.offsetLeft);
    setScrollLeft(containerRef.current.scrollLeft);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - containerRef.current.offsetLeft;
    const walk = (x - startX) * 2;
    containerRef.current.scrollLeft = scrollLeft - walk;
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const cardWidth = 352;
      const scrollLeft = el.scrollLeft;
      const index = Math.round(scrollLeft / cardWidth);
      setCurrentIndex(Math.min(Math.max(0, index), movies.length - 1));
    };
    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, [movies.length]);

  const handleCardClick = (index) => {
    setCurrentIndex(index);
  };

  const scrollToSlide = (slideIndex) => {
    const cardWidth = 352;
    const scrollPos = Math.min(slideIndex * MOVIES_PER_SLIDE * cardWidth, (movies.length - 1) * cardWidth);
    if (containerRef.current) {
      containerRef.current.scrollTo({ left: scrollPos, behavior: 'smooth' });
    }
    setCurrentIndex(Math.min(slideIndex * MOVIES_PER_SLIDE, movies.length - 1));
  };

  const handleButtonClick = (action, movieTitle, movieId, e) => {
    e.preventDefault();
    e.stopPropagation();
    devLog('🔵 handleButtonClick called:', action, movieTitle, movieId);
    devLog('🔵 Handlers available:', { onLike: !!onLike, onDislike: !!onDislike, onFavorite: !!onFavorite });
    
    // IMMEDIATELY update local state for instant visual feedback
    const idStr = String(movieId);
    const idInt = parseInt(movieId, 10);
    
    setLocalInteractions(prev => {
      const newState = { ...prev };
      const currentState = newState[idStr] || newState[idInt] || {};
      
      if (action === 'like') {
        newState[idStr] = { ...currentState, like: true, dislike: false };
        newState[idInt] = { ...currentState, like: true, dislike: false };
      } else if (action === 'dislike') {
        newState[idStr] = { ...currentState, dislike: true, like: false };
        newState[idInt] = { ...currentState, dislike: true, like: false };
      } else if (action === 'favorite') {
        const newFavorite = !currentState.favorite;
        newState[idStr] = { ...currentState, favorite: newFavorite };
        newState[idInt] = { ...currentState, favorite: newFavorite };
      }
      
      devLog('🔵 Local state updated immediately:', newState);
      setForceUpdate(prev => prev + 1); // Force re-render
      return newState;
    });
    
    // Then call parent handlers
    switch (action) {
      case 'like':
        if (onLike) {
          devLog('🔵 Calling onLike handler');
          onLike(movieTitle);
        } else {
          console.error('❌ onLike handler is not defined!');
        }
        break;
      case 'dislike':
        if (onDislike) {
          devLog('🔵 Calling onDislike handler');
          onDislike(movieTitle);
        } else {
          console.error('❌ onDislike handler is not defined!');
        }
        break;
      case 'favorite':
        if (onFavorite) {
          devLog('🔵 Calling onFavorite handler');
          onFavorite(movieTitle);
        } else {
          console.error('❌ onFavorite handler is not defined!');
        }
        break;
      case 'review':
        if (onReview) {
          onReview(movieTitle);
        }
        break;
      default:
        console.error('❌ Unknown action:', action);
        break;
    }
  };

  return (
    <div className="holographic-gallery-container">
      <div 
        ref={containerRef}
        className="holographic-gallery"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
      >
        {movies.map((movie, index) => (
          <div
            key={index}
            className={`holographic-card ${hoveredIndex === index ? 'hovered' : ''} ${currentIndex === index ? 'active' : ''}`}
            onMouseEnter={() => setHoveredIndex(index)}
            onMouseLeave={() => setHoveredIndex(null)}
            onClick={() => handleCardClick(index)}
          >
            {/* Holographic Effect Layers */}
            <div className="card-glow"></div>
            <div className="card-reflection"></div>
            
            {/* Main Card Content */}
            <div className="card-content">
              {/* Movie Poster */}
              <div className="movie-poster">
                <img 
                  src={movie.poster_url || movie.image || 'https://via.placeholder.com/300x450/1a1a1a/666666?text=No+Image'} 
                  alt={movie.title}
                  onError={(e) => {
                    e.target.src = 'https://via.placeholder.com/300x450/1a1a1a/666666?text=No+Image';
                  }}
                />
                <div className="poster-overlay">
                  {movie.confidence != null && (
                    <div
                      className={`ai-confidence ai-confidence--${(movie.confidenceLevel || "medium").toLowerCase()}`}
                      title={movie.aiConfidence != null ? `${Math.round((movie.aiConfidence || 0) * 100)}% confidence` : undefined}
                    >
                      {movie.confidenceLevel === "high" ? "High confidence" : movie.confidenceLevel === "low" ? "Low confidence" : "Medium confidence"}
                    </div>
                  )}
                </div>
              </div>

              {/* Movie Info */}
              <div className="movie-info">
                <h3 className="movie-title line-clamp-2" title={movie.title || ''}>{movie.title}</h3>
                <div className="movie-meta">
                  <span className="movie-year">{movie.release_year || movie.year}</span>
                  <span className="movie-genre">{movie.genres ? movie.genres.join(', ') : movie.genre}</span>
                  <span className="movie-rating">★ {movie.rating}</span>
                </div>
                {(() => {
                  const mid = movie.id ?? movie.movie_id;
                  const inWl = isInWatchlist && isInWatchlist(mid);
                  const rev = Boolean((userInteractions[mid] || userInteractions[String(mid)] || {})['review']);
                  return (inWl || rev) ? (
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {inWl && (
                        <span className="px-2 py-0.5 rounded text-xs bg-teal-500/20 text-teal-300 border border-teal-500/30">
                          In watchlist
                        </span>
                      )}
                      {rev && (
                        <span className="px-2 py-0.5 rounded text-xs bg-amber-500/20 text-amber-200 border border-amber-500/30">
                          You reviewed
                        </span>
                      )}
                    </div>
                  ) : null;
                })()}
                {movie.director && movie.director !== 'Unknown' && (
                  <p className="movie-director">by {movie.director}</p>
                )}
                <p className="ai-reason">{movie.overview || movie.matchReason || ""}</p>
                {(movie.matchReason || movie.ai_reason) ? (
                  <p className="text-xs text-teal-400/90 mt-1.5" title={movie.matchReason || movie.ai_reason}>
                    <span className="font-medium text-teal-300">Why this recommendation?</span> {((movie.matchReason || movie.ai_reason) || "").slice(0, 120)}
                    {((movie.matchReason || movie.ai_reason) || "").length > 120 ? "…" : ""}
                  </p>
                ) : null}
              </div>

              {/* Interactive Buttons - Always visible for debugging */}
              <div className={`interactive-buttons visible`} style={{ opacity: 1, transform: 'translateY(0)', position: 'relative', zIndex: 100 }}>
                {(() => {
                  const movieId = movie.id || movie.movie_id;
                  if (!movieId) {
                    devWarn('⚠️ No movie ID for:', movie.title);
                    return null;
                  }
                  
                  const idStr = String(movieId);
                  const idInt = parseInt(movieId, 10);
                  
                  // Use LOCAL state first (immediate updates), fallback to props
                  const localState = localInteractions[movieId] || localInteractions[idStr] || localInteractions[idInt] || {};
                  const propState = userInteractions[movieId] || userInteractions[idStr] || userInteractions[idInt] || {};
                  
                  // Prefer local state (more up-to-date)
                  const movieInteractions = Object.keys(localState).length > 0 ? localState : propState;
                  
                  const isLiked = Boolean(movieInteractions.like);
                  const isDisliked = Boolean(movieInteractions.dislike);
                  const isFavorited = Boolean(movieInteractions.favorite);
                  const hasReviewed = Boolean(movieInteractions.review);
                  
                  // Log only on changes
                  if (forceUpdate > 0 || isLiked || isDisliked || isFavorited) {
                    devLog(`🎬 Rendering buttons for: ${movie.title} (ID: ${movieId}, forceUpdate: ${forceUpdate})`);
                    devLog(`   Local state:`, localState);
                    devLog(`   Prop state:`, propState);
                    devLog(`   Final state:`, { isLiked, isDisliked, isFavorited });
                  }
                  
                  // Force inline styles - use camelCase for React (glass-themed)
                  const likeStyle = {
                    background: isLiked ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: isLiked ? 'blur(10px) saturate(180%)' : 'none',
                    WebkitBackdropFilter: isLiked ? 'blur(10px) saturate(180%)' : 'none',
                    borderColor: isLiked ? 'rgba(34, 197, 94, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                    color: isLiked ? '#4ade80' : '#ffffff',
                    boxShadow: isLiked ? '0 0 30px rgba(34, 197, 94, 0.4), 0 0 60px rgba(34, 197, 94, 0.2), inset 0 0 20px rgba(34, 197, 94, 0.1)' : 'none',
                    borderWidth: '1px',
                    borderStyle: 'solid'
                  };
                  
                  const dislikeStyle = {
                    background: isDisliked ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: isDisliked ? 'blur(10px) saturate(180%)' : 'none',
                    WebkitBackdropFilter: isDisliked ? 'blur(10px) saturate(180%)' : 'none',
                    borderColor: isDisliked ? 'rgba(239, 68, 68, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                    color: isDisliked ? '#f87171' : '#ffffff',
                    boxShadow: isDisliked ? '0 0 30px rgba(239, 68, 68, 0.4), 0 0 60px rgba(239, 68, 68, 0.2), inset 0 0 20px rgba(239, 68, 68, 0.1)' : 'none',
                    borderWidth: '1px',
                    borderStyle: 'solid'
                  };
                  
                  const favoriteStyle = {
                    background: isFavorited ? 'rgba(251, 191, 36, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: isFavorited ? 'blur(10px) saturate(180%)' : 'none',
                    WebkitBackdropFilter: isFavorited ? 'blur(10px) saturate(180%)' : 'none',
                    borderColor: isFavorited ? 'rgba(251, 191, 36, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                    color: isFavorited ? '#fcd34d' : '#ffffff',
                    boxShadow: isFavorited ? '0 0 30px rgba(251, 191, 36, 0.4), 0 0 60px rgba(251, 191, 36, 0.2), inset 0 0 20px rgba(251, 191, 36, 0.1)' : 'none',
                    borderWidth: '1px',
                    borderStyle: 'solid'
                  };

                  const reviewStyle = {
                    background: hasReviewed ? 'rgba(20, 184, 166, 0.15)' : 'rgba(255, 255, 255, 0.1)',
                    backdropFilter: hasReviewed ? 'blur(10px) saturate(180%)' : 'none',
                    WebkitBackdropFilter: hasReviewed ? 'blur(10px) saturate(180%)' : 'none',
                    borderColor: hasReviewed ? 'rgba(20, 184, 166, 0.4)' : 'rgba(255, 255, 255, 0.1)',
                    color: hasReviewed ? '#2dd4bf' : '#ffffff',
                    boxShadow: hasReviewed ? '0 0 20px rgba(20, 184, 166, 0.3)' : 'none',
                    borderWidth: '1px',
                    borderStyle: 'solid'
                  };
                  
                  return (
                    <>
                      <button
                        type="button"
                        key={`like-btn-${movieId}-${isLiked}`}
                        className={`action-button like ${isLiked ? 'active' : ''}`}
                        onClick={(e) => {
                          devLog('🖱️ LIKE BUTTON CLICKED for', movie.title, movieId);
                          handleButtonClick('like', movie.title, movieId, e);
                        }}
                        title={isLiked ? 'Liked' : 'Like'}
                        style={likeStyle}
                      >
                        <svg width="22" height="22" viewBox="0 0 24 24" fill={isLiked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/>
                        </svg>
                      </button>
                      
                      <button
                        type="button"
                        key={`dislike-btn-${movieId}-${isDisliked}`}
                        className={`action-button dislike ${isDisliked ? 'active' : ''}`}
                        onClick={(e) => {
                          devLog('🖱️ DISLIKE BUTTON CLICKED for', movie.title, movieId);
                          handleButtonClick('dislike', movie.title, movieId, e);
                        }}
                        title={isDisliked ? 'Disliked' : 'Dislike'}
                        style={dislikeStyle}
                      >
                        <svg width="22" height="22" viewBox="0 0 24 24" fill={isDisliked ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18"/>
                          <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                      </button>
                      
                      <button
                        type="button"
                        key={`favorite-btn-${movieId}-${isFavorited}`}
                        className={`action-button favorite ${isFavorited ? 'active' : ''}`}
                        onClick={(e) => {
                          devLog('🖱️ FAVORITE BUTTON CLICKED for', movie.title, movieId);
                          handleButtonClick('favorite', movie.title, movieId, e);
                        }}
                        title={isFavorited ? 'Remove from Favorites' : 'Add to Favorites'}
                        style={favoriteStyle}
                      >
                        <svg width="22" height="22" viewBox="0 0 24 24" fill={isFavorited ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"/>
                        </svg>
                      </button>
                      
                      {onToggleWatchlist && (
                        <button
                          type="button"
                          className={`action-button watchlist ${isInWatchlist && isInWatchlist(movie.id) ? 'active' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleWatchlist(movie);
                          }}
                          title={isInWatchlist && isInWatchlist(movie.id) ? 'Remove from Watchlist' : 'Add to Watchlist'}
                        >
                          <svg width="22" height="22" viewBox="0 0 24 24" fill={isInWatchlist && isInWatchlist(movie.id) ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16Z"/>
                          </svg>
                        </button>
                      )}
                      
                      {onReview && (
                        <button
                          type="button"
                          className={`action-button review ${hasReviewed ? 'active' : ''}`}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onReview(movie);
                          }}
                          title={hasReviewed ? 'View your review' : 'Review'}
                          style={reviewStyle}
                        >
                          <MessageSquare className="w-[22px] h-[22px]" strokeWidth={2} />
                        </button>
                      )}
                      
                      {onShare && (
                        <button
                          type="button"
                          className="action-button share"
                          onClick={(e) => {
                            e.stopPropagation();
                            onShare(movie);
                          }}
                          title="Share"
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
          </div>
        ))}
      </div>
      
      {/* Navigation Dots: one per slide (not per movie) */}
      {numSlides > 1 && (
        <div className="navigation-dots">
          {Array.from({ length: numSlides }, (_, i) => (
            <button
              key={i}
              className={`nav-dot ${currentSlide === i ? 'active' : ''}`}
              onClick={() => scrollToSlide(i)}
              aria-label={`Go to slide ${i + 1} of ${numSlides}`}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default HolographicGallery; 