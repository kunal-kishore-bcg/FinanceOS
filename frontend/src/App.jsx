import { useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import Dashboard from "./pages/Dashboard.jsx";

export default function App() {
  // The token lives only in React state — never localStorage or
  // sessionStorage, per the "in memory" requirement. Consequence: a
  // page refresh logs the user out. That's the trade-off of "in
  // memory," not a bug — flagging it so it doesn't look broken in
  // the demo if someone hits refresh mid-review.
  const [token, setToken] = useState(null);
  const [userEmail, setUserEmail] = useState(null);

  function handleLogin(accessToken, email) {
    setToken(accessToken);
    setUserEmail(email);
  }

  function handleLogout() {
    setToken(null);
    setUserEmail(null);
  }

  if (!token) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return <Dashboard token={token} userEmail={userEmail} onLogout={handleLogout} />;
}
