import { useState } from "react";
import { useAuth } from "../store/auth";

export function AuthScreen() {
  const { login, register, status, error } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [identifier, setIdentifier] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const busy = status === "loading";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (mode === "login") {
        await login(identifier, password);
      } else {
        await register(username, email, password);
      }
    } catch {
      /* error surfaced via store */
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="hex auth-hex">M</div>
        <h1 className="auth-title">{mode === "login" ? "Welcome back" : "Join the hive"}</h1>
        <p className="auth-subtitle">
          {mode === "login" ? "Sign in to Memorum" : "Create your Memorum account"}
        </p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={submit}>
          {mode === "login" ? (
            <div className="auth-field">
              <label>Username or email</label>
              <input value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
            </div>
          ) : (
            <>
              <div className="auth-field">
                <label>Username</label>
                <input value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} />
              </div>
              <div className="auth-field">
                <label>Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
            </>
          )}
          <div className="auth-field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          <button className="auth-submit" disabled={busy} type="submit">
            {busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <div className="auth-switch">
          {mode === "login" ? (
            <>
              New here? <button onClick={() => setMode("register")}>Create an account</button>
            </>
          ) : (
            <>
              Already have an account? <button onClick={() => setMode("login")}>Sign in</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
