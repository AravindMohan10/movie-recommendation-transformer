// src/Utils/api.js
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

// Helper function to handle API responses
async function handleResponse(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    // Handle Pydantic validation errors (detail is an array) or simple error strings
    let errorMessage;
    if (Array.isArray(errorData.detail)) {
      // Extract message from first validation error
      errorMessage = errorData.detail[0]?.msg || errorData.detail[0]?.message || JSON.stringify(errorData.detail);
    } else if (typeof errorData.detail === 'string') {
      errorMessage = errorData.detail;
    } else {
      errorMessage = errorData.message || `HTTP error! status: ${response.status}`;
    }
    throw new Error(errorMessage);
  }
  return response.json();
}

export async function signup({ username, email, password }) {
  try {
    const res = await fetch(`${API_BASE}/signup`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Signup error:', error);
    // Check for CORS/preflight errors specifically
    if (error.message.includes('CORS') || error.message.includes('preflight') || error.message.includes('Access-Control')) {
      throw new Error('CORS error: Backend is not allowing requests from this origin. Check ALLOWED_ORIGINS on Fly.io.');
    }
    if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
      throw new Error('Failed to connect to server. Please check if the backend is running and CORS is configured.');
    }
    throw error;
  }
}

export async function login(usernameOrEmail, password) {
  try {
    const form = new URLSearchParams();
    form.append("username", usernameOrEmail);
    form.append("password", password);

    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    
    const data = await handleResponse(res);
    
    // Store token in localStorage for frontend use
    if (data.access_token) {
      localStorage.setItem('cineai_token', data.access_token);
    }
    
    // Return the data directly without extra API call
    return data;
  } catch (error) {
    console.error('Login error:', error);
    if (error.message.includes('Failed to fetch')) {
      throw new Error('Failed to connect to server. Please check if the backend is running.');
    }
    throw error;
  }
}

export async function getMe() {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
    };

    const res = await fetch(`${API_BASE}/me`, {
      method: "GET",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('GetMe error:', error);
    throw error;
  }
}

export async function logout() {
  try {
    const res = await fetch(`${API_BASE}/logout`, {
      method: "POST",
      credentials: "include",
    });
    
    // Always clear the token regardless of API response
    localStorage.removeItem('cineai_token');
    
    // Only throw if it's a server error (5xx), not auth errors (4xx)
    if (res.status >= 500) {
      throw new Error(`Server error: ${res.status}`);
    }
    
    return res.ok ? await res.json() : { message: "Logged out" };
  } catch (error) {
    console.error('Logout request failed:', error);
    // Always clear the token even if API fails
    localStorage.removeItem('cineai_token');
    // Don't throw error - logout should always succeed locally
    return { message: "Logged out" };
  }
}

export async function getOnboardingStatus() {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
    };

    const res = await fetch(`${API_BASE}/recommendations/onboarding/status`, {
      method: "GET",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Get onboarding status error:', error);
    throw error;
  }
}

export async function completeOnboarding(onboardingData) {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };

    const res = await fetch(`${API_BASE}/recommendations/onboarding/complete`, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify(onboardingData),
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Complete onboarding error:', error);
    throw error;
  }
}

export async function updateOnboarding(onboardingData) {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };

    const res = await fetch(`${API_BASE}/recommendations/onboarding/update`, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify(onboardingData),
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Update onboarding error:', error);
    throw error;
  }
}

export async function getRecommendations(limit = 10) {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
    };

    const res = await fetch(`${API_BASE}/recommendations?limit=${limit}`, {
      method: "GET",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Get recommendations error:', error);
    throw error;
  }
}

/** Surprise Me: random quality picks (no documentaries, no adult). */
export async function getSurpriseMe(limit = 5) {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
    };
    const res = await fetch(`${API_BASE}/recommendations/surprise-me?limit=${limit}`, {
      method: "GET",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Get surprise me error:', error);
    throw error;
  }
}

export async function getWatchlist() {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
    };

    const res = await fetch(`${API_BASE}/watchlist`, {
      method: "GET",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Get watchlist error:', error);
    throw error;
  }
}

export async function addToWatchlist(movieId) {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };

    const res = await fetch(`${API_BASE}/watchlist/add?movie_id=${movieId}`, {
      method: "POST",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Add to watchlist error:', error);
    throw error;
  }
}

export async function removeFromWatchlist(movieId) {
  try {
    const token = localStorage.getItem('cineai_token');
    const headers = {
      'Authorization': `Bearer ${token}`,
    };

    const res = await fetch(`${API_BASE}/watchlist/remove/${movieId}`, {
      method: "DELETE",
      credentials: "include",
      headers,
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Remove from watchlist error:', error);
    throw error;
  }
}

export async function forgotPassword(email) {
  try {
    const res = await fetch(`${API_BASE}/forgot-password`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Forgot password error:', error);
    throw error;
  }
}

export async function verifyResetToken(token) {
  try {
    // URL encode the token to handle special characters
    const encodedToken = encodeURIComponent(token);
    const res = await fetch(`${API_BASE}/reset-password/verify/${encodedToken}`, {
      method: "GET",
      credentials: "include",
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Verify reset token error:', error);
    throw error;
  }
}

export async function resetPassword(token, newPassword) {
  try {
    const res = await fetch(`${API_BASE}/reset-password`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    return handleResponse(res);
  } catch (error) {
    console.error('Reset password error:', error);
    throw error;
  }
}

function authHeaders() {
  const token = localStorage.getItem('cineai_token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

export async function getMyReviews() {
  const res = await fetch(`${API_BASE}/reviews/my`, {
    method: "GET",
    credentials: "include",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getMovieReviews(movieId) {
  const res = await fetch(`${API_BASE}/reviews/movie/${movieId}`, {
    method: "GET",
    credentials: "include",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function submitReview(movieId, rating, reviewText) {
  const res = await fetch(`${API_BASE}/recommendations/interact`, {
    method: "POST",
    credentials: "include",
    headers: authHeaders(),
    body: JSON.stringify({
      movie_id: movieId,
      action: 'review',
      rating: Number(rating),
      review_text: reviewText || null,
    }),
  });
  return handleResponse(res);
}

/** Public: fetch movie by id (for share page). No auth. */
export async function getMovieById(movieId) {
  const res = await fetch(`${API_BASE}/movies/${movieId}`, {
    method: "GET",
    credentials: "include",
  });
  return handleResponse(res);
}

/** Public: list of genre names for browse-by-genre. No auth. */
export async function getGenres() {
  const res = await fetch(`${API_BASE}/movies/genres`, {
    method: "GET",
    credentials: "include",
  });
  return handleResponse(res);
}

/** Public: all movies in a genre from catalog (not recommendations). No auth. */
export async function getMoviesByGenre(genre, limit = 80) {
  const res = await fetch(
    `${API_BASE}/movies/by-genre?genre=${encodeURIComponent(genre)}&limit=${limit}`,
    { method: "GET", credentials: "include" }
  );
  return handleResponse(res);
}

export async function searchMovies(query) {
  if (!query || String(query).trim().length < 2) return { results: [] };
  const res = await fetch(
    `${API_BASE}/movies/search?query=${encodeURIComponent(String(query).trim())}`,
    { method: "GET", credentials: "include" }
  );
  return handleResponse(res);
}

/** Public. Truly random good movies (no docs) for landing page. */
export async function getRandomMovies(limit = 12) {
  const res = await fetch(`${API_BASE}/movies/random?limit=${limit}`, {
    method: "GET",
    credentials: "include",
  });
  return handleResponse(res);
}

// --- Hidden gems (high quality, low popularity; configurable backend) ---

/** Authenticated. Hidden gems: high quality, low popularity, serendipity-ranked. */
export async function getHiddenGems(limit = 15) {
  const res = await fetch(`${API_BASE}/recommendations/hidden-gems?limit=${limit}`, {
    method: "GET",
    credentials: "include",
  });
  return handleResponse(res);
}

// --- News digest (personalized articles; you provide content via POST) ---

/** Authenticated. Personalized news digest for current user. */
export async function getNewsDigest(limit = 10) {
  const res = await fetch(`${API_BASE}/news/digest?limit=${limit}`, {
    method: "GET",
    credentials: "include",
  });
  return handleResponse(res);
}

/** Authenticated. Ingest one article (title, content, optional url, tags). */
export async function createNewsArticle(body) {
  const res = await fetch(`${API_BASE}/news`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handleResponse(res);
}