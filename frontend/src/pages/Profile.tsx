import { FormEvent, useEffect, useState } from 'react';
import { AuthStore } from '../store/auth';

const CLASS_OPTIONS = ['4', '5', '6', '7', '8', '9', '10', '11', '12'];

export default function Profile() {
  const user = AuthStore((state) => state.user);
  const updateProfile = AuthStore((state) => state.updateProfile);

  const [fullName, setFullName] = useState('');
  const [classGrade, setClassGrade] = useState('10');
  const [rollNumber, setRollNumber] = useState('');
  const [schoolName, setSchoolName] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name || '');
    setClassGrade(user.class_grade || '10');
    setRollNumber(user.roll_number || '');
    setSchoolName(user.school_name || '');
  }, [user]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setMessage('');
    setError('');

    try {
      await updateProfile({
        full_name: fullName,
        class_grade: classGrade,
        roll_number: rollNumber,
        school_name: schoolName,
      });
      setMessage('Profile updated. Your library and subjects will now follow this class.');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to save your profile right now.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="reference-page-stack">
      <section className="library-reference-header smoother-header-card">
        <div>
          <h1>Your Profile</h1>
          <p>Keep your learning setup accurate so the right class content appears everywhere.</p>
        </div>
      </section>

      <section className="panel-card profile-card">
        <form className="auth-form reference-auth-form profile-form" onSubmit={handleSubmit}>
          <label>
            <span>Full Name</span>
            <input value={fullName} onChange={(event) => setFullName(event.target.value)} />
          </label>

          <label>
            <span>Your Class</span>
            <select value={classGrade} onChange={(event) => setClassGrade(event.target.value)}>
              {CLASS_OPTIONS.map((grade) => <option key={grade} value={grade}>Class {grade}</option>)}
            </select>
          </label>

          <label>
            <span>Roll Number</span>
            <input value={rollNumber} onChange={(event) => setRollNumber(event.target.value)} />
          </label>

          <label>
            <span>School Name</span>
            <input value={schoolName} onChange={(event) => setSchoolName(event.target.value)} />
          </label>

          {message ? <div className="form-success">{message}</div> : null}
          {error ? <div className="form-error">{error}</div> : null}

          <button className="primary-button" type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </section>
    </div>
  );
}
