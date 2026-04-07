import { Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { getSubjectMeta } from '../lib/learning';
import { AuthStore } from '../store/auth';

const CLASS_OPTIONS = ['4', '5', '6', '7', '8', '9', '10', '11', '12'];

interface Chapter {
  id: number;
  chapter_num: number;
  chapter: string;
}

interface SubjectMap {
  [subject: string]: Chapter[];
}

export default function Library() {
  const navigate = useNavigate();
  const user = AuthStore((state) => state.user);
  const [selectedClass, setSelectedClass] = useState(user?.class_grade || '10');
  const [subjects, setSubjects] = useState<SubjectMap>({});
  const [search, setSearch] = useState('');

  useEffect(() => {
    const load = async () => {
      const response = await api.get(`/library/books/${selectedClass}`);
      setSubjects(response.data.subjects || {});
    };
    void load();
  }, [selectedClass]);

  const entries = useMemo(() => Object.entries(subjects), [subjects]);
  const filtered = useMemo(() => entries.filter(([subject, chapters]) => {
    const query = search.trim().toLowerCase();
    if (!query) return true;
    return subject.toLowerCase().includes(query) || chapters.some((chapter) => chapter.chapter.toLowerCase().includes(query));
  }), [entries, search]);

  return (
    <div className="reference-page-stack">
      <section className="library-reference-header smoother-header-card">
        <div>
          <h1>Browse by subject</h1>
          <p>Use search and filters to quickly find the subject you want.</p>
        </div>
        <label className="class-select-block">
          <span>Class</span>
          <select value={selectedClass} onChange={(event) => setSelectedClass(event.target.value)}>
            {CLASS_OPTIONS.map((grade) => <option key={grade} value={grade}>Class {grade}</option>)}
          </select>
        </label>
      </section>

      <label className="library-search-bar">
        <Search size={18} />
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search subjects or chapters" />
      </label>

      <section className="subject-dashboard-grid">
        {filtered.map(([subject, chapters]) => {
          const meta = getSubjectMeta(subject);
          const Icon = meta.icon;
          const estimatedHours = Math.ceil(chapters.length * 1.5);
          return (
            <button key={subject} type="button" className="subject-dashboard-card" onClick={() => navigate(`/subject/${subject}?class=${selectedClass}`)}>
              <div className={`subject-card-top-strip ${meta.gradient}`} />
              <div className="subject-dashboard-head">
                <div>
                  <h3>{meta.label}</h3>
                  <p className="subject-card-meta">{meta.description}</p>
                </div>
                <span className="subject-card-arrow">→</span>
              </div>
              <div className="subject-preview-list">
                {chapters.slice(0, 2).map((chapter) => <span key={chapter.id}>Ch. {chapter.chapter_num}: {chapter.chapter}</span>)}
                {chapters.length > 2 && <span style={{ opacity: 0.6 }}>+ {chapters.length - 2} more</span>}
              </div>
              <div className="subject-card-footer">
                <span>
                  <strong>{chapters.length}</strong>
                  <small>Chapters</small>
                </span>
                <span>
                  <strong>~{estimatedHours}h</strong>
                  <small>Estimated</small>
                </span>
              </div>
            </button>
          );
        })}
      </section>
    </div>
  );
}
