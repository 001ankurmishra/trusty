import { createContext, useContext, useState } from "react";

export const AppContext = createContext(null);

export function useApp() {
  return useContext(AppContext);
}

export function useAppState() {
  const [user, setUser] = useState(() => {
    const u = localStorage.getItem("sova_user");
    return u ? JSON.parse(u) : null;
  });
  const [project, setProject] = useState(() => {
    const p = localStorage.getItem("sova_project");
    return p ? JSON.parse(p) : null;
  });

  const login = (userData, token) => {
    localStorage.setItem("sova_token", token);
    localStorage.setItem("sova_user", JSON.stringify(userData));
    setUser(userData);
  };
  const logout = () => {
    localStorage.removeItem("sova_token");
    localStorage.removeItem("sova_user");
    localStorage.removeItem("sova_project");
    setUser(null);
    setProject(null);
  };
  const selectProject = (p) => {
    localStorage.setItem("sova_project", JSON.stringify(p));
    setProject(p);
  };

  return { user, project, login, logout, selectProject };
}
