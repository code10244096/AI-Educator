import { create } from 'zustand'

export const useAppStore = create((set) => ({
  // 当前页面
  currentPage: 'grader',
  setCurrentPage: (page) => set({ currentPage: page }),
  
  // 用户信息
  user: null,
  setUser: (user) => set({ user }),
  
  // 主题
  darkMode: false,
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}))
