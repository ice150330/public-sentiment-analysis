import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  AuthSession,
  AuthUser,
  clearAuthToken,
  getAuthToken,
  getCurrentUser,
  login as loginRequest,
  register as registerRequest,
  saveAuthToken,
} from '../services/api';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<AuthSession>;
  register: (username: string, password: string, email?: string) => Promise<AuthSession>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const response = await getCurrentUser();
      setUser(response.data);
    } catch {
      clearAuthToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await loginRequest({ username, password });
    saveAuthToken(response.data.access_token);
    setUser(response.data.user);
    return response.data;
  }, []);

  const register = useCallback(async (username: string, password: string, email?: string) => {
    const response = await registerRequest({ username, password, email: email || undefined });
    saveAuthToken(response.data.access_token);
    setUser(response.data.user);
    return response.data;
  }, []);

  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refresh }),
    [user, loading, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return value;
};
