import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { AuthStore } from '../store/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const CLASS_OPTIONS = ['4', '5', '6', '7', '8', '9', '10', '11', '12'];
const ALL_CHAPTERS = '__all__';

type TutorMode = 'chat' | 'summary' | 'explain';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface TutorSection {
  label: string;
  body: string;
}

interface SubjectMap {
  [subject: string]: Array<{ id: number; chapter_num: number; chapter: string }>;
}

interface ChapterContextNote {
  title: string;
  note: string;
}

interface ChapterContext {
  summary_text?: string;
  topics_covered?: string[];
  subtopic_notes?: ChapterContextNote[];
}

interface SourceCard {
  subject: string;
  class_grade: string;
  chapter: string;
  page?: number | null;
  snippet: string;
  source_type: string;
}

const modeMeta: Record<TutorMode, { title: string; description: string; endpoint: string }> = {
  chat: {
    title: 'Ask your tutor',
    description: 'Have a calm back-and-forth conversation about a chapter, doubt, or homework question.',
    endpoint: '/tutor/chat',
  },
  summary: {
    title: 'Build a quick revision summary',
    description: 'Turn a chapter into clean revision notes with key ideas and exam focus.',
    endpoint: '/tutor/summarize',
  },
  explain: {
    title: 'Understand the concept simply',
    description: 'Break a tough idea into easy language with examples that actually help.',
    endpoint: '/tutor/explain',
  },
};

async function streamTutorResponse(
  token: string,
  endpoint: string,
  payload: Record<string, unknown>,
  onChunk: (chunk: string) => void,
) {
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
    // Add line breaks before key section labels
    .replace(/\b(Definition|Formula|Example|Note|Key point|Concept|Answer|Why it matters|Board-style question|Step-by-step solution|Simple everyday example)\s*-\s*/gi, '\n\n$1: ')
    .replace(/\b(Definition|Formula|Example|Note|Key point|Concept|Answer|Why it matters|Board-style question|Step-by-step solution|Simple everyday example)\s*[:]\s*/gi, '\n\n$1: ')
    // Ensure proper spacing between sentences
    .replace(/([.!?])([A-Za-z])/g, '$1  $2')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/([:;])([A-Za-z])/g, '$1  $2')
    .replace(/(\d+)\.([A-Za-z])/g, '$1.  $2')
    .replace(/\r/g, '')
    // Normalize multiple line breaks but preserve paragraph structure
    .replace(/\n{4,}/g, '\n\n')
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

    if (!active) {
      active = { label: 'Response', body: line };
    } else {
      active.body = active.body ? `${active.body}\n${line}` : line;
    }
  }

  if (active) sections.push(active);
  return sections;
}

function buildPromptChips(mode: TutorMode, topic: string, subject: string) {
  if (mode === 'summary') {
    return [
      topic || 'Make a revision sheet for this chapter',
      `What should I revise first from this ${subject} chapter?`,
      'Give me the most important exam points only',
    ];
  }

  if (mode === 'explain') {
    return [
      topic ? `Teach me the big idea of ${topic}` : 'Teach me the big idea simply',
      topic ? `Show one solved example from ${topic}` : 'Show one solved example',
      topic ? `What mistake should I avoid in ${topic}?` : 'What mistake should I avoid?',
    ];
  }

  return [
    topic ? `Ask about ${topic}` : 'Why is this chapter important?',
    'Give me a step-by-step answer',
    'Test my understanding first',
  ];
}

function decodePrompt(value: string | null) {
  return value ? decodeURIComponent(value) : '';
}

function isGenericTopicLabel(value: string) {
  return ['core idea', 'key concept', 'main idea', 'daily-life connection', 'important terms', 'revision focus'].includes(value.trim().toLowerCase());
}

export default function Chat() {
  const user = AuthStore((state) => state.user);
  const token = AuthStore((state) => state.token);
  const [params] = useSearchParams();

  const initialMode = ((params.get('mode') as TutorMode) || 'chat');
  const initialTopic = params.get('topic') || '';
  const initialPrompt = decodePrompt(params.get('prompt'));
  const initialChapter = params.get('chapter') || (isGenericTopicLabel(initialTopic) ? '' : initialTopic);

  const [mode, setMode] = useState<TutorMode>(initialMode);
  const [classGrade, setClassGrade] = useState(params.get('class') || user?.class_grade || '10');
  const [subjects, setSubjects] = useState<SubjectMap>({});
  const [subject, setSubject] = useState(params.get('subject') || 'science');
  const [chapterScope, setChapterScope] = useState(initialChapter || ALL_CHAPTERS);
  const [input, setInput] = useState(initialPrompt || initialTopic);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Ask me a doubt from your chapter and I will explain it clearly.',
    },
  ]);
  const [resultText, setResultText] = useState('');
  const [resultPrompt, setResultPrompt] = useState('');
  const [error, setError] = useState('');
  const [chapterContext, setChapterContext] = useState<ChapterContext | null>(null);
  const [sourceCards, setSourceCards] = useState<SourceCard[]>([]);
  const chapterTitle = chapterScope !== ALL_CHAPTERS ? chapterScope : '';

  useEffect(() => {
    if (user?.class_grade) setClassGrade(params.get('class') || user.class_grade);
  }, [user?.class_grade, params]);

  useEffect(() => {
    const loadSubjects = async () => {
      const response = await api.get(`/library/books/${classGrade}`);
      const nextSubjects = response.data.subjects || {};
      setSubjects(nextSubjects);
      if (!nextSubjects[subject]) {
        const firstSubject = Object.keys(nextSubjects)[0];
        if (firstSubject) setSubject(firstSubject);
      }
    };

    void loadSubjects();
  }, [classGrade, subject]);

  const subjectOptions = useMemo(() => Object.keys(subjects), [subjects]);
  const chapterOptions = useMemo(() => (subject ? subjects[subject] || [] : []), [subject, subjects]);

  useEffect(() => {
    if (!chapterOptions.length) {
      setChapterScope(ALL_CHAPTERS);
      return;
    }

    const requestedChapter = params.get('chapter');
    const hasRequestedChapter = requestedChapter
      ? chapterOptions.some((item) => item.chapter.toLowerCase() === requestedChapter.toLowerCase())
      : false;

    if (hasRequestedChapter) {
      setChapterScope(requestedChapter || ALL_CHAPTERS);
      return;
    }

    if (chapterScope !== ALL_CHAPTERS) {
      const stillExists = chapterOptions.some((item) => item.chapter.toLowerCase() === chapterScope.toLowerCase());
      if (!stillExists) {
        setChapterScope(ALL_CHAPTERS);
      }
    }
  }, [chapterOptions, chapterScope, params]);

  useEffect(() => {
    const loadChapterContext = async () => {
      if (!chapterTitle || chapterScope === ALL_CHAPTERS) {
        setChapterContext(null);
        return;
      }

      const subjectChapters = subjects[subject] || [];
      const matched = subjectChapters.find((item) => item.chapter.toLowerCase() === chapterTitle.toLowerCase())
        || Object.values(subjects).flat().find((item) => item.chapter.toLowerCase() === chapterTitle.toLowerCase());

      if (!matched) {
        setChapterContext(null);
        return;
      }

      const response = await api.get(`/library/chapter/${matched.id}`);
      setChapterContext({
        summary_text: cleanResponseText(response.data.summary_text || ''),
        topics_covered: (response.data.topics_covered || []).map((item: string) => cleanResponseText(item)),
        subtopic_notes: (response.data.subtopic_notes || [])
          .map((item: ChapterContextNote) => ({
            title: cleanResponseText(item.title),
            note: cleanResponseText(item.note),
          }))
          .filter((item: ChapterContextNote) => item.title && item.note)
          .slice(0, 3),
      });
    };

    void loadChapterContext();
  }, [chapterScope, chapterTitle, classGrade, subject, subjects]);

  useEffect(() => {
    const nextMode = ((params.get('mode') as TutorMode) || 'chat');
    const nextTopic = params.get('topic') || '';
    const nextPrompt = decodePrompt(params.get('prompt'));
    const nextChapter = params.get('chapter') || '';
    setMode(nextMode);
    if (params.get('subject')) setSubject(params.get('subject') || 'science');
    setChapterScope(nextChapter || ALL_CHAPTERS);
    if (nextMode === 'summary') {
      setInput(nextPrompt || nextTopic || '');
    } else if (nextMode === 'explain') {
      const safeTopic = isGenericTopicLabel(nextTopic) ? nextChapter : nextTopic;
      setInput(nextPrompt || (safeTopic ? `Explain ${safeTopic} in simple words with an example.` : ''));
    } else {
      setInput(nextPrompt || nextTopic || '');
    }
  }, [params]);

  const placeholder = useMemo(() => {
    if (mode === 'summary') {
      return chapterTitle
        ? `Create a clean summary for ${chapterTitle}`
        : `Ask for a subject-wide revision summary across all ${subject} chapters`;
    }
    if (mode === 'explain') {
      return chapterTitle
        ? `Ask for a simple explanation from ${chapterTitle}`
        : `Ask for a simple explanation from any ${subject} chapter`;
    }
    return chapterTitle
      ? `Ask a question only from ${chapterTitle}`
      : `Ask a question across all ${subject} chapters`;
  }, [chapterTitle, mode, subject]);

  const quickPrompts = useMemo(() => {
    const rawTopic = params.get('topic') || '';
    const topicLabel = chapterTitle || (isGenericTopicLabel(rawTopic) ? '' : rawTopic);
    if (mode === 'explain' && chapterTitle) {
      return [
        `Explain ${chapterTitle} in simple words with an example`,
        `What is the main idea of ${chapterTitle}?`,
        `Show me a step-by-step explanation from ${chapterTitle}`,
      ];
    }
    if (mode === 'summary' && !chapterTitle) {
      return [
        `Give me a full revision summary for all ${subject} chapters in Class ${classGrade}`,
        `What should I revise first from ${subject} this week?`,
        `Which ${subject} chapters are most important for exams?`,
      ];
    }
    if (mode === 'chat' && !chapterTitle) {
      return [
        `Ask me questions from any ${subject} chapter in Class ${classGrade}`,
        `Which ${subject} chapter should I revise first?`,
        `Test me across all ${subject} chapters`,
      ];
    }
    return buildPromptChips(mode, topicLabel, subject);
  }, [mode, params, subject, chapterTitle, classGrade]);
  const sections = useMemo(() => extractSections(resultText), [resultText]);
  const contextTitle = chapterTitle || 'All chapters';
  const contextTopics = useMemo(() => (chapterContext?.topics_covered || []).slice(0, 4), [chapterContext]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim() || !token || loading) return;

    const currentInput = input.trim();
    setError('');
    setLoading(true);

    if (mode === 'chat') {
      const userMessage: ChatMessage = { id: String(Date.now()), role: 'user', content: currentInput };
      const assistantId = String(Date.now() + 1);
      setMessages((current) => [...current, userMessage, { id: assistantId, role: 'assistant', content: '' }]);
      setInput('');

      try {
        await streamTutorResponse(token, modeMeta.chat.endpoint, {
          message: currentInput,
          class_grade: classGrade,
          subject,
          chapter: chapterTitle || undefined,
          history: messages.slice(-6).map((message) => ({ role: message.role, content: message.content })),
        }, (chunk) => {
          setMessages((current) => current.map((message) => (
            message.id === assistantId
              ? { ...message, content: cleanResponseText(`${message.content}${chunk}`) }
              : message
          )));
        });
      } catch (streamError: any) {
        setMessages((current) => current.map((message) => (
          message.id === assistantId
            ? { ...message, content: streamError?.message || 'Tutor request failed. Check whether the backend and Ollama are running.' }
            : message
        )));
      } finally {
        setLoading(false);
      }
      return;
    }

    setResultText('');
    setResultPrompt(currentInput);
    setInput('');
    setSourceCards([]);

    const payload = mode === 'summary'
      ? { chapter: currentInput, class_grade: classGrade, subject, chapter_scope: chapterTitle || undefined }
      : { concept: currentInput, class_grade: classGrade, subject, chapter: chapterTitle || undefined, simple_mode: true };

    try {
      try {
        const sourceResponse = await api.post('/tutor/sources', {
          query: currentInput,
          class_grade: classGrade,
          subject,
          chapter: chapterTitle || undefined,
        });
        setSourceCards(sourceResponse.data.sources || []);
      } catch {
        setSourceCards([]);
      }
      await streamTutorResponse(token, modeMeta[mode].endpoint, payload, (chunk) => {
        setResultText((current) => cleanResponseText(`${current}${chunk}`));
      });
    } catch (streamError: any) {
      setError(streamError?.message || 'Tutor request failed. Check whether the backend and Ollama are running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack tutor-page">
      <section className="panel-card tutor-hero-card smoother-tutor-card">
        <div className="tutor-workspace-head">
          <div>
            <p className="eyebrow">Tutor workspace</p>
            <h2>Learn with a clean flow that stays inside the chapter</h2>
          </div>
          <div className="context-pill compact-context-pill">
            <span>Class {classGrade}</span>
            <strong>{subject}</strong>
            <small>{contextTitle}</small>
          </div>
        </div>

        <div className="tutor-toolbar">
          <label>
            <span>Class</span>
            <select value={classGrade} onChange={(event) => setClassGrade(event.target.value)}>
              {CLASS_OPTIONS.map((grade) => <option key={grade} value={grade}>Class {grade}</option>)}
            </select>
          </label>
          <label>
            <span>Subject</span>
            <select value={subject} onChange={(event) => setSubject(event.target.value)}>
              {subjectOptions.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)}
            </select>
          </label>
          <label>
            <span>Chapter</span>
            <select value={chapterScope} onChange={(event) => setChapterScope(event.target.value)}>
              <option value={ALL_CHAPTERS}>All chapters</option>
              {chapterOptions.map((item) => (
                <option key={item.id} value={item.chapter}>
                  {`Chapter ${item.chapter_num}: ${item.chapter}`}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mode-card-grid smoother-mode-grid">
          {(['chat', 'summary', 'explain'] as TutorMode[]).map((item) => (
            <button
              key={item}
              type="button"
              className={`mode-card softer-mode-card${mode === item ? ' active' : ''}`}
              onClick={() => {
                setMode(item);
                setError('');
              }}
            >
              <p className="eyebrow">{item}</p>
              <h3>{modeMeta[item].title}</h3>
              <p>{modeMeta[item].description}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="tutor-layout smoother-tutor-layout">
        <article className="panel-card tutor-input-card">
          <div className="panel-head compact-panel-head">
            <div>
              <p className="eyebrow">Current mode</p>
              <h3>{modeMeta[mode].title}</h3>
            </div>
          </div>

          <div className="prompt-chip-row cleaner-prompt-row">
            {quickPrompts.map((prompt) => (
              <button key={prompt} type="button" className="prompt-chip cleaner-prompt-chip" onClick={() => setInput(prompt)}>
                {prompt}
              </button>
            ))}
          </div>

          <form className="composer tutor-composer" onSubmit={handleSubmit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={placeholder}
              rows={mode === 'chat' ? 5 : 6}
            />
            <button className="primary-button" type="submit" disabled={loading || !input.trim()}>
              {loading ? 'Working...' : mode === 'chat' ? 'Send to tutor' : mode === 'summary' ? 'Create summary' : 'Explain clearly'}
            </button>
          </form>

          {error ? <div className="form-error">{error}</div> : null}

          {chapterContext ? (
            <section className="tutor-context-notes">
              <div className="panel-head compact-panel-head">
                <div>
                  <p className="eyebrow">Chapter notes</p>
                  <h3>{chapterTitle || 'This chapter'}</h3>
                </div>
              </div>
              {chapterContext.summary_text ? <p className="tutor-context-summary">{chapterContext.summary_text}</p> : null}
              {contextTopics.length ? (
                <div className="tutor-context-topic-row">
                  {contextTopics.map((topic) => <span key={topic}>{topic}</span>)}
                </div>
              ) : null}
              {chapterContext.subtopic_notes?.length ? (
                <div className="tutor-context-note-list">
                  {chapterContext.subtopic_notes.map((item) => (
                    <article key={item.title} className="tutor-context-note-card">
                      <strong>{item.title}</strong>
                      <p>{item.note}</p>
                      <button type="button" className="topic-tutor-link" onClick={() => setInput(`Explain ${item.title} from ${chapterTitle} in simple words with one example.`)}>
                        Use this note
                      </button>
                    </article>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null}
        </article>

        {mode === 'chat' ? (
          <article className="panel-card tutor-output-card">
            <div className="panel-head compact-panel-head">
              <div>
                <p className="eyebrow">Conversation</p>
                <h3>Interactive tutor chat</h3>
              </div>
            </div>
            <div className="message-stack enhanced-message-stack cleaner-message-stack">
              {messages.map((message) => (
                <article key={message.id} className={`message-card ${message.role}`}>
                  <span>{message.role === 'user' ? 'You' : 'VidyaAI'}</span>
                  <p>{message.content || (loading && message.role === 'assistant' ? 'Thinking...' : '')}</p>
                </article>
              ))}
            </div>
          </article>
        ) : (
          <article className="panel-card tutor-output-card">
            <div className="panel-head compact-panel-head">
              <div>
                <p className="eyebrow">Learning result</p>
                <h3>{mode === 'summary' ? 'Revision-ready chapter notes' : 'Simple concept breakdown'}</h3>
              </div>
              {resultPrompt ? <span className="subject-pill">{resultPrompt}</span> : null}
            </div>

            {!resultText && !loading ? (
              <div className="empty-state-card">
                <h4>{mode === 'summary' ? 'Ask for a chapter summary' : 'Ask for a concept explanation'}</h4>
                <p>
                  {mode === 'summary'
                    ? 'You will get a clean revision layout instead of a raw text block.'
                    : 'You will get a simplified explanation that stays focused on the actual topic.'}
                </p>
              </div>
            ) : null}

            {sections.length > 0 ? (
              <div className="response-section-stack">
                {sections.map((section, index) => (
                  <section key={`${section.label}-${index}`} className="response-section-card">
                    <p className="eyebrow">{section.label}</p>
                    <p>{section.body}</p>
                  </section>
                ))}
              </div>
            ) : resultText ? (
              <div className="response-section-card response-single-card">
                <p>{resultText}</p>
              </div>
            ) : null}

            {sourceCards.length ? (
              <section className="source-card-section">
                <div className="panel-head compact-panel-head">
                  <div>
                    <p className="eyebrow">NCERT support</p>
                    <h4>These textbook parts were used</h4>
                  </div>
                </div>
                <div className="source-card-stack">
                  {sourceCards.map((card, index) => (
                    <article key={`${card.chapter}-${card.page || index}`} className="source-card">
                      <div className="source-card-top">
                        <span className="subject-pill soft-pill">{card.subject}</span>
                        <span className="subject-pill soft-pill">{card.chapter}</span>
                        {card.page ? <span className="subject-pill soft-pill">Page {card.page}</span> : null}
                      </div>
                      <p>{card.snippet}</p>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {loading ? <div className="streaming-note">Building your learning output...</div> : null}
          </article>
        )}
      </section>
    </div>
  );
}
