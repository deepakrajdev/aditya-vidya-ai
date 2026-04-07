import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { AuthStore } from '../store/auth';

const CLASS_OPTIONS = ['4', '5', '6', '7', '8', '9', '10', '11', '12'];

export default function Register() {
  const navigate = useNavigate();
  const register = AuthStore((state) => state.register);
  const [fullName, setFullName] = useState('');
  const [rollNumber, setRollNumber] = useState('');
  const [schoolName, setSchoolName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [classGrade, setClassGrade] = useState('10');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(email, fullName, password, classGrade, rollNumber, schoolName);
      navigate('/app');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to create your account right now.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-reference-page">
      <div className="auth-reference-shell">
        <div className="auth-reference-brand">
          <span className="student-brand-mark"><Sparkles size={18} /></span>
          <strong>VidyaAI</strong>
        </div>

        <section className="auth-reference-card auth-form-reference-card">
          <div className="auth-reference-head centered-head">
            <h1>Welcome to VidyaAI!</h1>
            <p>Set up your student profile to get started with personalized learning.</p>
          </div>

          <form className="auth-form reference-auth-form" onSubmit={handleSubmit}>
            <label>
              <span>Full Name *</span>
              <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Arjun Sharma" required />
            </label>

            <label>
              <span>Roll Number *</span>
              <input value={rollNumber} onChange={(event) => setRollNumber(event.target.value)} placeholder="e.g. 2024001" required />
            </label>

            <label>
              <span>Your Class *</span>
              <select value={classGrade} onChange={(event) => setClassGrade(event.target.value)}>
                {CLASS_OPTIONS.map((grade) => <option key={grade} value={grade}>Class {grade}</option>)}
              </select>
            </label>

            <label>
              <span>School Name <em>(optional)</em></span>
              <input value={schoolName} onChange={(event) => setSchoolName(event.target.value)} placeholder="Delhi Public School" />
            </label>

            <label>
              <span>Email *</span>
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
            </label>

            <label>
              <span>Password *</span>
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" minLength={8} required />
            </label>

            {error ? <div className="form-error">{error}</div> : null}

            <button className="primary-button full-width-button" type="submit" disabled={loading}>
              {loading ? 'Starting...' : 'Start Learning'}
            </button>
          </form>

          <p className="auth-switch center-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </section>
      </div>
    </div>
  );
}
