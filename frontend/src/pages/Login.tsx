import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { AuthStore } from '../store/auth';

export default function Login() {
  const navigate = useNavigate();
  const login = AuthStore((state) => state.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/app');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to sign in right now.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-reference-page">
      <div className="auth-reference-shell narrow-shell">
        <div className="auth-reference-brand">
          <span className="student-brand-mark"><Sparkles size={18} /></span>
          <strong>VidyaAI</strong>
        </div>

        <section className="auth-reference-card auth-form-reference-card">
          <div className="auth-reference-head centered-head">
            <h1>Welcome back</h1>
            <p>Continue from your chapters, topics, and AI learning sessions.</p>
          </div>

          <form className="auth-form reference-auth-form" onSubmit={handleSubmit}>
            <label>
              <span>Email *</span>
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
            </label>

            <label>
              <span>Password *</span>
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
            </label>

            {error ? <div className="form-error">{error}</div> : null}

            <button className="primary-button full-width-button" type="submit" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="auth-switch center-switch">
            New here? <Link to="/register">Create your account</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
