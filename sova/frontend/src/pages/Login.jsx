import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApp } from "../store.js";
import client, { API_BASE } from "../api/client.js";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useApp();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const form = new URLSearchParams();
      form.append("username", username);
      form.append("password", password);
      const res = await client.post("/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      login({ username: res.data.username, role: res.data.role }, res.data.access_token);
      navigate("/");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed. Is the backend running on " + API_BASE + "?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-sova-bg">
      <div className="w-full max-w-sm card">
        <div className="text-center mb-6">
          <div className="font-mono text-sova-accent font-bold text-2xl">TrustForge</div>
          <div className="text-sova-subtext text-xs mt-1">Secure AI Workbench</div>
          <div className="text-sova-subtext text-[11px] mt-3 italic">
            "Private by Architecture. Intelligent by Design. Verified by Default."
          </div>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="text-xs text-sova-subtext">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full mt-1 bg-sova-panel2 border border-sova-border rounded-lg px-3 py-2 text-sm outline-none focus:border-sova-accent"
            />
          </div>
          <div>
            <label className="text-xs text-sova-subtext">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full mt-1 bg-sova-panel2 border border-sova-border rounded-lg px-3 py-2 text-sm outline-none focus:border-sova-accent"
            />
          </div>
          {error && <div className="text-red-400 text-xs">{error}</div>}
          <button disabled={loading} className="btn btn-primary w-full mt-2">
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="text-[11px] text-sova-subtext mt-4 text-center">
          Default: admin / admin123 · reviewer / reviewer123
        </div>
      </div>
    </div>
  );
}
