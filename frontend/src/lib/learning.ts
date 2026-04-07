import { Atom, BookOpen, Calculator, FlaskConical, Globe2, Landmark, Leaf, PenSquare } from 'lucide-react';
import { LucideIcon } from 'lucide-react';

export interface SubjectMeta {
  key: string;
  label: string;
  shortLabel: string;
  description: string;
  gradient: string;
  accent: string;
  icon: LucideIcon;
}

export const SUBJECT_META: Record<string, SubjectMeta> = {
  math: {
    key: 'math',
    label: 'Mathematics',
    shortLabel: 'Math',
    description: 'Algebra • Geometry • Mensuration',
    gradient: 'subject-gradient-math',
    accent: 'accent-math',
    icon: Calculator,
  },
  science: {
    key: 'science',
    label: 'Science',
    shortLabel: 'Science',
    description: 'Physics • Chemistry • Biology',
    gradient: 'subject-gradient-science',
    accent: 'accent-science',
    icon: FlaskConical,
  },
  history: {
    key: 'history',
    label: 'History',
    shortLabel: 'History',
    description: 'Events • Timelines • Movements',
    gradient: 'subject-gradient-history',
    accent: 'accent-history',
    icon: Landmark,
  },
  geography: {
    key: 'geography',
    label: 'Geography',
    shortLabel: 'Geography',
    description: 'Maps • Resources • Environment',
    gradient: 'subject-gradient-geography',
    accent: 'accent-geography',
    icon: Globe2,
  },
  civics: {
    key: 'civics',
    label: 'Civics',
    shortLabel: 'Civics',
    description: 'Democracy • Rights • Institutions',
    gradient: 'subject-gradient-civics',
    accent: 'accent-civics',
    icon: BookOpen,
  },
  economics: {
    key: 'economics',
    label: 'Economics',
    shortLabel: 'Economics',
    description: 'Development • Money • Markets',
    gradient: 'subject-gradient-economics',
    accent: 'accent-economics',
    icon: BookOpen,
  },
  english: {
    key: 'english',
    label: 'English',
    shortLabel: 'English',
    description: 'Reading • Writing • Literature',
    gradient: 'subject-gradient-english',
    accent: 'accent-english',
    icon: PenSquare,
  },
  physics: {
    key: 'physics',
    label: 'Physics',
    shortLabel: 'Physics',
    description: 'Motion • Energy • Laws',
    gradient: 'subject-gradient-science',
    accent: 'accent-science',
    icon: Atom,
  },
  chemistry: {
    key: 'chemistry',
    label: 'Chemistry',
    shortLabel: 'Chemistry',
    description: 'Matter • Reactions • Elements',
    gradient: 'subject-gradient-history',
    accent: 'accent-history',
    icon: FlaskConical,
  },
  biology: {
    key: 'biology',
    label: 'Biology',
    shortLabel: 'Biology',
    description: 'Life • Cells • Systems',
    gradient: 'subject-gradient-geography',
    accent: 'accent-geography',
    icon: Leaf,
  },
};

function toTitle(value: string) {
  return value
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getSubjectMeta(subject: string): SubjectMeta {
  return SUBJECT_META[subject] || {
    key: subject,
    label: toTitle(subject),
    shortLabel: toTitle(subject),
    description: 'CBSE chapter learning',
    gradient: 'subject-gradient-default',
    accent: 'accent-default',
    icon: BookOpen,
  };
}
