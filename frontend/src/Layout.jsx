import { Link, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="app">
      <nav className="top-nav">
        <Link to="/" className="top-nav-brand">
          <span className="brand-badge">CT</span>
          <span>ClearTrade</span>
        </Link>
        <div className="top-nav-links">
          <Link to="/" className="top-nav-link">
            Dashboard
          </Link>
          <Link to="/history" className="top-nav-link">
            History
          </Link>
        </div>
      </nav>
      <Outlet />
    </div>
  );
}
