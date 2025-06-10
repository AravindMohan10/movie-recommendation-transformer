import React, { useState, useEffect, useMemo } from "react";
import { useAuth } from "../contexts/AuthContext";
import ProfileMenu from "../Components/ProfileMenu";
import ShinyText from "../Components/ShinyText";
import HolographicGallery from "../Components/HolographicGallery";
import HowItWorksModal from "../Components/HowItWorksModal";
import OnboardingFlow from "../Components/OnboardingFlow";
import DashboardSidebar from "../Components/DashboardSidebar";
import SurpriseMeModal from "../Components/SurpriseMeModal";
import MovieReviewsModal from "../Components/MovieReviewsModal";
import MovieSearch from "../Components/MovieSearch";
import { getOnboardingStatus, getRecommendations, getSurpriseMe, getGenres, getMoviesByGenre, getHiddenGems, completeOnboarding } from "../Utils/api";
import { devLog, devWarn, devError } from "../Utils/logger";

const demoMovies = [
  {
    image: "https://image.tmdb.org/t/p/w342/8UlWHLMpgZm9bx6QYh0NFoq67TZ.jpg",
    title: "Inception",
    genre: "Sci-Fi",
    year: 2010,
    rating: 8.8,
    director: "Christopher Nolan",
    aiConfidence: 0.94,
    matchReason: "Based on your preference for mind-bending narratives"
  },
  {
    image: "https://image.tmdb.org/t/p/w342/6ELJEzQJ3Y45HczvreC3dg0GV5R.jpg",
    title: "Interstellar",
    genre: "Adventure",
    year: 2014,
    rating: 8.6,
    director: "Christopher Nolan",
    aiConfidence: 0.87,
    matchReason: "Matches your taste for epic space dramas"
  },
  {
    image: "https://image.tmdb.org/t/p/w342/2CAL2433ZeIihfX1Hb2139CX0pW.jpg",
    title: "The Dark Knight",
    genre: "Action",
    year: 2008,
    rating: 9.0,
    director: "Christopher Nolan",
    aiConfidence: 0.92,
    matchReason: "Aligns with your preference for complex superhero stories"
  },
  {
    image: "https://image.tmdb.org/t/p/w342/q719jXXEzOoYaps6babgKnONONX.jpg",
    title: "Tenet",
    genre: "Action",
    year: 2020,
    rating: 7.4,
    director: "Christopher Nolan",
    aiConfidence: 0.78,
    matchReason: "Similar to your preferred time-bending thrillers"
  },
  {
    image: "https://image.tmdb.org/t/p/w342/6KErczPBROQty7QoIsaa6wJYXZi.jpg",
    title: "The Matrix",
    genre: "Sci-Fi",
    year: 1999,
    rating: 8.7,
    director: "Lana & Lilly Wachowski",
    aiConfidence: 0.96,
    matchReason: "Perfect match for your cyberpunk preferences"
  },
  {
    image: "https://image.tmdb.org/t/p/w342/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
    title: "Pulp Fiction",
    genre: "Crime",
    year: 1994,
    rating: 8.9,
    director: "Quentin Tarantino",
    aiConfidence: 0.85,
    matchReason: "Fits your appreciation for nonlinear storytelling"
  },
];

export default function Dashboard() {
  const { user, loading, isAuthenticated } = useAuth();
  const [movies, setMovies] = useState([]);
  const [aiInsights, setAiInsights] = useState({
    totalInteractions: 0,
    topGenres: []
  });
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingCompleted, setOnboardingCompleted] = useState(false);
  const [loadingRecommendations, setLoadingRecommendations] = useState(true);
  const [recentActivity, setRecentActivity] = useState([]);
  const [modelSource, setModelSource] = useState(null); // 'model' or 'fallback'
  const [recommendationQuality, setRecommendationQuality] = useState({
    confidence: 0,
    personalization: 0,
    diversity: 0
  });
  const [confidenceLabel, setConfidenceLabel] = useState("—"); // "High confidence" | "Mixed confidence" | "Limited data"
  const [sidebarOpen, setSidebarOpen] = useState(true); // Open by default, collapsible
  const [userInteractions, setUserInteractions] = useState({}); // Track interactions per movie: {movieId: {like: true, dislike: false, favorite: true}}
  const [watchlist, setWatchlist] = useState([]); // User's watchlist
  const [surpriseMovies, setSurpriseMovies] = useState([]);
  const [showSurpriseModal, setShowSurpriseModal] = useState(false);
  const [loadingSurprise, setLoadingSurprise] = useState(false);
  const [reviewModalMovie, setReviewModalMovie] = useState(null);
  const [howItWorksOpen, setHowItWorksOpen] = useState(false);
  const [selectedGenre, setSelectedGenre] = useState(null); // null = Recommendations, else genre name e.g. "Action" (browse all in genre)
  const [allGenres, setAllGenres] = useState([]); // from API for browse-by-genre chips
  const [genreMovies, setGenreMovies] = useState([]); // all movies in selected genre (from catalog)
  const [loadingGenre, setLoadingGenre] = useState(false);
  const [hiddenGems, setHiddenGems] = useState([]);
  const [loadingHiddenGems, setLoadingHiddenGems] = useState(false);

  // When user selects a genre, fetch all movies in that genre from catalog (not filter recs)
  useEffect(() => {
    if (!selectedGenre) {
      setGenreMovies([]);
      return;
    }
    let cancelled = false;
    setLoadingGenre(true);
    getMoviesByGenre(selectedGenre, 80)
      .then((data) => {
        if (cancelled) return;
        const list = (data.movies || []).map((m) => ({
          id: m.movie_id || m.id,
          movie_id: m.movie_id || m.id,
          image: m.poster_url || (m.poster_path ? `https://image.tmdb.org/t/p/w342${m.poster_path}` : null),
          poster_url: m.poster_url || (m.poster_path ? `https://image.tmdb.org/t/p/w342${m.poster_path}` : null),
          title: m.title,
          genre: m.genre || (m.genres && m.genres[0]) || "Unknown",
          genres: m.genres || [],
          year: m.release_year,
          release_year: m.release_year,
          rating: m.vote_average || 0,
          director: "—",
          matchReason: `From catalog: ${selectedGenre}`,
          overview: m.overview || "",
        }));
        setGenreMovies(list);
      })
      .catch(() => {
        if (!cancelled) setGenreMovies([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingGenre(false);
      });
    return () => { cancelled = true; };
  }, [selectedGenre]);

  // Fetch genre list for chips (browse-by-genre, not from recommendations)
  useEffect(() => {
    getGenres()
      .then((data) => setAllGenres(data.genres || []))
      .catch(() => setAllGenres([]));
  }, []);

  // Fetch hidden gems channel when authenticated (show when on recommendations view)
  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    setLoadingHiddenGems(true);
    getHiddenGems(15)
      .then((data) => {
        if (cancelled) return;
        const list = (data.recommendations || []).map((m) => {
          const pp = m.poster_path;
          const posterUrl = pp && !String(pp).startsWith("http")
            ? (pp.startsWith("/") ? `https://image.tmdb.org/t/p/w342${pp}` : `https://image.tmdb.org/t/p/w342/${pp}`)
            : pp || null;
          return {
            id: m.movie_id,
            movie_id: m.movie_id,
            title: m.title || "Unknown",
            overview: m.overview || "",
            rating: m.vote_average || 0,
            vote_average: m.vote_average || 0,
            poster_url: posterUrl,
            poster_path: m.poster_path,
            image: posterUrl,
            serendipity_score: m.serendipity_score,
            genre: "Hidden gem",
            genres: ["Hidden gem"],
            year: null,
            release_year: null,
            director: "—",
            matchReason: m.explanation || "High quality, lower popularity pick.",
          };
        });
        setHiddenGems(list);
      })
      .catch(() => {
        if (!cancelled) setHiddenGems([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingHiddenGems(false);
      });
    return () => { cancelled = true; };
  }, [isAuthenticated]);

  // Fetch recommendations, check onboarding status, and load activities
  useEffect(() => {
    if (isAuthenticated && user) {
      checkOnboardingAndFetchRecommendations();
      loadActivities(); // Load activities from backend
      loadWatchlist(); // Load watchlist
    }
  }, [isAuthenticated, user]);

  const checkOnboardingAndFetchRecommendations = async () => {
    try {
      setLoadingRecommendations(true);
      
      // Always fetch recommendations (works with or without onboarding)
      // Onboarding is optional for showcasing - we show popular movies as fallback
      await fetchRecommendations();
      
      // Check onboarding status for UI hints (but don't block)
      try {
        const onboardingStatus = await getOnboardingStatus();
        if (!onboardingStatus.onboarding_completed) {
          // Don't force onboarding, just note it's available
          devLog('Onboarding available but not required');
        }
      } catch (error) {
        // Onboarding status check failed, but recommendations should still work
        devLog('Onboarding status unavailable, showing recommendations anyway');
      }
      
    } catch (error) {
      devError('Error fetching recommendations:', error);
      // Even if there's an error, try to show some movies
      setLoadingRecommendations(false);
    }
  };

  const fetchRecommendations = async () => {
    try {
      setLoadingRecommendations(true);
      
      const data = await getRecommendations(10);
      
      // Track model source
      const isModelRecommendations = data.recommendations.length > 0 && 
        data.recommendations.some(m => m.confidence > 0.5 || m.predicted_rating > 0);
      setModelSource(isModelRecommendations ? 'model' : 'fallback');
      
      // Calculate recommendation quality metrics and global confidence label
      if (data.recommendations.length > 0) {
        const avgConfidence = data.recommendations.reduce((sum, m) => sum + (m.confidence || 0.5), 0) / data.recommendations.length;
        const avgPct = Math.round(avgConfidence * 100);
        const avgRating = data.recommendations.reduce((sum, m) => sum + (m.predicted_rating || 7), 0) / data.recommendations.length;
        const uniqueGenres = new Set(data.recommendations.flatMap(m => {
          if (Array.isArray(m.genres)) return m.genres;
          if (m.genre) return [m.genre];
          return [];
        }));
        setRecommendationQuality({
          confidence: avgPct,
          personalization: Math.round(Math.min(avgRating / 10 * 100, 100)),
          diversity: Math.round((uniqueGenres.size / Math.max(data.recommendations.length, 1)) * 100)
        });
        if (avgPct >= 70) setConfidenceLabel("High confidence");
        else if (avgPct >= 50) setConfidenceLabel("Mixed confidence");
        else setConfidenceLabel("Limited data");
      } else {
        setConfidenceLabel("—");
      }
      
      // Transform API data to match our component format
      const transformedMovies = data.recommendations.map(movie => {
        const movieId = movie.movie_id || movie.id;
        const conf = movie.confidence != null ? movie.confidence : 0.6;
        let confidenceLevel = movie.confidence_level;
        if (!confidenceLevel) {
          if (conf >= 0.7) confidenceLevel = "high";
          else if (conf >= 0.5) confidenceLevel = "medium";
          else confidenceLevel = "low";
        }
        return {
          id: movieId,
          movie_id: movieId,
          image: movie.poster_url || movie.image || movie.poster_path || `https://via.placeholder.com/342x513/1a1a1a/666666?text=No+Poster`,
          poster_url: movie.poster_url || movie.image || movie.poster_path,
          title: movie.title,
          genre: (movie.genres && movie.genres[0]) || movie.genre || "Unknown",
          genres: movie.genres || movie.genres_list || [],
          year: movie.release_year || movie.year || 2020,
          release_year: movie.release_year || movie.year,
          rating: movie.rating || movie.vote_average || 8.0,
          vote_average: movie.vote_average || movie.rating,
          director: movie.director || "Unknown",
          directors: movie.directors || [],
          confidence: movie.confidence != null ? movie.confidence : conf,
          aiConfidence: conf,
          confidenceLevel,
          matchReason: movie.ai_reason ?? movie.explanation ?? null,
          overview: movie.overview || ""
        };
      });
      
      setMovies(transformedMovies);
      setAiInsights(prev => ({
        ...prev,
        totalInteractions: data.total_interactions || 0
      }));
      
      // Set model source from API
      if (data.model_source) {
        setModelSource(data.model_source);
      }
      
    } catch (error) {
      devError('Error fetching recommendations:', error);
      setMovies(demoMovies);
      setConfidenceLabel("—");
    } finally {
      setLoadingRecommendations(false);
    }
  };

  // Callback functions for interactive buttons
  // Load activities from backend on mount and when needed
  const loadActivities = async () => {
    try {
      const response = await fetch('/api/recommendations/interactions?limit=20', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('cineai_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        // Filter: Only show the most recent like OR dislike per movie (mutual exclusivity)
        const movieActions = {}; // Track most recent action per movie
        data.interactions.forEach(interaction => {
          const key = `${interaction.movie_id}_${interaction.action}`;
          const movieKey = interaction.movie_id;
          const timestamp = new Date(interaction.created_at || interaction.timestamp || 0).getTime();
          
          // For like/dislike: only keep the most recent one per movie
          if (interaction.action === 'like' || interaction.action === 'dislike') {
            if (!movieActions[movieKey] || timestamp > movieActions[movieKey].timestamp) {
              movieActions[movieKey] = {
                interaction,
                timestamp,
                key: interaction.action
              };
            }
          } else {
            // For favorite/review: keep all (not mutually exclusive)
            movieActions[key] = {
              interaction,
              timestamp,
              key: interaction.action
            };
          }
        });
        
        // Build final list: most recent like/dislike + all favorites/reviews
        // Note: Favorites can be toggled off, so we only show existing favorites
        const filteredInteractions = Object.values(movieActions)
          .map(item => item.interaction)
          .filter(interaction => {
            // Only include favorite if it still exists (hasn't been removed)
            // All other interactions are included
            return true;
          })
          .sort((a, b) => {
            const timeA = new Date(a.created_at || a.timestamp || 0).getTime();
            const timeB = new Date(b.created_at || b.timestamp || 0).getTime();
            return timeB - timeA; // Most recent first
          });
        
        const formattedActivities = filteredInteractions.map(interaction => {
          const activityLabels = {
            like: `Liked "${interaction.movie_title}"`,
            dislike: `Disliked "${interaction.movie_title}"`,
            favorite: `Favorited "${interaction.movie_title}"`,
            review: `Reviewed "${interaction.movie_title}"`
          };
          
          // Format time - handle both created_at and timestamp
          let timeLabel = 'Just now';
          const timestampStr = interaction.created_at || interaction.timestamp;
          if (timestampStr) {
            try {
              const now = new Date();
              const created = new Date(timestampStr);
              if (!isNaN(created.getTime())) {
                const diffMs = now - created;
                const diffHours = diffMs / (1000 * 60 * 60);
                const diffDays = diffMs / (1000 * 60 * 60 * 24);
                
                if (diffDays >= 1) {
                  timeLabel = `${Math.floor(diffDays)}d ago`;
                } else if (diffHours >= 1) {
                  timeLabel = `${Math.floor(diffHours)}h ago`;
                } else {
                  const diffMins = diffMs / (1000 * 60);
                  if (diffMins >= 1) {
                    timeLabel = `${Math.floor(diffMins)}m ago`;
                  } else {
                    timeLabel = 'Just now';
                  }
                }
              }
            } catch (e) {
              devError('Error parsing timestamp:', e);
            }
          }
          
          const timestamp = (interaction.created_at || interaction.timestamp) 
            ? new Date(interaction.created_at || interaction.timestamp).getTime() 
            : Date.now();
          
          return {
            id: interaction.id || `interaction_${interaction.movie_id}_${interaction.action}`,
            type: interaction.action,
            label: activityLabels[interaction.action] || `Interacted with "${interaction.movie_title}"`,
            time: timeLabel,
            timestamp: timestamp,
            movie_id: interaction.movie_id,
            movie_title: interaction.movie_title
          };
        });
        
        setRecentActivity(formattedActivities);
        devLog('📊 Loaded activities:', formattedActivities.length, 'items');
        
        // Build user interactions map for button states (handle both id formats)
        const interactionsMap = {};
        data.interactions.forEach(interaction => {
          const movieId = interaction.movie_id;
          // Store with both string and int keys for compatibility
          const idStr = String(movieId);
          const idInt = parseInt(movieId);
          
          // Initialize if needed
          if (!interactionsMap[idStr]) {
            interactionsMap[idStr] = {};
          }
          if (!interactionsMap[idInt]) {
            interactionsMap[idInt] = {};
          }
          
          // Set the action flag
          interactionsMap[idStr][interaction.action] = true;
          interactionsMap[idInt][interaction.action] = true;
        });
        
        devLog('🔘 User interactions map:', interactionsMap);
        devLog('🔘 Setting userInteractions state...');
        setUserInteractions(interactionsMap);
        devLog('🔘 State set complete');
      }
    } catch (error) {
      devError('Error loading activities:', error);
    }
  };

  // Load watchlist
  const loadWatchlist = async () => {
    try {
      const response = await fetch('/api/watchlist', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('cineai_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setWatchlist(data.watchlist || []);
      }
    } catch (error) {
      devError('Error loading watchlist:', error);
    }
  };

  // Add activity to local state (for immediate UI feedback)
  const addToActivity = (type, title, movieId) => {
    // Check if duplicate (same movie + action)
    setRecentActivity(prev => {
      const existing = prev.find(a => a.movie_id === movieId && a.type === type);
      if (existing) {
        // Update existing, move to top
        return [{
          ...existing,
          time: 'Just now',
          timestamp: Date.now()
        }, ...prev.filter(a => !(a.movie_id === movieId && a.type === type))];
      }
      
      const activityLabels = {
        like: `Liked "${title}"`,
        dislike: `Disliked "${title}"`,
        favorite: `Favorited "${title}"`,
        review: `Reviewed "${title}"`
      };
      
      return [{
        id: `temp_${Date.now()}`,
        type,
        label: activityLabels[type] || `Interacted with "${title}"`,
        time: 'Just now',
        timestamp: Date.now(),
        movie_id: movieId,
        movie_title: title
      }, ...prev].slice(0, 20);
    });
  };

  const handleLike = async (movieTitle) => {
    const movie = movies.find(m => m.title === movieTitle);
    if (!movie) return;
    
    const movieId = movie.id || movie.movie_id;
    const idStr = String(movieId);
    const idInt = parseInt(movieId);
    
    devLog('👍 Like clicked for movie:', movieId, movieTitle);
    devLog('🔘 Current state BEFORE update:', userInteractions);
    
    // Update button state immediately - use functional update
    setUserInteractions((prev) => {
      const newState = JSON.parse(JSON.stringify(prev)); // Deep clone
      const currentState = newState[idStr] || newState[idInt] || {};
      
      // Update both formats
      newState[idStr] = { ...currentState, like: true, dislike: false, favorite: currentState.favorite || false };
      newState[idInt] = { ...currentState, like: true, dislike: false, favorite: currentState.favorite || false };
      
      devLog('🔘 New state AFTER update:', newState);
      devLog('🔘 State for this movie:', newState[idStr] || newState[idInt]);
      
      return newState;
    });
    
    // Immediate UI updates - Optimistic
    addToActivity('like', movieTitle, movieId);
    
    try {
      const token = localStorage.getItem('cineai_token');
      devLog('🌐 API Call - Like:', { movieId, token: token ? 'present' : 'missing' });
      
      const apiUrl = '/api/recommendations/interact';
      devLog('🌐 Calling:', apiUrl);
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          movie_id: movieId,
          action: 'like'
        })
      });
      
      devLog('🌐 Response status:', response.status);
      const responseData = await response.json().catch(() => ({}));
      devLog('🌐 Response data:', responseData);
      
      if (!response.ok) {
        devError('❌ API Error:', response.status, responseData);
      }

      if (response.ok) {
        // Reload activities from backend to get persisted data
        await loadActivities();
        
        setAiInsights(prev => ({
          ...prev,
          totalInteractions: prev.totalInteractions + 1
        }));
        
        // Don't refresh recommendations - keep carousel smooth and stable
        // User can manually refresh or recommendations update on next page load
      } else {
        // Revert on error
        await loadActivities();
      }
    } catch (error) {
      devError('Error recording like:', error);
      // Revert on error
      await loadActivities();
    }
  };

  const handleDislike = async (movieTitle) => {
    const movie = movies.find(m => m.title === movieTitle);
    if (!movie) return;
    
    const movieId = movie.id || movie.movie_id;
    const idStr = String(movieId);
    const idInt = parseInt(movieId);
    
    devLog('👎 Dislike clicked for movie:', movieId, movieTitle);
    devLog('🔘 Current state BEFORE update:', userInteractions);
    
    // Update button state immediately - use functional update
    setUserInteractions((prev) => {
      const newState = JSON.parse(JSON.stringify(prev)); // Deep clone
      const currentState = newState[idStr] || newState[idInt] || {};
      
      // Update both formats
      newState[idStr] = { ...currentState, dislike: true, like: false, favorite: currentState.favorite || false };
      newState[idInt] = { ...currentState, dislike: true, like: false, favorite: currentState.favorite || false };
      
      devLog('🔘 New state AFTER update:', newState);
      devLog('🔘 State for this movie:', newState[idStr] || newState[idInt]);
      
      return newState;
    });
    
    // Immediate UI updates - Optimistic
    addToActivity('dislike', movieTitle, movieId);
    
    try {
      const token = localStorage.getItem('cineai_token');
      devLog('🌐 API Call - Dislike:', { movieId, token: token ? 'present' : 'missing' });
      
      const response = await fetch('/api/recommendations/interact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          movie_id: movieId,
          action: 'dislike'
        })
      });
      
      devLog('🌐 Response status:', response.status);
      const responseData = await response.json().catch(() => ({}));
      devLog('🌐 Response data:', responseData);

      if (response.ok) {
        // Reload activities from backend
        await loadActivities();
        
        setAiInsights(prev => ({
          ...prev,
          totalInteractions: prev.totalInteractions + 1
        }));
        
        // Don't refresh recommendations - keep carousel smooth and stable
        // User can manually refresh or recommendations update on next page load
      } else {
        // Revert on error
        await loadActivities();
      }
    } catch (error) {
      devError('Error recording dislike:', error);
      // Revert on error
      await loadActivities();
    }
  };

  const handleFavorite = async (movieTitle) => {
    const movie = movies.find(m => m.title === movieTitle);
    if (!movie) return;
    
    const movieId = movie.id || movie.movie_id;
    const idStr = String(movieId);
    const idInt = parseInt(movieId);
    
    devLog('⭐ Favorite clicked for movie:', movieId, movieTitle);
    devLog('🔘 Current state BEFORE update:', userInteractions);
    
    // Check current favorite state to determine if we're favoriting or unfavoriting
    const currentState = userInteractions[idStr] || userInteractions[idInt] || {};
    const isCurrentlyFavorited = currentState.favorite || false;
    const newFavoriteState = !isCurrentlyFavorited;
    
    // Update button state immediately (toggle favorite)
    setUserInteractions((prev) => {
      const newState = JSON.parse(JSON.stringify(prev)); // Deep clone
      const currentState = newState[idStr] || newState[idInt] || {};
      
      // Update both formats
      newState[idStr] = { ...currentState, favorite: newFavoriteState };
      newState[idInt] = { ...currentState, favorite: newFavoriteState };
      
      devLog('🔘 New state AFTER update:', newState);
      devLog('🔘 State for this movie:', newState[idStr] || newState[idInt]);
      devLog('🔘 Favorite state:', newFavoriteState);
      
      return newState;
    });
    
    // Update activity feed - add if favoriting, remove if unfavoriting
    if (newFavoriteState) {
      // Adding favorite - add to activity
      addToActivity('favorite', movieTitle, movieId);
    } else {
      // Removing favorite - remove from activity
      setRecentActivity(prev => prev.filter(activity => 
        !(activity.movie_id === movieId && activity.type === 'favorite')
      ));
    }
    
    try {
      const token = localStorage.getItem('cineai_token');
      devLog('🌐 API Call - Favorite:', { movieId, token: token ? 'present' : 'missing' });
      
      const response = await fetch('/api/recommendations/interact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          movie_id: movieId,
          action: 'favorite'
        })
      });
      
      devLog('🌐 Response status:', response.status);
      
      if (response.ok) {
        const responseData = await response.json().catch(() => ({}));
        devLog('🌐 Response data:', responseData);
        
        // Reload activities from backend to reflect the toggle
        await loadActivities();
        
        // Only increment interactions if we're favoriting (not unfavoriting)
        if (newFavoriteState && !responseData.removed) {
          setAiInsights(prev => ({
            ...prev,
            totalInteractions: prev.totalInteractions + 1
          }));
        }
        
        // Don't refresh recommendations - keep carousel smooth and stable
        // User can manually refresh or recommendations update on next page load
      } else {
        // Revert on error - toggle back
        setUserInteractions((prev) => {
          const newState = JSON.parse(JSON.stringify(prev));
          const currentState = newState[idStr] || newState[idInt] || {};
          newState[idStr] = { ...currentState, favorite: isCurrentlyFavorited };
          newState[idInt] = { ...currentState, favorite: isCurrentlyFavorited };
          return newState;
        });
        await loadActivities();
      }
    } catch (error) {
      devError('Error recording favorite:', error);
      // Revert on error - toggle back
      setUserInteractions((prev) => {
        const newState = JSON.parse(JSON.stringify(prev));
        const currentState = newState[idStr] || newState[idInt] || {};
        newState[idStr] = { ...currentState, favorite: isCurrentlyFavorited };
        newState[idInt] = { ...currentState, favorite: isCurrentlyFavorited };
        return newState;
      });
      await loadActivities();
    }
  };

  // "Surprise Me" handler - get niche, high-quality film recommendations (no documentaries, no adult)
  const handleSurpriseMe = async () => {
    try {
      setLoadingSurprise(true);
      setShowSurpriseModal(true);
      const data = await getSurpriseMe(5);
      if (data.recommendations && data.recommendations.length > 0) {
        const transformedMovies = data.recommendations.slice(0, 5).map(movie => {
          const posterPath = movie.poster_path;
          const posterUrl = posterPath && !posterPath.startsWith('http')
            ? `https://image.tmdb.org/t/p/w342${posterPath.startsWith('/') ? '' : '/'}${posterPath}`
            : posterPath || null;
          return {
            id: movie.movie_id,
            movie_id: movie.movie_id,
            title: movie.title,
            overview: movie.overview || '',
            poster: posterUrl,
            image: posterUrl,
            poster_path: movie.poster_path,
            rating: movie.vote_average || movie.predicted_rating || 0,
            vote_average: movie.vote_average,
            vote_count: movie.vote_count,
            director: movie.director,
            explanation: movie.explanation || 'A hidden gem worth discovering!',
            is_surprise: true,
            guarantee_level: movie.guarantee_level || 'high'
          };
        });
        setSurpriseMovies(transformedMovies);
      } else {
        setSurpriseMovies([]);
      }
    } catch (error) {
      devError('Error getting surprise recommendation:', error);
      setSurpriseMovies([]);
    } finally {
      setLoadingSurprise(false);
    }
  };

  // Share handler
  const handleShare = async (movie) => {
    const shareUrl = `${window.location.origin}/share/movie/${movie.id || movie.movie_id}`;
    const shareText = `Check out "${movie.title}" - recommended by CineAI! 🎬`;
    
    if (navigator.share) {
      // Use Web Share API on mobile
      try {
        await navigator.share({
          title: movie.title,
          text: shareText,
          url: shareUrl
        });
      } catch (err) {
        if (err.name !== 'AbortError') {
          // Fallback to copy
          navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
          alert('Link copied to clipboard!');
        }
      }
    } else {
      // Fallback: copy to clipboard
      navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
      alert('Link copied to clipboard! 📋');
    }
  };

  // Toggle watchlist
  const handleToggleWatchlist = async (movie) => {
    try {
      const movieId = movie.id || movie.movie_id;
      const isInList = watchlist.some(w => w.movie_id === movieId);
      
      if (isInList) {
        // Remove from watchlist
        const response = await fetch(`/api/watchlist/remove/${movieId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('cineai_token')}`
          }
        });
        
        if (response.ok) {
          await loadWatchlist();
        }
      } else {
        // Add to watchlist
        const response = await fetch(`/api/watchlist/add?movie_id=${movieId}`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('cineai_token')}`
          }
        });

        if (response.ok) {
          await loadWatchlist();
        }
      }
    } catch (error) {
      devError('Error toggling watchlist:', error);
    }
  };

  const handleReview = (movie) => {
    if (!movie) return;
    setReviewModalMovie(movie);
  };

  const handleReviewSubmitted = async () => {
    await loadActivities();
    setAiInsights(prev => ({ ...prev, totalInteractions: prev.totalInteractions + 1 }));
  };

  const handleOnboardingComplete = async (onboardingData) => {
    try {
      await completeOnboarding(onboardingData);
      setShowOnboarding(false);
      setOnboardingCompleted(true);
      await fetchRecommendations();
    } catch (error) {
      devError('Error completing onboarding:', error);
      setShowOnboarding(false);
      setOnboardingCompleted(true);
      await fetchRecommendations();
    }
  };

  const handleOnboardingSkip = async () => {
    try {
      await completeOnboarding({ skipped: true });
      setShowOnboarding(false);
      setOnboardingCompleted(true);
      await fetchRecommendations();
    } catch (error) {
      devError('Error skipping onboarding:', error);
      setShowOnboarding(false);
      setOnboardingCompleted(true);
      await fetchRecommendations();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-teal-400 border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
          <div className="text-lg text-teal-200 font-light">Initializing your experience...</div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-black">
        <div className="text-5xl font-extrabold mb-8 bg-gradient-to-r from-teal-300 via-yellow-100 to-blue-200 bg-clip-text text-transparent tracking-tight">
          cine.<span className="text-white">ai</span>
        </div>
        <div className="text-xl text-gray-400 mb-8 font-light">Your premium movie companion</div>
        <a
          href="/auth"
          className="px-12 py-4 bg-gradient-to-r from-teal-400 via-yellow-300 to-blue-400 text-white rounded-full font-bold tracking-wide hover:scale-105 transition-all duration-300 shadow-2xl"
        >
          Begin Experience
        </a>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Onboarding Flow */}
      {showOnboarding && (
        <OnboardingFlow
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
        />
      )}

      {/* Subtle particle background */}
      <div className="fixed inset-0 z-0 opacity-20">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_80%,rgba(1,255,233,0.3),transparent_50%)]"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(252,255,108,0.3),transparent_50%)]"></div>
      </div>

      {/* Premium Navbar */}
      <nav className={`relative z-10 flex items-center justify-between px-12 py-8 border-b border-teal-700/30 transition-all duration-300 ${sidebarOpen ? 'ml-[260px]' : 'ml-0'}`}>
        <div className="flex items-center gap-8">
          <div className="text-2xl font-extrabold bg-gradient-to-r from-teal-300 via-yellow-100 to-blue-200 bg-clip-text text-transparent tracking-tight">
            cine.<span className="text-white">ai</span>
          </div>
          <div className="hidden md:flex items-center gap-2 text-sm text-teal-200">
            <div className="w-1.5 h-1.5 bg-teal-400 rounded-full animate-pulse"></div>
            AI Active
          </div>
        </div>
        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() => setHowItWorksOpen(true)}
            title="How recommendations work"
            className="rounded-full border border-teal-400/50 text-teal-300 p-2 bg-transparent hover:bg-teal-500/10 hover:border-teal-400 transition"
            aria-label="How recommendations work"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </button>
          <ProfileMenu />
        </div>
      </nav>

      {/* Welcome Section */}
      <section className="relative z-10 px-12 py-12">
        <div className={`mx-auto transition-all duration-300 ${sidebarOpen ? 'ml-[260px]' : 'ml-0'}`} style={{ maxWidth: '100%' }}>
          <div className="flex items-center justify-between mb-12">
            <div>
              <h1 className="text-4xl font-light text-white mb-3 tracking-wide">
                Welcome back, <span className="text-teal-300">{user.username}</span>
              </h1>
              <p className="text-gray-400 text-lg font-light">
                Your AI has analyzed {aiInsights.totalInteractions} interactions to curate today's selections
              </p>
            </div>
          </div>

          {/* Genre Tags */}
          {aiInsights.topGenres.length > 0 && (
            <div className="flex flex-wrap gap-3 mb-16">
              {aiInsights.topGenres.map((genre, index) => (
                <span 
                  key={genre}
                  className="px-4 py-2 bg-black/70 border border-teal-700 text-teal-200 text-sm font-light tracking-wide hover:border-yellow-200 transition-colors duration-300 rounded-lg"
                >
                  {genre}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Main Content - Adjusts margin when sidebar is open */}
      <main className={`relative z-10 mx-auto px-12 pb-16 transition-all duration-300 ${sidebarOpen ? 'ml-[260px]' : 'ml-0'}`} style={{ maxWidth: '100%' }}>
        {/* Premium Recommendations Section */}
        <section className="mb-20">
          <div className="flex items-center justify-between mb-12">
            <div>
              <h2 className="text-3xl font-light text-white mb-2 tracking-wide">
                Your Recommendations
              </h2>
              <p className="text-gray-400 font-light">
                Curated just for you
                {" · "}
                <button
                  type="button"
                  onClick={() => setHowItWorksOpen(true)}
                  className="text-teal-400 hover:text-teal-300 underline underline-offset-2 transition"
                >
                  How it works
                </button>
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <MovieSearch
                onLike={loadActivities}
                onWatchlist={loadWatchlist}
                isInWatchlist={(id) => watchlist.some((w) => w.movie_id === id)}
              />
              <button
                onClick={fetchRecommendations}
                disabled={loadingRecommendations}
                className="px-4 py-2 bg-black/70 border border-teal-700 text-teal-200 rounded-lg font-medium hover:border-teal-500 hover:bg-teal-500/10 transition-all disabled:opacity-50 flex items-center gap-2"
              >
                {loadingRecommendations ? (
                  <span className="w-4 h-4 border-2 border-teal-400 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                )}
                Refresh
              </button>
              <button
                onClick={handleSurpriseMe}
                className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:scale-105 transition-all duration-300 shadow-lg hover:shadow-purple-500/50 flex items-center gap-2"
              >
                <span>🎲</span>
                Surprise Me
              </button>
              {selectedGenre == null && (
                <div
                  className="hidden md:flex items-center gap-3 px-4 py-2 bg-black/70 border border-teal-700 rounded-lg"
                  title={confidenceLabel === "High confidence" ? "Most recommendations have high confidence from similar users or review similarity." : confidenceLabel === "Limited data" ? "Based on limited interaction data; like or review more for better picks." : "Confidence varies across recommendations."}
                >
                  <div className={`w-2 h-2 rounded-full animate-pulse ${confidenceLabel === "High confidence" ? "bg-teal-400" : confidenceLabel === "Limited data" ? "bg-slate-400" : "bg-amber-400"}`} />
                  <span className="text-teal-200 text-sm font-light tracking-wide">{confidenceLabel}</span>
                </div>
              )}
            </div>
          </div>

          {/* Genre browse chips: "All" = recommendations; others = all movies in that genre from catalog */}
          <div className="mb-6">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setSelectedGenre(null)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 border ${
                  selectedGenre == null
                    ? "bg-teal-500/20 border-teal-400 text-teal-200 shadow-sm shadow-teal-500/10"
                    : "bg-black/70 border-teal-700 text-teal-200 hover:border-teal-500 hover:bg-teal-500/10"
                }`}
                aria-pressed={selectedGenre == null}
                aria-label="Show recommendations"
              >
                Recommendations
              </button>
              {allGenres.map((genreName) => {
                const isActive = selectedGenre === genreName;
                return (
                  <button
                    key={genreName}
                    type="button"
                    onClick={() => setSelectedGenre(genreName)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-300 border ${
                      isActive
                        ? "bg-teal-500/20 border-teal-400 text-teal-200 shadow-sm shadow-teal-500/10"
                        : "bg-black/70 border-teal-700 text-teal-200 hover:border-teal-500 hover:bg-teal-500/10"
                    }`}
                    aria-pressed={isActive}
                    aria-label={`Browse ${genreName} movies`}
                  >
                    {genreName}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section title: Recommendations vs "All [Genre] movies" */}
          <h3 className="text-xl font-light text-teal-200/90 mb-4 tracking-wide">
            {selectedGenre == null ? "Recommendations" : `All ${selectedGenre} movies`}
          </h3>

          <div className="w-full">
            {(selectedGenre == null ? loadingRecommendations : loadingGenre) ? (
              <div className="flex gap-6 overflow-hidden pb-4">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className="flex-shrink-0 w-[320px] h-[600px] rounded-2xl bg-white/5 border border-teal-500/20 animate-pulse"
                  >
                    <div className="w-full h-[450px] bg-white/10 rounded-t-2xl" />
                    <div className="p-4 space-y-3">
                      <div className="h-5 bg-white/10 rounded w-3/4" />
                      <div className="h-4 bg-white/10 rounded w-1/2" />
                      <div className="h-4 bg-white/10 rounded w-full" />
                    </div>
                  </div>
                ))}
              </div>
            ) : selectedGenre == null ? (
              movies.length > 0 ? (
                <HolographicGallery
                  movies={movies}
                onLike={(title) => {
                  devLog('🎯 Dashboard: onLike called with:', title);
                  handleLike(title);
                }}
                onDislike={(title) => {
                  devLog('🎯 Dashboard: onDislike called with:', title);
                  handleDislike(title);
                }}
                onFavorite={(title) => {
                  devLog('🎯 Dashboard: onFavorite called with:', title);
                  handleFavorite(title);
                }}
                onReview={handleReview}
                userInteractions={userInteractions}
                onShare={handleShare}
                onToggleWatchlist={handleToggleWatchlist}
                isInWatchlist={(movieId) => watchlist.some(w => w.movie_id === movieId)}
                />
              ) : (
                <div className="text-center py-16 rounded-2xl border border-teal-500/20 bg-white/5">
                  <div className="text-4xl mb-4">🎬</div>
                  <div className="text-xl text-gray-300 mb-2">No recommendations yet</div>
                  <div className="text-gray-500 mb-6 max-w-md mx-auto">
                    Like a few movies, add some to your watchlist, or try Refresh. We’ll curate picks for you.
                  </div>
                  <button
                    onClick={fetchRecommendations}
                    disabled={loadingRecommendations}
                    className="px-6 py-3 bg-gradient-to-r from-teal-400 to-blue-500 text-white rounded-lg font-medium hover:scale-105 transition-all duration-300 disabled:opacity-50"
                  >
                    Refresh recommendations
                  </button>
                </div>
              )
            ) : genreMovies.length > 0 ? (
              <HolographicGallery
                movies={genreMovies}
                onLike={(title) => handleLike(title)}
                onDislike={(title) => handleDislike(title)}
                onFavorite={(title) => handleFavorite(title)}
                onReview={handleReview}
                userInteractions={userInteractions}
                onShare={handleShare}
                onToggleWatchlist={handleToggleWatchlist}
                isInWatchlist={(movieId) => watchlist.some(w => w.movie_id === movieId)}
              />
            ) : (
              <div className="text-center py-16 rounded-2xl border border-teal-500/20 bg-white/5">
                <div className="text-4xl mb-4">🎬</div>
                <div className="text-xl text-gray-300 mb-2">No movies in this genre</div>
                <div className="text-gray-500 mb-6 max-w-md mx-auto">
                  Try another genre or go back to recommendations.
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedGenre(null)}
                  className="px-6 py-3 bg-black/70 border border-teal-700 text-teal-200 rounded-lg font-medium hover:border-teal-500 hover:bg-teal-500/10 transition-all duration-300"
                >
                  Back to recommendations
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Hidden gems channel: high quality, lower popularity — only on recommendations view */}
        {selectedGenre == null && (
          <section className="mt-10 mb-8 px-4 md:px-6">
            <div className="max-w-7xl mx-auto">
              <h2 className="text-xl font-semibold text-teal-200 mb-1 tracking-wide">
                Hidden gems
              </h2>
              <p className="text-sm text-teal-400/80 mb-4">
                High-quality picks that fly under the radar
              </p>
              {loadingHiddenGems ? (
                <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className="flex-shrink-0 w-[280px] h-[480px] rounded-xl bg-white/5 border border-teal-500/20 animate-pulse"
                    >
                      <div className="w-full h-[380px] bg-white/10 rounded-t-xl" />
                      <div className="p-3 space-y-2">
                        <div className="h-4 bg-white/10 rounded w-2/3" />
                        <div className="h-3 bg-white/10 rounded w-1/2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : hiddenGems.length > 0 ? (
                <div className="overflow-x-auto pb-4 scrollbar-thin -mx-2 px-2" style={{ scrollbarWidth: "thin" }}>
                  <HolographicGallery
                    movies={hiddenGems}
                    onLike={handleLike}
                    onDislike={handleDislike}
                    onFavorite={handleFavorite}
                    onReview={handleReview}
                    userInteractions={userInteractions}
                    onShare={handleShare}
                    onToggleWatchlist={handleToggleWatchlist}
                    isInWatchlist={(movieId) => watchlist.some((w) => w.movie_id === movieId)}
                  />
                </div>
              ) : (
                <div className="py-8 rounded-xl border border-teal-500/20 bg-white/5 text-center text-teal-400/70 text-sm">
                  No hidden gems right now. Check back later.
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      {/* Sidebar - Glassmorphism */}
      <DashboardSidebar
        recentActivity={recentActivity}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Surprise Me Modal */}
      <SurpriseMeModal
        isOpen={showSurpriseModal}
        onClose={() => setShowSurpriseModal(false)}
        movies={surpriseMovies}
        loading={loadingSurprise}
        onLike={handleLike}
        onDislike={handleDislike}
        onFavorite={handleFavorite}
        onReview={handleReview}
        onShare={handleShare}
        onToggleWatchlist={handleToggleWatchlist}
        isInWatchlist={(movieId) => watchlist.some(w => w.movie_id === movieId)}
        userInteractions={userInteractions}
      />

      {/* Movie Reviews Modal (your review + others) */}
      <MovieReviewsModal
        isOpen={!!reviewModalMovie}
        onClose={() => setReviewModalMovie(null)}
        movie={reviewModalMovie}
        onReviewSubmitted={handleReviewSubmitted}
      />

      <HowItWorksModal
        isOpen={howItWorksOpen}
        onClose={() => setHowItWorksOpen(false)}
      />
    </div>
  );
}