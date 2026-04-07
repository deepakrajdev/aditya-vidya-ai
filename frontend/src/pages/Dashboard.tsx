import { ChevronRight, Calendar, CheckCircle, Plus } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { getSubjectMeta } from '../lib/learning';
import { AuthStore } from '../store/auth';

interface Chapter {
  id: number;
  chapter_num: number;
  chapter: string;
}

interface SubjectMap {
  [subject: string]: Chapter[];
}

interface DashboardStats {
  totalChats: number;
  totalQuizzes: number;
  totalSummaries: number;
  booksAccessed: number;
}

interface ProgressState {
  streak_days: number;
  recent_activity: Array<{ type: string; chapter: string; subject: string; timestamp: string; score_percent?: number }>;
  weak_topics: Array<{ subject: string; chapter: string; score_percent: number }>;
  revision_queue: Array<{ subject: string; chapter: string; reason: string }>;
}

interface Todo {
  id: string;
  text: string;
  completed: boolean;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const user = AuthStore((state) => state.user);
  const [subjects, setSubjects] = useState<SubjectMap>({});
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [todos, setTodos] = useState<Todo[]>(() => {
    const saved = localStorage.getItem('student_todos');
    return saved ? JSON.parse(saved) : [];
  });
  const [newTodo, setNewTodo] = useState('');
  const [currentDate, setCurrentDate] = useState(new Date());

  useEffect(() => {
    const load = async () => {
      const [libraryResponse, statsResponse, progressResponse] = await Promise.all([
        api.get(`/library/books/${user?.class_grade || '10'}`),
        api.get('/dashboard/stats'),
        api.get('/dashboard/progress'),
      ]);
      setSubjects(libraryResponse.data.subjects || {});
      setStats(statsResponse.data);
      setProgress(progressResponse.data);
    };

    void load();
  }, [user?.class_grade]);

  const saveTodos = (updatedTodos: Todo[]) => {
    setTodos(updatedTodos);
    localStorage.setItem('student_todos', JSON.stringify(updatedTodos));
  };

  const addTodo = () => {
    if (newTodo.trim()) {
      saveTodos([...todos, { id: Date.now().toString(), text: newTodo, completed: false }]);
      setNewTodo('');
    }
  };

  const toggleTodo = (id: string) => {
    saveTodos(todos.map(todo => todo.id === id ? { ...todo, completed: !todo.completed } : todo));
  };

  const deleteTodo = (id: string) => {
    saveTodos(todos.filter(todo => todo.id !== id));
  };

  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const generateCalendarDays = () => {
    const daysInMonth = getDaysInMonth(currentDate);
    const firstDay = getFirstDayOfMonth(currentDate);
    const days = [];

    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }
    return days;
  };

  const subjectEntries = useMemo(() => Object.entries(subjects), [subjects]);

  return (
    <div className="dashboard-wrapper">
      {/* Header Section */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">
            Welcome back, <span className="name-accent">{user?.full_name?.split(' ')[0] || 'Learner'}</span>!
          </h1>
          <p className="dashboard-subtitle">Class {user?.class_grade || '10'} • CBSE • Let's make progress today</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-main">
        {/* Left Column - Stats & Study Queue */}
        <div className="dashboard-left">
          {/* Quick Stats - Large, Modern Cards */}
          <div className="premium-stats-container">
            {/* Streak Card - Hero */}
            <div className="stat-card-premium streak-card" style={{ background: 'linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%)' }}>
              <div className="stat-icon">🔥</div>
              <div className="stat-content">
                <p className="stat-label">Study Streak</p>
                <h2 className="stat-number">{progress?.streak_days || 0}</h2>
                <p className="stat-helper">days on fire</p>
              </div>
            </div>

            {/* Other Stats - Grid */}
            <div className="stat-cards-grid">
              <div className="stat-card-compact" style={{ background: 'linear-gradient(135deg, #4ECDC4 0%, #6FE7DD 100%)' }}>
                <p className="stat-label-small">Chapters</p>
                <h3>{stats?.booksAccessed || 0}</h3>
              </div>
              <div className="stat-card-compact" style={{ background: 'linear-gradient(135deg, #FFE66D 0%, #FFF5B4 100%)' }}>
                <p className="stat-label-small">Summaries</p>
                <h3>{stats?.totalSummaries || 0}</h3>
              </div>
              <div className="stat-card-compact" style={{ background: 'linear-gradient(135deg, #A8E6CF 0%, #C5F1E0 100%)' }}>
                <p className="stat-label-small">Quizzes</p>
                <h3>{stats?.totalQuizzes || 0}</h3>
              </div>
            </div>
          </div>

          {/* Revision Queue - Clean Cards */}
          <div className="study-section">
            <div className="section-header">
              <h3>Continue Learning</h3>
              <p>Pick up where you left off</p>
            </div>
            {(progress?.revision_queue || []).length ? (
              <div className="revision-stack">
                {progress?.revision_queue.slice(0, 4).map((item) => (
                  <button
                    key={`${item.subject}-${item.chapter}`}
                    type="button"
                    className="revision-item-btn"
                    onClick={() => navigate(`/subject/${item.subject}?class=${user?.class_grade || '10'}`)}
                  >
                    <div className="revision-info">
                      <h4>{item.chapter}</h4>
                      <p>{item.subject}</p>
                    </div>
                    <ChevronRight size={20} className="revision-arrow" />
                  </button>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <p>Start a chapter to build your personalized learning queue</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Calendar & Todo */}
        <div className="dashboard-right">
          {/* Compact Calendar */}
          <div className="calendar-widget">
            <div className="calendar-header">
              <h3>Your Schedule</h3>
              <div className="calendar-nav">
                <button
                  type="button"
                  onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1))}
                  className="calendar-btn"
                >
                  ←
                </button>
                <span className="calendar-month">{currentDate.toLocaleString('default', { month: 'short', year: 'numeric' })}</span>
                <button
                  type="button"
                  onClick={() => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1))}
                  className="calendar-btn"
                >
                  →
                </button>
              </div>
            </div>
            <div className="calendar-grid">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                <div key={day} className="calendar-day-header">{day}</div>
              ))}
              {generateCalendarDays().map((day, idx) => (
                <div key={idx} className={`calendar-day ${day === null ? 'empty' : day === new Date().getDate() ? 'today' : ''}`}>
                  {day}
                </div>
              ))}
            </div>
          </div>

          {/* Smart Todo List */}
          <div className="todo-widget">
            <h3 className="todo-title">This Week's Goals</h3>
            <div className="todo-input-container">
              <input
                type="text"
                value={newTodo}
                onChange={(e) => setNewTodo(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && addTodo()}
                placeholder="Add a goal..."
                className="todo-input"
              />
              <button type="button" onClick={addTodo} className="todo-add-btn">
                <Plus size={18} />
              </button>
            </div>
            <div className="todo-list">
              {todos.length ? (
                todos.map(todo => (
                  <div key={todo.id} className={`todo-item ${todo.completed ? 'completed' : ''}`}>
                    <button
                      type="button"
                      onClick={() => toggleTodo(todo.id)}
                      className="todo-checkbox"
                    >
                      <CheckCircle size={20} />
                    </button>
                    <span className="todo-text">{todo.text}</span>
                    <button
                      type="button"
                      onClick={() => deleteTodo(todo.id)}
                      className="todo-delete"
                    >
                      ✕
                    </button>
                  </div>
                ))
              ) : (
                <p className="empty-todo">Your week is clear! Add goals to get started.</p>
              )}
            </div>
            {todos.length > 0 && (
              <div className="todo-progress">
                <p>{todos.filter(t => t.completed).length} of {todos.length} complete</p>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${(todos.filter(t => t.completed).length / todos.length) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Weak Topics Section */}
      {(progress?.weak_topics || []).length > 0 && (
        <div className="focus-section">
          <div className="section-header">
            <h3>Topics to Focus On</h3>
            <p>Based on your recent quiz performance</p>
          </div>
          <div className="weak-topics-grid">
            {progress?.weak_topics.slice(0, 3).map((item) => (
              <div key={`${item.subject}-${item.chapter}`} className="focus-card">
                <div className="focus-badge">{item.score_percent}%</div>
                <h4>{item.chapter}</h4>
                <p>{item.subject}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Your Subjects Section */}
      <section className="subject-section">
        <div className="section-header">
          <h3>Your Subjects</h3>
          <p>Select a subject to explore chapters</p>
        </div>

        <div className="subject-dashboard-grid">
          {subjectEntries.map(([subject, chapters]) => {
            const meta = getSubjectMeta(subject);
            const Icon = meta.icon;
            return (
              <button
                key={subject}
                type="button"
                className="subject-dashboard-card"
                onClick={() => navigate(`/subject/${subject}?class=${user?.class_grade || '10'}`)}
              >
                <div className={`subject-card-top-strip ${meta.gradient}`} />
                <div className="subject-dashboard-head">
                  <span className={`subject-icon-box ${meta.gradient}`}>
                    <Icon size={24} />
                  </span>
                  <ChevronRight size={22} className="subject-card-arrow" />
                </div>
                <h3>{meta.label}</h3>
                <p className="subject-card-meta">
                  <span>{chapters.length} chapters</span>
                </p>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
