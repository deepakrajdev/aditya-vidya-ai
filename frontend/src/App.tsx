import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { useEffect } from 'react';
import { AuthStore } from './store/auth';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';
import Subject from './pages/Subject';
import Chapter from './pages/Chapter';
import Chat from './pages/Chat';
import Quiz from './pages/Quiz';
import Profile from './pages/Profile';
import './index.css';

function App() {
  const { token, hydrated, checkAuth } = AuthStore();

  useEffect(() => {
    if (hydrated && token) {
      void checkAuth();
    }
  }, [hydrated, token, checkAuth]);

  if (!hydrated) {
    return (
      <div className="app-loading">
        <div className="spinner" />
        <p>Loading VidyaAI...</p>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={token ? <Navigate to="/app" replace /> : <Login />} />
        <Route path="/register" element={token ? <Navigate to="/app" replace /> : <Register />} />

        <Route element={token ? <Layout /> : <Navigate to="/login" replace />}>
          <Route path="/app" element={<Dashboard />} />
          <Route path="/library" element={<Library />} />
          <Route path="/subject/:subjectId" element={<Subject />} />
          <Route path="/chapter/:bookId" element={<Chapter />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/quiz" element={<Quiz />} />
          <Route path="/profile" element={<Profile />} />
        </Route>

        <Route path="*" element={<Navigate to={token ? '/app' : '/'} replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
