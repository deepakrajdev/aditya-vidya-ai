import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { AuthStore } from '../store/auth';

const CLASS_OPTIONS = ['4', '5', '6', '7', '8', '9', '10', '11', '12'];

interface QuizQuestion {
  question: string;
  options: string[];
  correct: string;
  explanation?: string;
}

interface ChapterOption {
  id: number;
  chapter_num: number;
  chapter: string;
}

interface SubjectMap {
  [subject: string]: ChapterOption[];
}

export default function Quiz() {
  const user = AuthStore((state) => state.user);
  const [params] = useSearchParams();
  const [topic, setTopic] = useState(params.get('topic') || '');
  const [classGrade, setClassGrade] = useState(params.get('class') || user?.class_grade || '10');
  const [subject, setSubject] = useState(params.get('subject') || '');
  const [subjects, setSubjects] = useState<SubjectMap>({});
  const [loading, setLoading] = useState(false);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [attemptSaved, setAttemptSaved] = useState(false);
  const [quizStartedAt, setQuizStartedAt] = useState<number | null>(null);

  useEffect(() => {
    if (user?.class_grade) setClassGrade(params.get('class') || user.class_grade);
  }, [user?.class_grade, params]);

  useEffect(() => {
    const load = async () => {
      const response = await api.get(`/library/books/${classGrade}`);
      const nextSubjects = response.data.subjects || {};
      setSubjects(nextSubjects);

      const requestedSubject = params.get('subject') || subject;
      if (requestedSubject && nextSubjects[requestedSubject]) {
        setSubject(requestedSubject);
      } else {
        const firstSubject = Object.keys(nextSubjects)[0] || '';
        setSubject(firstSubject);
      }
    };

    void load();
  }, [classGrade]);

  const subjectOptions = useMemo(() => Object.keys(subjects), [subjects]);
  const topicOptions = useMemo(() => (subject ? subjects[subject] || [] : []), [subject, subjects]);

  useEffect(() => {
    if (!subjectOptions.length) {
      setSubject('');
      setTopic('');
      return;
    }

    if (subject && !subjects[subject]) {
      setSubject(subjectOptions[0]);
      return;
    }

    const requestedTopic = params.get('topic') || topic;
    if (requestedTopic && topicOptions.some((item) => item.chapter === requestedTopic)) {
      setTopic(requestedTopic);
      return;
    }

    if (!topicOptions.some((item) => item.chapter === topic)) {
      setTopic(topicOptions[0]?.chapter || '');
    }
  }, [subject, subjectOptions, subjects, topicOptions, params]);

  const generateQuiz = async (event?: FormEvent) => {
    event?.preventDefault();
    if (!topic) {
      setError('Select a chapter first.');
      return;
    }
    setLoading(true);
    setError('');
    setSubmitted(false);
    setSelected({});
    setAttemptSaved(false);
    try {
      const response = await api.post('/tutor/quiz', {
        topic,
        class_grade: classGrade,
        subject,
        num_questions: 5,
      });
      setQuestions(response.data.questions || []);
      setQuizStartedAt(Date.now());
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Unable to generate a quiz right now.');
      setQuestions([]);
    } finally {
      setLoading(false);
    }
  };

  const score = questions.reduce((total, question, index) => total + (selected[index] === question.correct ? 1 : 0), 0);
  const answeredCount = useMemo(() => Object.keys(selected).length, [selected]);

  const submitAttempt = async () => {
    setSubmitted(true);
    if (attemptSaved || !questions.length) return;
    try {
      await api.post('/tutor/quiz/submit', {
        topic,
        class_grade: classGrade,
        subject,
        score,
        total_questions: questions.length,
        correct_answers: score,
        time_taken_seconds: quizStartedAt ? Math.max(1, Math.round((Date.now() - quizStartedAt) / 1000)) : 0,
        quiz_data: JSON.stringify(questions),
      });
      setAttemptSaved(true);
    } catch {
      // Keep quiz usable even if progress save fails.
    }
  };

  return (
    <div className="page-stack quiz-page">
      <section className="panel-card quiz-hero-card">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Quiz mode</p>
            <h2>Turn any chapter into a practice round</h2>
            <p className="panel-subtext">Keep quizzes short, clean, and chapter-specific so students can learn without feeling lost.</p>
          </div>
          <div className="quiz-score-rail">
            <div>
              <span>Questions</span>
              <strong>{questions.length || 5}</strong>
            </div>
            <div>
              <span>Answered</span>
              <strong>{answeredCount}</strong>
            </div>
            <div>
              <span>Score</span>
              <strong>{submitted ? `${score}/${questions.length}` : '--'}</strong>
            </div>
          </div>
        </div>

        <form className="quiz-builder polished-quiz-builder" onSubmit={generateQuiz}>
          <label>
            <span>Chapter</span>
            <select value={topic} onChange={(event) => setTopic(event.target.value)} required>
              {topicOptions.length ? (
                topicOptions.map((item) => (
                  <option key={item.id} value={item.chapter}>
                    Chapter {item.chapter_num}: {item.chapter}
                  </option>
                ))
              ) : (
                <option value="">No chapters available</option>
              )}
            </select>
          </label>
          <label>
            <span>Class</span>
            <select value={classGrade} onChange={(event) => setClassGrade(event.target.value)}>
              {CLASS_OPTIONS.map((grade) => <option key={grade} value={grade}>Class {grade}</option>)}
            </select>
          </label>
          <label>
            <span>Subject</span>
            <select value={subject} onChange={(event) => setSubject(event.target.value)}>
              {subjectOptions.length ? (
                subjectOptions.map((item) => <option key={item} value={item}>{item.charAt(0).toUpperCase() + item.slice(1)}</option>)
              ) : (
                <option value="">No subjects available</option>
              )}
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={loading || !topic || !subject}>
            {loading ? 'Generating...' : 'Generate quiz'}
          </button>
        </form>

        <div className="quiz-topic-row">
          <span className="subject-pill">Class {classGrade}</span>
          <span className="subject-pill soft-pill">{subject}</span>
          <span className="subject-pill soft-pill">{topic}</span>
        </div>

        {error ? <div className="form-error">{error}</div> : null}
      </section>

      {questions.length > 0 ? (
        <section className="panel-card quiz-session-card">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Question set</p>
              <h3>{topic}</h3>
            </div>
            {submitted ? <div className="score-badge">Score: {score}/{questions.length}</div> : null}
          </div>

          <div className="quiz-list enhanced-quiz-list">
            {questions.map((question, index) => (
              <article key={`${question.question}-${index}`} className="quiz-card polished-quiz-card">
                <div className="quiz-card-top">
                  <span className="class-badge">Q{index + 1}</span>
                  <strong>{question.question}</strong>
                </div>
                <div className="options-list">
                  {question.options.map((option) => {
                    const optionKey = option.trim().charAt(0);
                    const isChosen = selected[index] === optionKey;
                    const isCorrect = question.correct === optionKey;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => !submitted && setSelected((current) => ({ ...current, [index]: optionKey }))}
                        className={`option-button${isChosen ? ' chosen' : ''}${submitted && isCorrect ? ' correct' : ''}`}
                      >
                        {option}
                      </button>
                    );
                  })}
                </div>
                {submitted && question.explanation ? <p className="quiz-explanation">{question.explanation}</p> : null}
              </article>
            ))}
          </div>

          <div className="quiz-actions">
            <button className="secondary-button" type="button" onClick={() => void generateQuiz()} disabled={loading}>New quiz</button>
            <button className="primary-button" type="button" onClick={() => void submitAttempt()} disabled={submitted || answeredCount === 0}>Submit answers</button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
