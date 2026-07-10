import { create } from "zustand";

export interface User {
  id: string;
  username: string;
  email: string;
  is_superuser: boolean;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("access_token"),
  user: JSON.parse(localStorage.getItem("user") ?? "null"),
  setAuth: (token, user) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(user));
    set({ token, user });
  },
  clear: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    set({ token: null, user: null });
  },
}));
