import { ChevronRight } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { getSubjectMeta } from '../lib/learning';
import { AuthStore } from '../store/auth';

interface Chapter {
  id: number;
  chapter_num: number;
  chapter: string;
  is_ingested?: boolean;
}

interface SubjectMap {
  [subject: string]: Chapter[];
}

export default function Subject() {
  const { subjectId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const user = AuthStore((state) => state.user);
  const [subjects, setSubjects] = useState<SubjectMap>({});
  const [loading, setLoading] = useState(true);
  const activeClass = searchParams.get('class') || user?.class_grade || '10';

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const response = await api.get(`/library/books/${activeClass}`);
      setSubjects(response.data.subjects || {});
      setLoading(false);
    };

    void load();
  }, [activeClass]);

  const meta = getSubjectMeta(subjectId);
  const Icon = meta.icon;
  const chapters = useMemo(() => subjects[subjectId] || [], [subjectId, subjects]);
  const ingestedCount = useMemo(() => chapters.filter((chapter: any) => chapter.is_ingested).length, [chapters]);

  if (loading) {
    return <div className="panel-card">Loading subject...</div>;
  }

  return (
    <div className="reference-page-stack">
      <section className={`subject-hero-card ${meta.gradient}`}>
        <div>
          <Link to="/library" className="subject-back-link">Back to library</Link>
          <div className="subject-hero-content">
            <span className="subject-icon-box light-icon-box">
              <Icon size={28} />
            </span>
            <div>
              <h1>{meta.label}</h1>
              <p>Class {activeClass} · CBSE Curriculum</p>
            </div>
          </div>
        </div>
        <div className="subject-stat-stack">
          <span>{chapters.length} Chapters</span>
          <span>{ingestedCount ? `${ingestedCount} NCERT-backed chapters` : 'Chapter notes ready'}</span>
          <span>Open a chapter to read notes, summary, quiz, and tutor help</span>
        </div>
      </section>

      <section className="reference-section-head">
        <h2>Chapters</h2>
        <p>Open a chapter to see notes, subtopics, summary, quiz, and tutor support.</p>
      </section>

      <section className="chapter-reference-grid">
        {chapters.map((chapter) => (
          <button key={chapter.id} type="button" className="chapter-reference-card" onClick={() => navigate(`/chapter/${chapter.id}`)}>
            <div className="chapter-reference-head">
              <span className={`chapter-number-badge ${meta.gradient}`}>{chapter.chapter_num}</span>
              <div>
                <h3>{chapter.chapter}</h3>
                <p>Notes, subtopics, summary, quiz, and AI help inside</p>
              </div>
              <ChevronRight size={20} className="chapter-chevron" />
            </div>
          </button>
        ))}
      </section>
    </div>
  );
}
