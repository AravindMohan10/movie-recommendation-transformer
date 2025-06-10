import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { updateOnboarding } from '../Utils/api';
import './OnboardingFlow.css';

const OnboardingFlow = ({ onComplete, onSkip }) => {
  const [currentStage, setCurrentStage] = useState(1);
  const [selections, setSelections] = useState({
    genres: [],
    favorite_movies: [],
    mood_preferences: []
  });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const stages = [
    {
      id: 1,
      title: "What genres do you enjoy?",
      subtitle: "Select all that apply",
      type: "genre_selection",
      maxSelections: 5,
      options: [
        "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
        "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
        "Romance", "Sci-Fi", "Thriller", "War", "Western"
      ]
    },
    {
      id: 2,
      title: "What are your favorite movies?",
      subtitle: "Search and select movies you love (including niche films!)",
      type: "movie_selection",
      maxSelections: 5,
      options: [
        { id: 1, title: "The Shawshank Redemption (1994)", genre: "Drama" },
        { id: 2, title: "The Godfather (1972)", genre: "Crime" },
        { id: 3, title: "The Dark Knight (2008)", genre: "Action" },
        { id: 4, title: "Pulp Fiction (1994)", genre: "Crime" },
        { id: 5, title: "Fight Club (1999)", genre: "Drama" },
        { id: 6, title: "Inception (2010)", genre: "Sci-Fi" },
        { id: 7, title: "The Matrix (1999)", genre: "Sci-Fi" },
        { id: 8, title: "Goodfellas (1990)", genre: "Crime" },
        { id: 9, title: "The Silence of the Lambs (1991)", genre: "Thriller" },
        { id: 10, title: "Interstellar (2014)", genre: "Sci-Fi" },
        { id: 11, title: "The Departed (2006)", genre: "Crime" },
        { id: 12, title: "Gladiator (2000)", genre: "Action" },
        { id: 13, title: "The Prestige (2006)", genre: "Drama" },
        { id: 14, title: "The Lion King (1994)", genre: "Animation" },
        { id: 15, title: "Titanic (1997)", genre: "Romance" }
      ]
    },
    {
      id: 3,
      title: "When do you watch movies?",
      subtitle: "Help us understand your viewing patterns",
      type: "mood_preferences",
      maxSelections: 3,
      options: [
        { id: "weekend", label: "Weekends", icon: "🌅" },
        { id: "weekday", label: "Weekdays", icon: "💼" },
        { id: "evening", label: "Evenings", icon: "🌙" },
        { id: "afternoon", label: "Afternoons", icon: "☀️" },
        { id: "late_night", label: "Late Night", icon: "🌃" }
      ]
    }
  ];

  const currentStageData = stages[currentStage - 1];

  // Search movies function
  const searchMovies = async (query) => {
    if (!query.trim() || query.trim().length < 2) {
      setSearchResults([]);
      return;
    }

    setSearching(true);
    try {
      const response = await fetch(`/api/movies/search?query=${encodeURIComponent(query.trim())}`, {
        method: 'GET'
      });

      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      } else {
        console.error('Failed to search movies');
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Error searching movies:', error);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  // Debounced search with longer delay for better performance
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery && searchQuery.trim().length >= 2) {
        searchMovies(searchQuery);
      } else {
        setSearchResults([]);
      }
    }, 500); // Increased from 300ms to 500ms

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  const handleSelection = (item) => {
    // For movie selection stage, use favorite_movies key
    const key = currentStageData.type === 'movie_selection' ? 'favorite_movies' : currentStageData.type;
    const currentSelections = selections[key] || [];
    const isSelected = currentSelections.includes(item);

    if (isSelected) {
      // Remove item
      setSelections(prev => ({
        ...prev,
        [key]: currentSelections.filter(i => i !== item)
      }));
    } else {
      // Add item if under max limit
      if (currentSelections.length < currentStageData.maxSelections) {
        setSelections(prev => ({
          ...prev,
          [key]: [...currentSelections, item]
        }));
      }
    }
  };

  const handleMovieSelection = (movie) => {
    const currentSelections = selections.favorite_movies || [];
    // Create movie title with year for consistency
    const movieTitleWithYear = movie.release_year ? `${movie.title} (${movie.release_year})` : movie.title;
    const isSelected = currentSelections.includes(movieTitleWithYear);

    if (isSelected) {
      // Remove movie
      setSelections(prev => ({
        ...prev,
        favorite_movies: currentSelections.filter(m => m !== movieTitleWithYear)
      }));
    } else {
      // Add movie if under max limit
      if (currentSelections.length < currentStageData.maxSelections) {
        setSelections(prev => ({
          ...prev,
          favorite_movies: [...currentSelections, movieTitleWithYear]
        }));
      }
    }
    // Clear search after selection
    setSearchQuery('');
    setSearchResults([]);
  };

  const handleNext = async () => {
    if (currentStage < stages.length) {
      setLoading(true);
      
      try {
        // Get the correct selections for the current stage
        const key = currentStageData.type === 'movie_selection' ? 'favorite_movies' : currentStageData.type;
        const stageSelections = selections[key] || [];
        
        // Send current stage selections to backend
        await updateOnboarding({
          stage: currentStage,
          selections: stageSelections
        });
        
        setCurrentStage(prev => prev + 1);
      } catch (error) {
        console.error('Error updating onboarding:', error);
        // Still proceed to next stage even if API fails
        setCurrentStage(prev => prev + 1);
      } finally {
        setLoading(false);
      }
    } else {
      // Complete onboarding
      onComplete(selections);
    }
  };

  const handleSkip = () => {
    onSkip();
  };

  const getSelectionCount = () => {
    // For movie selection stage, use favorite_movies key
    if (currentStageData.type === 'movie_selection') {
      return selections.favorite_movies?.length || 0;
    }
    // For other stages, use the stage type as key
    return selections[currentStageData.type]?.length || 0;
  };

  const canProceed = () => {
    const count = getSelectionCount();
    return count > 0 && count <= currentStageData.maxSelections;
  };

  // Render movie search section
  const renderMovieSearch = () => (
    <div className="movie-search-section">
      <div className="search-container">
        <input
          type="text"
          placeholder="Type at least 2 characters to search movies..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="movie-search-input"
        />
        {searching && <div className="search-spinner" />}
        {searchQuery.length > 0 && searchQuery.length < 2 && (
          <div className="search-hint">Type at least 2 characters to search</div>
        )}
        
        {/* Dropdown Suggestions */}
        {searchResults.length > 0 && (
          <div className="search-dropdown">
            {searchResults.map((movie) => {
              const movieTitleWithYear = movie.release_year ? `${movie.title} (${movie.release_year})` : movie.title;
              const isSelected = selections.favorite_movies?.includes(movieTitleWithYear);
              return (
                <motion.button
                  key={movie.id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`dropdown-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleMovieSelection(movie)}
                  disabled={!isSelected && getSelectionCount() >= currentStageData.maxSelections}
                >
                  <div className="dropdown-item-content">
                    <div className="movie-title">
                      {movie.title} {movie.release_year && `(${movie.release_year})`}
                    </div>
                    <div className="movie-meta">
                      <span className="movie-rating">⭐ {movie.rating}</span>
                      <span className="movie-genres">{movie.genres.join(', ')}</span>
                    </div>
                  </div>
                  {isSelected && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="selection-indicator"
                    >
                      ✓
                    </motion.div>
                  )}
                </motion.button>
              );
            })}
          </div>
        )}
      </div>
      
      {/* Selected Movies */}
      {selections.favorite_movies && selections.favorite_movies.length > 0 && (
        <div className="selected-movies">
          <h4>Selected Movies ({selections.favorite_movies.length}/{currentStageData.maxSelections})</h4>
          <div className="selected-movies-grid">
            {selections.favorite_movies.map((movieTitle, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="selected-movie-chip"
              >
                <span>{movieTitle}</span>
                <button
                  onClick={() => handleSelection(movieTitle)}
                  className="remove-movie-btn"
                >
                  ×
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}
      
      <div className="popular-movies-section">
        <h4>Popular Movies (or search above for niche films)</h4>
        <div className="options-grid">
          {currentStageData.options.map((option, index) => {
            const isSelected = selections.favorite_movies?.includes(option.title);
            
            return (
              <motion.button
                key={index}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className={`option-card ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelection(option.title)}
                disabled={!isSelected && getSelectionCount() >= currentStageData.maxSelections}
              >
                <span className="option-text">{option.title}</span>
                <span className="option-genre">{option.genre}</span>
                {isSelected && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="selection-indicator"
                  >
                    ✓
                  </motion.div>
                )}
              </motion.button>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-container">
        {/* Progress Bar */}
        <div className="progress-bar">
          <div 
            className="progress-fill"
            style={{ width: `${(currentStage / stages.length) * 100}%` }}
          />
        </div>

        {/* Stage Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStage}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={{ duration: 0.3 }}
            className="stage-content"
          >
            <div className="stage-header">
              <h2 className="stage-title">{currentStageData.title}</h2>
              <p className="stage-subtitle">{currentStageData.subtitle}</p>
              <div className="selection-counter">
                {getSelectionCount()} / {currentStageData.maxSelections} selected
              </div>
            </div>

            {/* Render movie search for movie selection stage */}
            {currentStageData.type === 'movie_selection' ? (
              renderMovieSearch()
            ) : (
              <div className="options-grid">
                {currentStageData.options.map((option, index) => {
                  const item = currentStageData.type === 'mood_preferences' ? option.id : option;
                  const isSelected = selections[currentStageData.type]?.includes(item);
                  
                  return (
                    <motion.button
                      key={index}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={`option-card ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleSelection(item)}
                      disabled={!isSelected && getSelectionCount() >= currentStageData.maxSelections}
                    >
                      {currentStageData.type === 'mood_preferences' && (
                        <span className="option-icon">{option.icon}</span>
                      )}
                      <span className="option-text">
                        {currentStageData.type === 'mood_preferences' ? option.label : option}
                      </span>
                      {isSelected && (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="selection-indicator"
                        >
                          ✓
                        </motion.div>
                      )}
                    </motion.button>
                  );
                })}
              </div>
            )}

            <div className="stage-actions">
              <button 
                className="skip-button"
                onClick={handleSkip}
              >
                Skip for now
              </button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`next-button ${canProceed() ? 'active' : 'disabled'}`}
                onClick={handleNext}
                disabled={!canProceed() || loading}
              >
                {loading ? (
                  <div className="loading-spinner" />
                ) : currentStage === stages.length ? (
                  'Complete Setup'
                ) : (
                  'Continue'
                )}
              </motion.button>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default OnboardingFlow;