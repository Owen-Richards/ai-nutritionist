import * as SecureStore from "expo-secure-store";
import React from "react";
import * as Sentry from "sentry-expo";

import { queryClient } from "@/utils/queryClient";

export type AuthStatus = "checking" | "authenticated" | "unauthenticated";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
};

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  signIn: (token: string, profile?: Partial<AuthUser>) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = "ai-health-access-token";

const demoUser: AuthUser = {
  id: "demo-user",
  name: "Demo Member",
  email: "demo@ai-health.app"
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = React.useState<AuthStatus>("checking");
  const [user, setUser] = React.useState<AuthUser | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = await SecureStore.getItemAsync(TOKEN_KEY);
        if (cancelled) return;
        if (token) {
          setUser(demoUser);
          setStatus("authenticated");
        } else {
          setStatus("unauthenticated");
        }
      } catch (error) {
        console.warn("Failed to read auth token", error);
        if (!cancelled) {
          setStatus("unauthenticated");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    if (user) {
      Sentry.Native.setUser({ id: user.id });
    } else {
      Sentry.Native.setUser(null);
    }
  }, [user]);

  const signIn = React.useCallback(async (token: string, profile?: Partial<AuthUser>) => {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    setUser({ ...demoUser, ...profile });
    setStatus("authenticated");
    queryClient.invalidateQueries({ refetchType: "active" }).catch((error) => {
      console.warn("Failed to refresh queries after sign-in", error);
    });
  }, []);

  const signOut = React.useCallback(async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setUser(null);
    setStatus("unauthenticated");
    queryClient.clear();
  }, []);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      signIn,
      signOut
    }),
    [signIn, signOut, status, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
