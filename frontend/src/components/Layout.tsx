import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { BookOpen, BrainCircuit, Home, LogOut, Settings2, Sparkles, Trophy } from 'lucide-react';
import { AuthStore } from '../store/auth';

const navItems = [
  { to: '/app', label: 'Home', icon: Home },
  { to: '/library', label: 'Library', icon: BookOpen },
  { to: '/chat', label: 'AI Tutor', icon: BrainCircuit },
  { to: '/quiz', label: 'Quiz', icon: Trophy },
  { to: '/profile', label: 'Profile', icon: Settings2 },
];

export default function Layout() {
  const navigate = useNavigate();
  const { user, logout } = AuthStore();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <div className="student-shell">
      <header className="student-topbar-shell">
        <div className="student-topbar">
          <Link to="/app" className="student-brand">
            <span className="student-brand-mark">
              <Sparkles size={18} />
            </span>
            <strong>VidyaAI</strong>
          </Link>

          <nav className="student-nav">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `student-nav-link${isActive ? ' active' : ''}`}>
                <Icon size={16} />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="student-topbar-actions">
            <span className="student-topbar-chip">Class {user?.class_grade || '10'}</span>
            <button className="student-signout" onClick={handleLogout}>Log out</button>
          </div>
        </div>
      </header>

      <main className="student-page-shell">
        <Outlet />
      </main>
    </div>
  );
}
