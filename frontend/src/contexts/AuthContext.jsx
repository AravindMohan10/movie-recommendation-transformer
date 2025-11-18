// src/contexts/AuthContext.jsx
import React, { createContext, useContext, useEffect, useState } from "react";
import { getMe as apiGetMe, logout as apiLogout, prefetchDashboardData } from "../Utils/api";

const defaultAuth = {
  user: null,
  loading: true,
  isAuthenticated: false,
  authError: null,
  logout: async () => {},
  login: async () => {},
  refreshAuth: () => {},
  setUser: () => {},
};
const AuthContext = createContext(defaultAuth);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(null);

  // Check authentication status on mount and token changes
  const checkAuth = async () => {
    try {
      setLoading(true);
      setAuthError(null);
      
      // Check if we have a token
      const token = localStorage.getItem('cineai_token');
      if (!token) {
        setUser(null);
        setIsAuthenticated(false);
        return;
      }
      
      const userData = await apiGetMe();
      setUser(userData);
      setIsAuthenticated(true);
      // Warm up key data so dashboard loads instantly
      prefetchDashboardData();
    } catch (error) {
      console.log('Authentication check failed:', error.message);
      setUser(null);
      setIsAuthenticated(false);
      localStorage.removeItem('cineai_token'); // Clear invalid token
      
      // Only set error if it's not a network error
      if (!error.message.includes('Failed to connect')) {
        setAuthError('Session expired. Please login again.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    setAuthError(null);
    prefetchDashboardData();
  };

  const logout = async () => {
    try {
      // Clear token first
      localStorage.removeItem('cineai_token');
      
      // Update state immediately
      setUser(null);
      setIsAuthenticated(false);
      setAuthError(null);
      
      // Try to call logout API (but don't wait for it)
      apiLogout().catch(error => {
        console.error('Logout API call failed:', error);
      });
      
      // Redirect to home page
      window.location.href = "/";
    } catch (error) {
      console.error('Logout error:', error);
      // Even if there's an error, clear everything and redirect
      localStorage.removeItem('cineai_token');
      setUser(null);
      setIsAuthenticated(false);
      setAuthError(null);
      window.location.href = "/";
    }
  };

  const refreshAuth = () => {
    checkAuth();
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      loading, 
      isAuthenticated,
      authError,
      logout, 
      login,
      refreshAuth,
      setUser 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}