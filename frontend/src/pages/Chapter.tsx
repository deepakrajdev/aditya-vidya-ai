import { BookOpen, BrainCircuit, HelpCircle, Lightbulb, ScrollText, Sparkles } from 'lucide-react';
import { FormEvent, Fragment, ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import api from '../api/client';
import { getSubjectMeta } from '../lib/learning';
import { AuthStore } from '../store/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type ChapterTool = 'summary' | 'explain' | 'quiz';

interface QuizQuestion {
  question: string;
  options: string[];
  correct: string;
  explanation?: string;
}

interface SubtopicNote {
  title: string;
  note: string;
  ask_ai_prompt: string;
}

interface ChapterDetail {
  id: number;
  class_grade: string;
  subject: string;
  chapter: string;
  chapter_num: number;
  overview: string;
  summary_text?: string;
  content_excerpt?: string;
  topics_covered?: string[];
  key_points?: string[];
  why_it_matters?: string;
  study_focus?: string;
  subtopic_notes?: SubtopicNote[];
  source_type?: string;
  is_ingested?: boolean;
}

interface TutorSection {
  label: string;
  body: string;
}

interface SourceCard {
  subject: string;
  class_grade: string;
  chapter: string;
  page?: number | null;
  snippet: string;
  source_type: string;
}

function cleanResponseText(text: string) {
  return text
    .replace(/[\u2011\u2013\u2014]/g, '-')
    .replace(/[\u2018\u2019]/g, "'")
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/\u00A0/g, ' ')
    .replace(/\u211d/g, 'real numbers')
    .replace(/\u211a/g, 'rational numbers')
    .replace(/\u2124/g, 'integers')
    .replace(/\u03c0/g, 'pi')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^\s*[-*]\s+/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\r/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function extractSections(text: string): TutorSection[] {
  const cleaned = cleanResponseText(text);
  if (!cleaned) return [];
  const lines = cleaned.split('\n').map((line) => line.trim()).filter(Boolean);
  const sections: TutorSection[] = [];
  let active: TutorSection | null = null;

  for (const line of lines) {
    const match = line.match(/^([A-Za-z][A-Za-z /&]{2,40}):\s*(.*)$/);
    if (match) {
      if (active) sections.push(active);
      active = { label: match[1], body: match[2] || '' };
      continue;
    }

    if (!active) active = { label: 'Response', body: line };
    else active.body = active.body ? `${active.body}\n${line}` : line;
  }

  if (active) sections.push(active);
  return sections;
}

function renderSectionContent(label: string, body: string): ReactNode {
  const sectionType = label.toLowerCase().replace(/\s+/g, '-');
  let className = 'section-definition';
  
  if (sectionType.includes('formula')) className = 'section-formula';
  else if (sectionType.includes('example')) className = 'section-example';
  else if (sectionType.includes('why') || sectionType.includes('matter')) className = 'section-why-it-matters';
  else if (sectionType.includes('key') || sectionType.includes('point')) className = 'section-key-point';
  else if (sectionType.includes('core') || sectionType.includes('concept')) className = 'section-concept';
  else if (sectionType.includes('note')) className = 'section-note';

  return (
    <article className={className}>
      <span className="section-label">{label}</span>
      <div className="section-body">
        {body.split('\n').filter(Boolean).map((para, idx) => (
          para.trim() && <p key={idx}>{para.trim()}</p>
        ))}
      </div>
    </article>
  );
}

function isGenericTitle(title: string) {
  const normalized = cleanResponseText(title).toLowerCase();
  return [
    'core idea',
    'key concept',
    'main idea',
    'daily-life connection',
    'important terms',
    'revision focus',
    'introduction to chapter',
    'chapter overview',
  ].includes(normalized);
}

function splitParagraphs(...blocks: string[]) {
  return blocks
    .flatMap((block) => cleanResponseText(block).split(/\n\n+/))
    .map((piece) => cleanResponseText(piece))
    .filter((piece, index, array) => piece.length > 60 && array.indexOf(piece) === index);
}

function buildReadingParagraphs(chapter: ChapterDetail) {
  const paragraphs = splitParagraphs(chapter.summary_text || '', chapter.content_excerpt || '', chapter.overview || '');
  return paragraphs.length ? paragraphs.slice(0, 4) : [cleanResponseText(chapter.overview || '')].filter(Boolean);
}

function buildStudyNotesFromChapter(chapter: ChapterDetail): SubtopicNote[] {
  const paragraphs = buildReadingParagraphs(chapter);
  const topicTitles = (chapter.topics_covered || [])
    .map((topic) => cleanResponseText(topic))
    .filter((topic) => topic && !isGenericTitle(topic));
  const keyPoints = (chapter.key_points || [])
    .map((point) => cleanResponseText(point))
    .filter((point) => point.length > 18);

  const titles = [...topicTitles, ...keyPoints.map((point) => point.split(/[.:;-]/)[0].trim())]
    .map((title) => cleanResponseText(title))
    .filter((title, index, array) => title && !isGenericTitle(title) && array.indexOf(title) === index)
    .slice(0, 6);

  const notes = titles.map((title, index) => ({
    title,
    note: keyPoints[index] || paragraphs[index % Math.max(paragraphs.length, 1)] || `${chapter.chapter} should be revised with the NCERT examples and textbook questions.`,
    ask_ai_prompt: `Explain ${title} from the chapter ${chapter.chapter} for Class ${chapter.class_grade} in simple words with one clear example.`,
  }));

  if (notes.length) return notes;

  return paragraphs.slice(0, 4).map((paragraph, index) => ({
    title: index === 0 ? `${chapter.chapter}: main idea` : `${chapter.chapter}: note ${index + 1}`,
    note: paragraph,
    ask_ai_prompt: `Explain this part of the chapter ${chapter.chapter} for Class ${chapter.class_grade}: ${paragraph}`,
  }));
}

async function streamTutorResponse(token: string, endpoint: string, payload: Record<string, unknown>, onChunk: (chunk: string) => void) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    throw new Error((await response.text()) || 'Request failed');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const event of events) {
      const line = event.trim();
      if (!line.startsWith('data: ')) continue;
      const data = line.slice(6);
      if (data === '[DONE]') return;
      const parsed = JSON.parse(data) as { chunk?: string };
      if (parsed.chunk) onChunk(parsed.chunk);
    }
  }
}

export default function Chapter() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const token = AuthStore((state) => state.token);
  const [chapter, setChapter] = useState<ChapterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTool, setActiveTool] = useState<ChapterTool>('summary');
  const [toolLoading, setToolLoading] = useState(false);
  const [toolError, setToolError] = useState('');
  const [summaryText, setSummaryText] = useState('');
  const [explainPrompt, setExplainPrompt] = useState('');
  const [explainText, setExplainText] = useState('');
  const [sourceCards, setSourceCards] = useState<SourceCard[]>([]);
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [attemptSaved, setAttemptSaved] = useState(false);
  const [quizStartedAt, setQuizStartedAt] = useState<number | null>(null);
  const [keyPointsLoading, setKeyPointsLoading] = useState(false);
  const studioRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const loadChapter = async () => {
      setLoading(true);
      const response = await api.get(`/library/chapter/${bookId}`);
      const nextChapter = {
        ...response.data,
        overview: cleanResponseText(response.data.overview || ''),
        summary_text: cleanResponseText(response.data.summary_text || ''),
        content_excerpt: cleanResponseText(response.data.content_excerpt || ''),
        topics_covered: (response.data.topics_covered || []).map((item: string) => cleanResponseText(item)),
        key_points: (response.data.key_points || []).map((item: string) => cleanResponseText(item)),
        subtopic_notes: (response.data.subtopic_notes || []).map((item: SubtopicNote) => ({
          ...item,
          title: cleanResponseText(item.title),
          note: cleanResponseText(item.note),
        })),
      };
      setChapter(nextChapter);
      setExplainPrompt(`Explain ${nextChapter.chapter} in simple words with one example from the chapter.`);
      setLoading(false);

      // Auto-generate key points if they don't exist and token is available
      if ((!nextChapter.key_points || nextChapter.key_points.length === 0) && token) {
        void generateKeyPoints(nextChapter);
      }
    };

    if (bookId) void loadChapter();
  }, [bookId]);

  const summarySections = useMemo(() => extractSections(summaryText), [summaryText]);
  const explainSections = useMemo(() => extractSections(explainText), [explainText]);
  const quizScore = quizQuestions.reduce((total, question, index) => total + (selectedAnswers[index] === question.correct ? 1 : 0), 0);

  const readingParagraphs = useMemo(() => (chapter ? buildReadingParagraphs(chapter) : []), [chapter]);
  const chapterTopics = useMemo(() => (chapter?.topics_covered || []).filter((item) => item && !isGenericTitle(item)).slice(0, 8), [chapter]);
  const subtopicNotes = useMemo(() => {
    if (!chapter) return [];
    const normalizedNotes = (chapter.subtopic_notes || [])
      .map((item) => ({
        ...item,
        title: cleanResponseText(item.title),
        note: cleanResponseText(item.note),
      }))
      .filter((item) => item.title && item.note && !isGenericTitle(item.title));

    return normalizedNotes.length ? normalizedNotes : buildStudyNotesFromChapter(chapter);
  }, [chapter]);

  const explainSuggestions = useMemo(() => {
    if (!chapter) return [];
    const notes = subtopicNotes.slice(0, 3).map((item) => `Teach me ${item.title} from ${chapter.chapter} with one clear example.`);
    if (notes.length) return notes;
    return [`Teach me the big idea of ${chapter.chapter}.`, `Show one solved example from ${chapter.chapter}.`];
  }, [chapter, subtopicNotes]);

  const scrollToStudio = () => {
    studioRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (loading || !chapter) {
    return <div className="panel-card">Opening chapter...</div>;
  }

  const meta = getSubjectMeta(chapter.subject);
  const tutorQuery = new URLSearchParams({ class: chapter.class_grade, subject: chapter.subject, topic: chapter.chapter, chapter: chapter.chapter, mode: 'chat' }).toString();

  const generateSummary = async () => {
    if (!token || toolLoading) return;
    setToolLoading(true);
    setToolError('');
    setSummaryText('');
    setSourceCards([]);
    try {
      try {
        const sourceResponse = await api.post('/tutor/sources', {
          query: chapter.chapter,
          class_grade: chapter.class_grade,
          subject: chapter.subject,
        });
        setSourceCards(sourceResponse.data.sources || []);
      } catch {
        setSourceCards([]);
      }
      await streamTutorResponse(token, '/tutor/summarize', { chapter: chapter.chapter, class_grade: chapter.class_grade, subject: chapter.subject }, (chunk) => {
        setSummaryText((current) => cleanResponseText(`${current}${chunk}`));
      });
    } catch (err: any) {
      setToolError(err?.message || 'Unable to create the summary right now.');
    } finally {
      setToolLoading(false);
    }
  };

  const generateKeyPoints = async (chapterData?: ChapterDetail) => {
    const targetChapter = chapterData || chapter;
    if (!token || !targetChapter) return;
    setKeyPointsLoading(true);
    try {
      await streamTutorResponse(token, '/tutor/explain', 
        { 
          concept: `Key learning points and main ideas from "${targetChapter.chapter}"`,
          class_grade: targetChapter.class_grade,
          subject: targetChapter.subject,
          chapter: targetChapter.chapter,
          simple_mode: true 
        }, 
        () => {}  // We don't need to stream individual chunks for this
      );
      // After generation, reload the chapter to get the updated key points from DB
      if (bookId) {
        const response = await api.get(`/library/chapter/${bookId}`);
        const updatedChapter = {
          ...response.data,
          overview: cleanResponseText(response.data.overview || ''),
          summary_text: cleanResponseText(response.data.summary_text || ''),
          content_excerpt: cleanResponseText(response.data.content_excerpt || ''),
          topics_covered: (response.data.topics_covered || []).map((item: string) => cleanResponseText(item)),
          key_points: (response.data.key_points || []).map((item: string) => cleanResponseText(item)),
          subtopic_notes: (response.data.subtopic_notes || []).map((item: SubtopicNote) => ({
            ...item,
            title: cleanResponseText(item.title),
            note: cleanResponseText(item.note),
          })),
        };
        setChapter(updatedChapter);
      }
    } catch (err) {
      console.error('Failed to generate key points:', err);
    } finally {
      setKeyPointsLoading(false);
    }
  };

  const handleExplain = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!token || toolLoading || !explainPrompt.trim()) return;
    setToolLoading(true);
    setToolError('');
    setExplainText('');
    setSourceCards([]);
    try {
      try {
        const sourceResponse = await api.post('/tutor/sources', {
          query: explainPrompt.trim(),
          class_grade: chapter.class_grade,
          subject: chapter.subject,
        });
        setSourceCards(sourceResponse.data.sources || []);
      } catch {
        setSourceCards([]);
      }
      await streamTutorResponse(token, '/tutor/explain', { concept: explainPrompt.trim(), class_grade: chapter.class_grade, subject: chapter.subject, chapter: chapter.chapter, simple_mode: true }, (chunk) => {
        setExplainText((current) => cleanResponseText(`${current}${chunk}`));
      });
    } catch (err: any) {
      setToolError(err?.message || 'Unable to explain this chapter right now.');
    } finally {
      setToolLoading(false);
    }
  };

  const generateQuiz = async () => {
    if (toolLoading) return;
    setToolLoading(true);
    setToolError('');
    setQuizSubmitted(false);
    setSelectedAnswers({});
    setAttemptSaved(false);
    try {
      const response = await api.post('/tutor/quiz', { topic: chapter.chapter, class_grade: chapter.class_grade, subject: chapter.subject, num_questions: 5 });
      setQuizQuestions(response.data.questions || []);
      setQuizStartedAt(Date.now());
    } catch (err: any) {
      setToolError(err?.response?.data?.detail || 'Unable to create the quiz right now.');
    } finally {
      setToolLoading(false);
    }
  };

  const activateTool = async (tool: ChapterTool) => {
    setActiveTool(tool);
    scrollToStudio();

    if (tool === 'summary' && !summaryText && !toolLoading) {
      void generateSummary();
    }

    if (tool === 'quiz' && quizQuestions.length === 0 && !toolLoading) {
      void generateQuiz();
    }
  };

  const submitQuizAttempt = async () => {
    setQuizSubmitted(true);
    if (attemptSaved || !quizQuestions.length) return;
    try {
      await api.post('/tutor/quiz/submit', {
        topic: chapter.chapter,
        class_grade: chapter.class_grade,
        subject: chapter.subject,
        score: quizScore,
        total_questions: quizQuestions.length,
        correct_answers: quizScore,
        time_taken_seconds: quizStartedAt ? Math.max(1, Math.round((Date.now() - quizStartedAt) / 1000)) : 0,
        quiz_data: JSON.stringify(quizQuestions),
      });
      setAttemptSaved(true);
    } catch {
      // Keep quiz flow usable even if save fails.
    }
  };

  const openSubtopicTutor = (item: SubtopicNote) => {
    const params = new URLSearchParams({
      class: chapter.class_grade,
      subject: chapter.subject,
      topic: item.title,
      chapter: chapter.chapter,
      prompt: item.ask_ai_prompt,
      mode: 'explain',
    }).toString();
    navigate(`/chat?${params}`);
  };

  const chapterTools = [
    {
      title: 'Chapter Summary',
      text: 'Turn this chapter into quick revision notes.',
      icon: ScrollText,
      accent: 'accent-geography',
      active: activeTool === 'summary',
      onClick: () => void activateTool('summary'),
    },
    {
      title: 'Explain Clearly',
      text: 'Break one idea into easy language with an example.',
      icon: Lightbulb,
      accent: 'accent-history',
      active: activeTool === 'explain',
      onClick: () => {
        setActiveTool('explain');
        scrollToStudio();
      },
    },
    {
      title: 'Practice Quiz',
      text: 'Answer quick questions from this chapter.',
      icon: HelpCircle,
      accent: 'accent-english',
      active: activeTool === 'quiz',
      onClick: () => void activateTool('quiz'),
    },
    {
      title: 'Ask AI Tutor',
      text: 'Open the full tutor for doubts, homework, or examples.',
      icon: BrainCircuit,
      accent: 'accent-math',
      active: false,
      onClick: () => navigate(`/chat?${tutorQuery}`),
    },
  ];

  return (
    <div className="reference-page-stack chapter-reading-page">
      <section className="panel-card chapter-reader-hero">
        <div className="chapter-reader-copy">
          <Link to={`/subject/${chapter.subject}?class=${chapter.class_grade}`} className="subject-back-link">Back to {meta.label}</Link>
          <p className="eyebrow">Chapter {chapter.chapter_num}</p>
          <h1>{chapter.chapter}</h1>
          <p className="chapter-reader-lead">{readingParagraphs[0] || chapter.overview}</p>
          <div className="chapter-reader-chip-row">
            <span className="student-topbar-chip">Class {chapter.class_grade}</span>
            <span className="student-outline-chip">{meta.label}</span>
            <span className="student-outline-chip">{chapter.is_ingested ? 'NCERT notes ready' : 'Saved chapter notes'}</span>
          </div>
        </div>

        <aside className="chapter-reader-rail">
          <div className="chapter-rail-card">
            <p className="eyebrow">Topics covered</p>
            <div className="chapter-topic-chip-list">
              {chapterTopics.length ? chapterTopics.map((topic) => <span key={topic}>{topic}</span>) : <span>{chapter.chapter}</span>}
            </div>
          </div>
        </aside>
      </section>

      <section className="chapter-reading-layout">
        <div className="chapter-main-column">
          <article className="panel-card chapter-reading-card">
            <p className="eyebrow">Chapter notes</p>
            <h2>What this chapter teaches</h2>
            <div className="chapter-reading-body">
              {readingParagraphs.map((paragraph, index) => <p key={`${paragraph.slice(0, 24)}-${index}`}>{paragraph}</p>)}
            </div>
          </article>

          <section className="panel-card chapter-key-points-card">
            <div className="chapter-key-points-head">
              <div>
                <p className="eyebrow">Key learning points</p>
                <h3>What you must understand from this chapter</h3>
              </div>
              {keyPointsLoading ? (
                <span className="student-outline-chip">Generating...</span>
              ) : chapter.key_points && chapter.key_points.length > 0 ? (
                <span className="student-outline-chip">{chapter.key_points.length} points</span>
              ) : null}
            </div>
            {keyPointsLoading ? (
              <div className="empty-state-card">
                <h4>Creating key points for you...</h4>
                <p>VidyaAI is analyzing this chapter to extract the most important ideas.</p>
              </div>
            ) : chapter.key_points && chapter.key_points.length > 0 ? (
              <div className="chapter-key-points-grid">
                {chapter.key_points.slice(0, 5).map((point, index) => (
                  <article key={`${point.slice(0, 30)}-${index}`} className="key-point-card">
                    <div className="key-point-head">
                      <span className="key-point-number">{index + 1}</span>
                      <span className={`topic-cluster-icon ${meta.gradient}`}><Sparkles size={16} /></span>
                    </div>
                    <p className="key-point-text">{point}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state-card">
                <h4>No key points yet</h4>
                <p>Generate key points to see the most important ideas from this chapter.</p>
                <button type="button" className="primary-button" onClick={() => void generateKeyPoints()} disabled={keyPointsLoading}>
                  {keyPointsLoading ? 'Generating...' : 'Generate Key Points'}
                </button>
              </div>
            )}
          </section>

          <section className="panel-card chapter-inline-notes">
            <div className="chapter-inline-notes-head">
              <div>
                <p className="eyebrow">Quick notes</p>
                <h3>Read the important ideas from this chapter</h3>
              </div>
              {chapterTopics.length ? <span className="student-outline-chip">{chapterTopics.length} topics</span> : null}
            </div>
            <div className="chapter-note-story-grid compact-note-grid">
              {subtopicNotes.map((item) => (
                <article key={item.title} className="panel-card chapter-note-story-card">
                  <div className="chapter-note-story-head">
                    <span className={`topic-cluster-icon ${meta.gradient}`}><BookOpen size={17} /></span>
                    <div>
                      <h3>{item.title}</h3>
                    </div>
                  </div>
                  <p className="chapter-note-story-body">{item.note}</p>
                  <button type="button" className="secondary-button chapter-note-ask" onClick={() => openSubtopicTutor(item)}>
                    Ask AI about this note
                  </button>
                </article>
              ))}
            </div>
          </section>
        </div>

        <aside className="chapter-tools-rail">
          <div className="panel-card chapter-tools-card">
            <p className="eyebrow">Study tools</p>
            <h3>Use the chapter your way</h3>
            <div className="chapter-tool-button-stack">
              {chapterTools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <button
                    key={tool.title}
                    type="button"
                    className={`chapter-tool-button${tool.active ? ' active' : ''}`}
                    onClick={tool.onClick}
                  >
                    <span className={`feature-icon-wrap ${tool.accent}`}><Icon size={18} /></span>
                    <div>
                      <strong>{tool.title}</strong>
                      <p>{tool.text}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </aside>
      </section>

      <section ref={studioRef} className="chapter-studio-card panel-card">
        <div className="panel-head compact-panel-head">
          <div>
            <p className="eyebrow">Chapter tools</p>
            <h3>{activeTool === 'summary' ? 'Revision summary' : activeTool === 'explain' ? 'Explain one part clearly' : 'Chapter quiz'}</h3>
          </div>
        </div>
        <div className="studio-tab-row">
          <button type="button" className={`tool-tab ${activeTool === 'summary' ? 'active' : ''}`} onClick={() => setActiveTool('summary')}>Summary</button>
          <button type="button" className={`tool-tab ${activeTool === 'explain' ? 'active' : ''}`} onClick={() => setActiveTool('explain')}>Explain</button>
          <button type="button" className={`tool-tab ${activeTool === 'quiz' ? 'active' : ''}`} onClick={() => setActiveTool('quiz')}>Quiz</button>
        </div>
        {toolError ? <div className="form-error">{toolError}</div> : null}

        {activeTool === 'summary' ? (
          <div className="study-tool-panel">
            <div className="study-tool-top">
              <p>Generate a cleaner revision sheet when you want a shorter exam-focused version.</p>
              <button type="button" className="primary-button" onClick={() => void generateSummary()} disabled={toolLoading}>{toolLoading ? 'Creating...' : 'Generate Summary'}</button>
            </div>
            {toolLoading ? (
              <div className="empty-state-card"><h4>Creating your summary...</h4><p>VidyaAI is generating a clean, exam-focused summary just for you.</p></div>
            ) : summarySections.length > 0 ? (
              <div className="response-section-stack">
                {summarySections.map((section, index) => <Fragment key={index}>{renderSectionContent(section.label, section.body)}</Fragment>)}
              </div>
            ) : chapter.summary_text ? (
              <div className="response-section-stack">
                {buildReadingParagraphs(chapter).map((paragraph, index) => (
                  <article key={`${paragraph.slice(0, 24)}-${index}`} className="section-definition">
                    <div className="section-body">
                      <p>{paragraph}</p>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state-card"><h4>Summary will appear here</h4><p>Generate a clean revision layout for this chapter.</p></div>
            )}
            {sourceCards.length ? <div className="source-card-stack">{sourceCards.map((card, index) => <article key={`${card.chapter}-${card.page || index}`} className="source-card"><div className="source-card-top"><span className="subject-pill soft-pill">{card.subject}</span><span className="subject-pill soft-pill">{card.chapter}</span>{card.page ? <span className="subject-pill soft-pill">Page {card.page}</span> : null}</div><p>{card.snippet}</p></article>)}</div> : null}
          </div>
        ) : null}

        {activeTool === 'explain' ? (
          <div className="study-tool-panel">
            <div className="prompt-chip-row cleaner-prompt-row">
              {explainSuggestions.map((prompt) => (
                <button key={prompt} type="button" className="prompt-chip cleaner-prompt-chip" onClick={() => setExplainPrompt(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
            <form className="composer tutor-composer" onSubmit={(event) => void handleExplain(event)}>
              <textarea value={explainPrompt} onChange={(event) => setExplainPrompt(event.target.value)} rows={4} />
              <button className="primary-button" type="submit" disabled={toolLoading || !explainPrompt.trim()}>{toolLoading ? 'Explaining...' : 'Explain Clearly'}</button>
            </form>
            {toolLoading ? (
              <div className="empty-state-card"><h4>Getting a clear explanation...</h4><p>VidyaAI is crafting an easy-to-understand explanation for you.</p></div>
            ) : explainSections.length > 0 ? (
              <div className="response-section-stack">{explainSections.map((section, index) => <Fragment key={index}>{renderSectionContent(section.label, section.body)}</Fragment>)}</div>
            ) : (
              <div className="empty-state-card"><h4>Explanation will appear here</h4><p>Ask for one idea, one example, or one confusing part from the chapter.</p></div>
            )}
            {sourceCards.length ? <div className="source-card-stack">{sourceCards.map((card, index) => <article key={`${card.chapter}-${card.page || index}`} className="source-card"><div className="source-card-top"><span className="subject-pill soft-pill">{card.subject}</span><span className="subject-pill soft-pill">{card.chapter}</span>{card.page ? <span className="subject-pill soft-pill">Page {card.page}</span> : null}</div><p>{card.snippet}</p></article>)}</div> : null}
          </div>
        ) : null}

        {activeTool === 'quiz' ? (
          <div className="study-tool-panel">
            <div className="study-tool-top">
              <p>Take a chapter quiz without leaving the page.</p>
              <button type="button" className="primary-button" onClick={() => void generateQuiz()} disabled={toolLoading}>{toolLoading ? 'Creating...' : quizQuestions.length ? 'New Quiz' : 'Start Quiz'}</button>
            </div>
            {toolLoading ? (
              <div className="empty-state-card"><h4>Preparing your quiz...</h4><p>VidyaAI is generating personalized questions for you.</p></div>
            ) : quizQuestions.length > 0 ? <div className="quiz-list enhanced-quiz-list compact-quiz-list">{quizQuestions.map((question, index) => <article key={`${question.question}-${index}`} className="quiz-card polished-quiz-card"><div className="quiz-card-top"><span className="class-badge">Q{index + 1}</span><strong>{question.question}</strong></div><div className="options-list">{question.options.map((option) => { const optionKey = option.trim().charAt(0); const isChosen = selectedAnswers[index] === optionKey; const isCorrect = question.correct === optionKey; return <button key={option} type="button" onClick={() => !quizSubmitted && setSelectedAnswers((current) => ({ ...current, [index]: optionKey }))} className={`option-button${isChosen ? ' chosen' : ''}${quizSubmitted && isCorrect ? ' correct' : ''}`}>{option}</button>; })}</div>{quizSubmitted && question.explanation ? <p className="quiz-explanation">{question.explanation}</p> : null}</article>)}<div className="quiz-actions"><div className="score-badge">{quizSubmitted ? `Score: ${quizScore}/${quizQuestions.length}` : 'Answer and submit when ready'}</div><button className="primary-button" type="button" onClick={() => void submitQuizAttempt()} disabled={quizSubmitted || Object.keys(selectedAnswers).length === 0}>Submit Answers</button></div></div> : <div className="empty-state-card"><h4>Quiz will appear here</h4><p>Generate a quick quiz for this chapter.</p></div>}
          </div>
        ) : null}
      </section>
    </div>
  );
}
