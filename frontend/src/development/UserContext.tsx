/** Geliştirme modu kullanıcı yönetimi context ve provider'ı. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchDevelopmentUsers, type DevelopmentUserInfo } from "./api";

const STORAGE_KEY = "development-user-id";

interface UserContextValue {
  currentUser: DevelopmentUserInfo | null;
  availableUsers: DevelopmentUserInfo[];
  setCurrentUser: (user: DevelopmentUserInfo) => void;
  clearCurrentUser: () => void;
  isLoading: boolean;
  headerValue: string | undefined;
}

const UserContext = createContext<UserContextValue>({
  currentUser: null,
  availableUsers: [],
  setCurrentUser: () => {},
  clearCurrentUser: () => {},
  isLoading: true,
  headerValue: undefined,
});

export function useDevelopmentUser(): UserContextValue {
  return useContext(UserContext);
}

export function DevelopmentUserProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUserState] = useState<DevelopmentUserInfo | null>(null);
  const [availableUsers, setAvailableUsers] = useState<DevelopmentUserInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedUserId = localStorage.getItem(STORAGE_KEY);
    fetchDevelopmentUsers()
      .then((response) => {
        setAvailableUsers(response.items);
        if (savedUserId) {
          const saved = response.items.find((u) => u.user_id === savedUserId);
          if (saved) {
            setCurrentUserState(saved);
          }
        }
        setIsLoading(false);
      })
      .catch(() => {
        setIsLoading(false);
      });
  }, []);

  const setCurrentUser = useCallback((user: DevelopmentUserInfo) => {
    localStorage.setItem(STORAGE_KEY, user.user_id);
    setCurrentUserState(user);
  }, []);

  const clearCurrentUser = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setCurrentUserState(null);
  }, []);

  const headerValue = useMemo(() => currentUser?.user_id, [currentUser]);

  return (
    <UserContext.Provider value={{ currentUser, availableUsers, setCurrentUser, clearCurrentUser, isLoading, headerValue }}>
      {children}
    </UserContext.Provider>
  );
}