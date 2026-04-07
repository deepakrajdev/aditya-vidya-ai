import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../api/client';

export interface User {
  id: number;
  email: string;
  full_name: string;
  class_grade: string;
  plan_type: string;
  roll_number?: string;
  school_name?: string;
  subscription_active?: boolean;
  created_at?: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  hydrated: boolean;
  register: (email: string, fullName: string, password: string, classGrade: string, rollNumber?: string, schoolName?: string) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  setHydrated: (value: boolean) => void;
  updateProfile: (profile: Partial<Pick<User, 'full_name' | 'class_grade' | 'roll_number' | 'school_name'>>) => Promise<void>;
}

export const AuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      hydrated: false,

      register: async (email, fullName, password, classGrade, rollNumber, schoolName) => {
        const response = await api.post('/auth/register', {
          email,
          full_name: fullName,
          password,
          class_grade: classGrade,
          roll_number: rollNumber,
          school_name: schoolName,
        });
        set({ token: response.data.access_token, user: response.data.user });
      },

      login: async (email, password) => {
        const response = await api.post('/auth/login', { email, password });
        set({
          token: response.data.access_token,
          user: response.data.user,
        });
      },

      logout: () => set({ token: null, user: null }),

      checkAuth: async () => {
        if (!get().token) return;
        try {
          const response = await api.get('/auth/me');
          set({ user: response.data });
        } catch {
          set({ token: null, user: null });
        }
      },

      setHydrated: (value) => set({ hydrated: value }),
      updateProfile: async (profile) => {
        const response = await api.patch('/auth/profile', profile);
        set({ user: response.data });
      },
    }),
    {
      name: 'vidya-auth',
      partialize: (state) => ({ token: state.token, user: state.user }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated(true);
      },
    },
  ),
);
