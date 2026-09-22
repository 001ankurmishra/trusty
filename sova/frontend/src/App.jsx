import { Routes, Route, Navigate } from "react-router-dom";
import { AppContext, useAppState } from "./store.js";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Workbench from "./pages/Workbench.jsx";
import Documents from "./pages/Documents.jsx";
import Security from "./pages/Security.jsx";
import Audit from "./pages/Audit.jsx";
import Rules from "./pages/Rules.jsx";
import Inbox from "./pages/Inbox.jsx";
import ModelRouterPage from "./pages/ModelRouterPage.jsx";
import Metrics from "./pages/Metrics.jsx";

function Protected({ user, children }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const state = useAppState();

  return (
    <AppContext.Provider value={state}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <Protected user={state.user}>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/workbench" element={<Workbench />} />
                  <Route path="/documents" element={<Documents />} />
                  <Route path="/rules" element={<Rules />} />
                  <Route path="/inbox" element={<Inbox />} />
                  <Route path="/models" element={<ModelRouterPage />} />
                  <Route path="/metrics" element={<Metrics />} />
                  <Route path="/security" element={<Security />} />
                  <Route path="/audit" element={<Audit />} />
                </Routes>
              </Layout>
            </Protected>
          }
        />
      </Routes>
    </AppContext.Provider>
  );
}
