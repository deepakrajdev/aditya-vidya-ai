"""VidyaAI database models and helpers."""

from datetime import datetime
import json
import os
import re
from typing import Optional

from sqlalchemy import inspect, text
from sqlmodel import Field, Session, SQLModel, create_engine, select

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vidya_ai.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

CATALOG = {
    "4": {
        "math": [
            "Numbers and Place Value",
            "Addition and Subtraction",
            "Multiplication",
            "Division",
            "Fractions",
            "Patterns",
            "Geometry Around Us",
            "Measurement",
            "Time",
            "Money",
            "Data Handling",
        ],
        "science": [
            "Living and Non-Living Things",
            "Plants Around Us",
            "Animals and Their Habitats",
            "Food and Digestion Basics",
            "Water",
            "Air and Weather",
            "Travel and Maps",
            "Safety and First Aid",
            "Our Environment",
            "The Earth and Sky",
        ],
        "english": [
            "Reading and Understanding Stories",
            "Poems and Rhythm",
            "Sentence Building",
            "Vocabulary and Word Meaning",
            "Listening and Speaking",
            "Writing Short Paragraphs",
        ],
    },
    "5": {
        "math": [
            "Large Numbers",
            "The Four Operations",
            "Multiples and Factors",
            "Fractions",
            "Decimals",
            "Measurement",
            "Perimeter and Area",
            "Time",
            "Money",
            "Data Handling",
            "Patterns and Symmetry",
        ],
        "science": [
            "Plant Life",
            "Animal Life",
            "Food and Health",
            "Skeletal and Muscular System",
            "Water and Its Uses",
            "Air and Pollution",
            "Weather and Climate",
            "Natural Resources",
            "Force and Energy",
            "Our Earth and Space",
        ],
        "english": [
            "Story Comprehension",
            "Poetry Appreciation",
            "Grammar in Use",
            "Word Building",
            "Conversation Skills",
            "Creative Writing",
        ],
    },
    "6": {
        "math": [
            "Knowing Our Numbers",
            "Whole Numbers",
            "Playing with Numbers",
            "Basic Geometrical Ideas",
            "Understanding Elementary Shapes",
            "Integers",
            "Fractions",
            "Decimals",
            "Data Handling",
            "Mensuration",
            "Algebra",
            "Ratio and Proportion",
            "Symmetry",
            "Practical Geometry",
        ],
        "science": [
            "Food: Where Does It Come From?",
            "Components of Food",
            "Fibre to Fabric",
            "Sorting Materials into Groups",
            "Separation of Substances",
            "Changes Around Us",
            "Getting to Know Plants",
            "Body Movements",
            "The Living Organisms and Their Surroundings",
            "Motion and Measurement of Distances",
            "Light, Shadows and Reflections",
            "Electricity and Circuits",
            "Fun with Magnets",
            "Water",
            "Air Around Us",
            "Garbage In, Garbage Out",
        ],
        "history": [
            "What, Where, How and When?",
            "On the Trail of the Earliest People",
            "From Gathering to Growing Food",
            "In the Earliest Cities",
            "What Books and Burials Tell Us",
            "Kingdoms, Kings and an Early Republic",
            "New Questions and Ideas",
            "Ashoka, the Emperor Who Gave Up War",
            "Vital Villages, Thriving Towns",
            "Traders, Kings and Pilgrims",
            "New Empires and Kingdoms",
            "Buildings, Paintings and Books",
        ],
        "geography": [
            "The Earth in the Solar System",
            "Globe: Latitudes and Longitudes",
            "Motions of the Earth",
            "Maps",
            "Major Domains of the Earth",
            "Our Country: India",
            "India: Climate, Vegetation and Wildlife",
        ],
        "civics": [
            "Understanding Diversity",
            "Diversity and Discrimination",
            "What is Government?",
            "Key Elements of a Democratic Government",
            "Panchayati Raj",
            "Rural Administration",
            "Urban Administration",
            "Rural Livelihoods",
            "Urban Livelihoods",
        ],
        "english": [
            "Who Did Patrick's Homework?",
            "How the Dog Found Himself a New Master!",
            "Taro's Reward",
            "An Indian-American Woman in Space",
            "A Different Kind of School",
            "Who I Am",
            "Fair Play",
            "A Game of Chance",
            "Desert Animals",
            "The Banyan Tree",
        ],
    },
    "7": {
        "math": [
            "Integers",
            "Fractions and Decimals",
            "Data Handling",
            "Simple Equations",
            "Lines and Angles",
            "The Triangle and Its Properties",
            "Congruence of Triangles",
            "Comparing Quantities",
            "Rational Numbers",
            "Practical Geometry",
            "Perimeter and Area",
            "Algebraic Expressions",
            "Exponents and Powers",
            "Symmetry",
            "Visualising Solid Shapes",
        ],
        "science": [
            "Nutrition in Plants",
            "Nutrition in Animals",
            "Fibre to Fabric",
            "Heat",
            "Acids, Bases and Salts",
            "Physical and Chemical Changes",
            "Weather, Climate and Adaptations",
            "Winds, Storms and Cyclones",
            "Soil",
            "Respiration in Organisms",
            "Transportation in Animals and Plants",
            "Reproduction in Plants",
            "Motion and Time",
            "Electric Current and Its Effects",
            "Light",
            "Water: A Precious Resource",
            "Forests: Our Lifeline",
            "Wastewater Story",
        ],
        "history": [
            "Tracing Changes Through a Thousand Years",
            "New Kings and Kingdoms",
            "The Delhi Sultans",
            "The Mughal Empire",
            "Rulers and Buildings",
            "Towns, Traders and Craftspersons",
            "Tribes, Nomads and Settled Communities",
            "Devotional Paths to the Divine",
            "The Making of Regional Cultures",
            "Eighteenth-Century Political Formations",
        ],
        "geography": [
            "Environment",
            "Inside Our Earth",
            "Our Changing Earth",
            "Air",
            "Water",
            "Natural Vegetation and Wildlife",
            "Human Environment: Settlement, Transport and Communication",
            "Human Environment Interactions",
        ],
        "civics": [
            "On Equality",
            "Role of the Government in Health",
            "How the State Government Works",
            "Growing up as Boys and Girls",
            "Women Change the World",
            "Understanding Media",
            "Markets Around Us",
            "A Shirt in the Market",
            "Struggles for Equality",
        ],
        "english": [
            "Three Questions",
            "A Gift of Chappals",
            "Gopal and the Hilsa Fish",
            "The Ashes That Made Trees Bloom",
            "Quality",
            "Expert Detectives",
            "The Invention of Vita-Wonk",
            "Fire: Friend and Foe",
            "A Bicycle in Good Repair",
            "The Story of Cricket",
        ],
    },
    "8": {
        "math": [
            "Rational Numbers",
            "Linear Equations in One Variable",
            "Understanding Quadrilaterals",
            "Practical Geometry",
            "Data Handling",
            "Squares and Square Roots",
            "Cubes and Cube Roots",
            "Comparing Quantities",
            "Algebraic Expressions and Identities",
            "Visualising Solid Shapes",
            "Mensuration",
            "Exponents and Powers",
            "Direct and Inverse Proportions",
            "Factorisation",
            "Introduction to Graphs",
            "Playing with Numbers",
        ],
        "science": [
            "Crop Production and Management",
            "Microorganisms: Friend and Foe",
            "Synthetic Fibres and Plastics",
            "Materials: Metals and Non-Metals",
            "Coal and Petroleum",
            "Combustion and Flame",
            "Conservation of Plants and Animals",
            "Cell: Structure and Functions",
            "Reproduction in Animals",
            "Reaching the Age of Adolescence",
            "Force and Pressure",
            "Friction",
            "Sound",
            "Chemical Effects of Electric Current",
            "Some Natural Phenomena",
            "Light",
            "Stars and the Solar System",
            "Pollution of Air and Water",
        ],
        "history": [
            "How, When and Where",
            "From Trade to Territory",
            "Ruling the Countryside",
            "Tribals, Dikus and the Vision of a Golden Age",
            "When People Rebel",
            "Civilising the Native, Educating the Nation",
            "Women, Caste and Reform",
            "The Making of the National Movement",
            "India After Independence",
        ],
        "geography": [
            "Resources",
            "Land, Soil, Water, Natural Vegetation and Wildlife Resources",
            "Mineral and Power Resources",
            "Agriculture",
            "Industries",
            "Human Resources",
        ],
        "civics": [
            "The Indian Constitution",
            "Understanding Secularism",
            "Why Do We Need a Parliament?",
            "Understanding Laws",
            "Judiciary",
            "Understanding Our Criminal Justice System",
            "Understanding Marginalisation",
            "Confronting Marginalisation",
            "Public Facilities",
            "Law and Social Justice",
        ],
        "english": [
            "The Best Christmas Present in the World",
            "The Tsunami",
            "Glimpses of the Past",
            "Bepin Choudhury's Lapse of Memory",
            "The Summit Within",
            "This is Jody's Fawn",
            "A Visit to Cambridge",
            "A Short Monsoon Diary",
            "The Great Stone Face",
        ],
    },
    "9": {
        "math": [
            "Number Systems",
            "Polynomials",
            "Coordinate Geometry",
            "Linear Equations in Two Variables",
            "Introduction to Euclid's Geometry",
            "Lines and Angles",
            "Triangles",
            "Quadrilaterals",
            "Areas of Parallelograms and Triangles",
            "Circles",
            "Constructions",
            "Heron's Formula",
            "Surface Areas and Volumes",
            "Statistics",
            "Probability",
        ],
        "science": [
            "Matter in Our Surroundings",
            "Is Matter Around Us Pure?",
            "Atoms and Molecules",
            "Structure of the Atom",
            "The Fundamental Unit of Life",
            "Tissues",
            "Diversity in Living Organisms",
            "Motion",
            "Force and Laws of Motion",
            "Gravitation",
            "Work and Energy",
            "Sound",
            "Why Do We Fall Ill?",
            "Natural Resources",
            "Improvement in Food Resources",
        ],
        "history": [
            "The French Revolution",
            "Socialism in Europe and the Russian Revolution",
            "Nazism and the Rise of Hitler",
            "Forest Society and Colonialism",
            "Pastoralists in the Modern World",
        ],
        "geography": [
            "India: Size and Location",
            "Physical Features of India",
            "Drainage",
            "Climate",
            "Natural Vegetation and Wildlife",
            "Population",
        ],
        "civics": [
            "What is Democracy? Why Democracy?",
            "Constitutional Design",
            "Electoral Politics",
            "Working of Institutions",
            "Democratic Rights",
        ],
        "economics": [
            "The Story of Village Palampur",
            "People as Resource",
            "Poverty as a Challenge",
            "Food Security in India",
        ],
        "english": [
            "The Fun They Had",
            "The Sound of Music",
            "The Little Girl",
            "A Truly Beautiful Mind",
            "The Snake and the Mirror",
            "My Childhood",
            "Packing",
            "Reach for the Top",
            "The Bond of Love",
            "Kathmandu",
            "If I Were You",
        ],
    },
    "10": {
        "math": [
            "Real Numbers",
            "Polynomials",
            "Pair of Linear Equations in Two Variables",
            "Quadratic Equations",
            "Arithmetic Progressions",
            "Triangles",
            "Coordinate Geometry",
            "Introduction to Trigonometry",
            "Some Applications of Trigonometry",
            "Circles",
            "Constructions",
            "Areas Related to Circles",
            "Surface Areas and Volumes",
            "Statistics",
            "Probability",
        ],
        "science": [
            "Chemical Reactions and Equations",
            "Acids, Bases and Salts",
            "Metals and Non-metals",
            "Carbon and its Compounds",
            "Periodic Classification of Elements",
            "Life Processes",
            "Control and Coordination",
            "How do Organisms Reproduce",
            "Heredity and Evolution",
            "Light Reflection and Refraction",
            "The Human Eye and the Colourful World",
            "Electricity",
            "Magnetic Effects of Electric Current",
            "Sources of Energy",
            "Our Environment",
            "Sustainable Management of Natural Resources",
        ],
        "history": [
            "The Rise of Nationalism in Europe",
            "Nationalism in India",
            "The Making of a Global World",
            "The Age of Industrialisation",
            "Print Culture and the Modern World",
        ],
        "geography": [
            "Resources and Development",
            "Forest and Wildlife Resources",
            "Water Resources",
            "Agriculture",
            "Minerals and Energy Resources",
            "Manufacturing Industries",
            "Lifelines of National Economy",
        ],
        "civics": [
            "Power Sharing",
            "Federalism",
            "Democracy and Diversity",
            "Gender, Religion and Caste",
            "Popular Struggles and Movements",
            "Political Parties",
            "Outcomes of Democracy",
            "Challenges to Democracy",
        ],
        "economics": [
            "Development",
            "Sectors of the Indian Economy",
            "Money and Credit",
            "Globalisation and the Indian Economy",
            "Consumer Rights",
        ],
        "english": [
            "A Letter to God",
            "Nelson Mandela: Long Walk to Freedom",
            "Two Stories about Flying",
            "From the Diary of Anne Frank",
            "Glimpses of India",
            "Mijbil the Otter",
            "Madam Rides the Bus",
            "The Sermon at Benares",
            "The Proposal",
        ],
    },
    "11": {
        "physics": [
            "Physical World",
            "Units and Measurements",
            "Motion in a Straight Line",
            "Laws of Motion",
            "Work, Energy and Power",
            "System of Particles and Rotational Motion",
            "Gravitation",
            "Thermodynamics",
            "Oscillations",
            "Waves",
        ],
        "chemistry": [
            "Some Basic Concepts of Chemistry",
            "Structure of Atom",
            "Classification of Elements and Periodicity",
            "Chemical Bonding and Molecular Structure",
            "Thermodynamics",
            "Equilibrium",
            "Redox Reactions",
            "Organic Chemistry - Basic Principles",
        ],
        "math": [
            "Sets",
            "Relations and Functions",
            "Trigonometric Functions",
            "Complex Numbers and Quadratic Equations",
            "Sequences and Series",
            "Straight Lines",
            "Conic Sections",
            "Limits and Derivatives",
            "Statistics",
            "Probability",
        ],
        "biology": [
            "The Living World",
            "Biological Classification",
            "Plant Kingdom",
            "Animal Kingdom",
            "Morphology of Flowering Plants",
            "Cell: The Unit of Life",
            "Biomolecules",
            "Cell Cycle and Cell Division",
            "Photosynthesis in Higher Plants",
            "Human Physiology Overview",
        ],
        "english": [
            "The Portrait of a Lady",
            "We're Not Afraid to Die",
            "Discovering Tut",
            "Landscape of the Soul",
            "The Ailing Planet",
        ],
    },
    "12": {
        "physics": [
            "Electric Charges and Fields",
            "Electrostatic Potential and Capacitance",
            "Current Electricity",
            "Ray Optics and Optical Instruments",
            "Semiconductor Electronics",
        ],
        "chemistry": [
            "Solutions",
            "Electrochemistry",
            "Chemical Kinetics",
            "d- and f-Block Elements",
            "Biomolecules",
            "Haloalkanes and Haloarenes",
            "Alcohols, Phenols and Ethers",
            "Aldehydes, Ketones and Carboxylic Acids",
        ],
        "math": [
            "Relations and Functions",
            "Matrices",
            "Determinants",
            "Application of Derivatives",
            "Probability",
            "Integrals",
            "Vector Algebra",
            "Three Dimensional Geometry",
            "Linear Programming",
        ],
        "biology": [
            "Reproduction in Organisms",
            "Sexual Reproduction in Flowering Plants",
            "Human Reproduction",
            "Molecular Basis of Inheritance",
            "Evolution",
            "Human Health and Disease",
            "Ecosystem",
            "Biodiversity and Conservation",
        ],
        "english": [
            "The Last Lesson",
            "Lost Spring",
            "Deep Water",
            "The Rattrap",
            "Indigo",
        ],
    },
}

SUBJECT_OVERVIEWS = {
    "math": "Focus on method, formula memory, and showing each step clearly.",
    "science": "Blend concept clarity with diagrams, definitions, and experiment-based reasoning.",
    "history": "Track timeline, cause and effect, and how events connect to each other.",
    "geography": "Revise maps, resource flows, and human-environment relationships.",
    "civics": "Think about systems, rights, institutions, and examples from public life.",
    "economics": "Stay sharp on definitions, real-life examples, and flow-based understanding.",
    "english": "Mix chapter understanding with writing quality, tone, and textual evidence.",
    "physics": "Focus on concepts, derivations, diagrams, and problem solving.",
    "chemistry": "Connect reactions, definitions, periodic trends, and everyday applications.",
    "biology": "Link processes, diagrams, terminology, and real-life examples to understand living systems clearly.",
}

ACTION_LABELS = {
    "math": ["Practice solved examples", "Revise formulas", "Try a quiz"],
    "science": ["Study diagrams", "Summarize concepts", "Ask why-based questions"],
    "history": ["Build timelines", "Revise causes and outcomes", "Practice long answers"],
    "geography": ["Revise maps", "Memorize key resources", "Practice data-based questions"],
    "civics": ["Understand institutions", "Use real examples", "Practice short notes"],
    "economics": ["Master definitions", "Connect to daily life", "Practice structured answers"],
    "english": ["Review themes", "Collect quotations", "Practice writing responses"],
    "physics": ["Revise formulas", "Understand derivations", "Try numericals"],
    "chemistry": ["Remember reactions", "Connect concepts", "Practice questions"],
    "biology": ["Revise diagrams", "Remember keywords", "Practice concept questions"],
}


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    full_name: str = Field(nullable=False)
    class_grade: str = Field(default="10", nullable=False)
    roll_number: Optional[str] = None
    school_name: Optional[str] = None
    hashed_password: Optional[str] = None
    google_id: Optional[str] = Field(unique=True, nullable=True, index=True)
    plan_type: str = Field(default="free")
    subscription_active: bool = Field(default=True)
    subscription_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = Field(default=True)


class Book(SQLModel, table=True):
    __tablename__ = "books"

    id: Optional[int] = Field(default=None, primary_key=True)
    class_grade: str = Field(index=True, nullable=False)
    subject: str = Field(index=True, nullable=False)
    chapter: str = Field(index=True, nullable=False)
    chapter_num: int = Field(nullable=False)
    total_pages: int = Field(default=0)
    chunks_count: int = Field(default=0)
    file_name: str = Field(nullable=False)
    source_url: Optional[str] = None
    source_type: str = Field(default="catalog")
    summary_text: Optional[str] = None
    topics_json: Optional[str] = None
    key_points_json: Optional[str] = None
    content_excerpt: Optional[str] = None
    is_ingested: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserAccessLog(SQLModel, table=True):
    __tablename__ = "user_access_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    book_id: int = Field(foreign_key="books.id", index=True, nullable=False)
    action: str
    tokens_used: int = Field(default=0)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)


class QuizAttempt(SQLModel, table=True):
    __tablename__ = "quiz_attempts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    book_id: int = Field(foreign_key="books.id", nullable=False)
    topic: str
    score: float
    total_questions: int
    correct_answers: int
    time_taken_seconds: int
    quiz_data: str = Field()
    attempted_at: datetime = Field(default_factory=datetime.utcnow)


def _ensure_sqlite_column(table: str, column_name: str, ddl: str) -> None:
    if "sqlite" not in DATABASE_URL:
        return
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns(table)}
    if column_name not in columns:
        with engine.begin() as connection:
            connection.execute(text(ddl))


def ensure_user_columns() -> None:
    _ensure_sqlite_column("users", "class_grade", "ALTER TABLE users ADD COLUMN class_grade VARCHAR NOT NULL DEFAULT '10'")
    _ensure_sqlite_column("users", "roll_number", "ALTER TABLE users ADD COLUMN roll_number VARCHAR")
    _ensure_sqlite_column("users", "school_name", "ALTER TABLE users ADD COLUMN school_name VARCHAR")


def ensure_book_columns() -> None:
    book_columns = {
        "source_type": "ALTER TABLE books ADD COLUMN source_type VARCHAR NOT NULL DEFAULT 'catalog'",
        "summary_text": "ALTER TABLE books ADD COLUMN summary_text TEXT",
        "topics_json": "ALTER TABLE books ADD COLUMN topics_json TEXT",
        "key_points_json": "ALTER TABLE books ADD COLUMN key_points_json TEXT",
        "content_excerpt": "ALTER TABLE books ADD COLUMN content_excerpt TEXT",
    }
    for column_name, ddl in book_columns.items():
        _ensure_sqlite_column("books", column_name, ddl)


def _title_case_subject(subject: str) -> str:
    labels = {
        "math": "Mathematics",
        "science": "Science",
        "history": "History",
        "geography": "Geography",
        "civics": "Civics",
        "economics": "Economics",
        "english": "English",
        "physics": "Physics",
        "chemistry": "Chemistry",
        "biology": "Biology",
    }
    return labels.get(subject, subject.replace("_", " ").title())


def _topic_words(chapter: str) -> list[str]:
    words = [word.strip() for word in chapter.replace(":", " ").replace(",", " ").split() if len(word.strip()) > 2]
    unique_words = []
    seen = set()
    for word in words:
        key = word.lower()
        if key not in seen:
            seen.add(key)
            unique_words.append(word)
    return unique_words


def build_catalog_assets(class_grade: str, subject: str, chapter: str) -> dict:
    subject_label = _title_case_subject(subject)
    keywords = _topic_words(chapter)
    chapter_focus = " ".join(keywords[:3]) if keywords else chapter

    topics = [
        f"Main idea of {chapter}",
        f"Important examples in {chapter_focus}",
        f"Key terms used in {subject_label.lower()}",
        "Revision questions and textbook practice",
    ]
    key_points = [
        f"Start with the central idea of {chapter}.",
        f"Connect this chapter with earlier Class {class_grade} {subject_label.lower()} concepts.",
        "Revise important terms, examples, and likely textbook questions.",
    ]

    summary_text = (
        f"{chapter} is a Class {class_grade} {subject_label} chapter in the VidyaAI curriculum map. "
        f"It focuses on building clear understanding, familiar examples, and exam-ready revision around {chapter.lower()}."
    )
    content_excerpt = (
        f"Use this chapter to understand {chapter.lower()}, notice the important ideas NCERT-style textbooks usually emphasize, "
        "and finish with short revision plus practice."
    )

    return {
        "summary_text": summary_text,
        "topics_json": json.dumps(topics),
        "key_points_json": json.dumps(key_points),
        "content_excerpt": content_excerpt,
    }


def seed_catalog() -> None:
    with Session(engine) as session:
        existing_books = {(book.class_grade, book.subject, book.chapter_num) for book in session.exec(select(Book)).all()}
        for class_grade, subjects in CATALOG.items():
            for subject, chapters in subjects.items():
                for index, chapter in enumerate(chapters, start=1):
                    key = (class_grade, subject, index)
                    if key in existing_books:
                        continue
                    session.add(
                        Book(
                            class_grade=class_grade,
                            subject=subject,
                            chapter=chapter,
                            chapter_num=index,
                            file_name=f"class{class_grade}_{subject}_chapter_{index:02d}.pdf",
                            is_ingested=False,
                            source_type="catalog",
                        )
                    )
        session.commit()


def ensure_catalog_content() -> None:
    with Session(engine) as session:
        books = session.exec(select(Book)).all()
        updated = False
        for book in books:
            if book.summary_text and book.topics_json and book.key_points_json and book.content_excerpt:
                continue
            assets = build_catalog_assets(book.class_grade, book.subject, book.chapter)
            if not book.summary_text:
                book.summary_text = assets["summary_text"]
            if not book.topics_json:
                book.topics_json = assets["topics_json"]
            if not book.key_points_json:
                book.key_points_json = assets["key_points_json"]
            if not book.content_excerpt:
                book.content_excerpt = assets["content_excerpt"]
            session.add(book)
            updated = True
        if updated:
            session.commit()


def cleanup_invalid_books() -> None:
    with Session(engine) as session:
        books = session.exec(select(Book)).all()
        removed = False
        for book in books:
            if book.chapter_num == 0 and not book.is_ingested:
                session.delete(book)
                removed = True
        if removed:
            session.commit()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    ensure_user_columns()
    ensure_book_columns()
    seed_catalog()
    ensure_catalog_content()
    cleanup_invalid_books()


def get_session():
    with Session(engine) as session:
        yield session


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def get_user_by_google_id(session: Session, google_id: str) -> Optional[User]:
    return session.exec(select(User).where(User.google_id == google_id)).first()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    return session.get(User, user_id)


def get_books_by_class(session: Session, class_grade: str):
    statement = select(Book).where(Book.class_grade == class_grade).order_by(Book.subject, Book.chapter_num)
    return session.exec(statement).all()


def get_book_by_id(session: Session, book_id: int) -> Optional[Book]:
    return session.get(Book, book_id)


def get_book_by_chapter(session: Session, class_grade: str, subject: str, chapter: str) -> Optional[Book]:
    statement = select(Book).where(
        Book.class_grade == class_grade,
        Book.subject == subject,
        Book.chapter == chapter,
    )
    return session.exec(statement).first()


def parse_json_list(value: Optional[str], fallback: Optional[list[str]] = None) -> list[str]:
    if not value:
        return fallback or []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return fallback or []


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    replacements = {
        "\u2011": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\xa0": " ",
        "\u211d": "real numbers",
        "\u211a": "rational numbers",
        "\u2124": "integers",
        "\u03c0": "pi",
        "\u221a": "square root",
    }
    cleaned = value
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return " ".join(cleaned.split())


def _derive_overview(book: Book) -> str:
    if book.summary_text:
        first_block = book.summary_text.split("\n\n")[0].strip()
        if first_block:
            return normalize_text(first_block)
    return normalize_text(f"{book.chapter} is part of Class {book.class_grade} {book.subject.title()} and should be studied with NCERT-first clarity.")


def _note_sentences(*values: Optional[str]) -> list[str]:
    sentences: list[str] = []
    for value in values:
        cleaned = normalize_text(value)
        if not cleaned:
            continue
        for piece in re.split(r"(?<=[.!?])\s+", cleaned):
            piece = piece.strip()
            if len(piece) > 20 and piece not in sentences:
                sentences.append(piece)
    return sentences


def _looks_generic_topic(topic: str) -> bool:
    generic = {
        "key concept",
        "daily-life connection",
        "important terms",
        "revision focus",
        "main idea",
        "core idea",
        "important ideas and examples",
        "revision questions and textbook practice",
    }
    return normalize_text(topic).lower() in generic


def _title_from_point(point: str, fallback: str) -> str:
    cleaned = normalize_text(point)
    if not cleaned:
        return fallback
    title = cleaned.split(".")[0].strip()
    words = title.split()
    if len(words) > 6:
        title = " ".join(words[:6])
    return title[:64] or fallback


def build_chapter_payload(book: Book) -> dict:
    subject_note = SUBJECT_OVERVIEWS.get(book.subject, "Build confidence through revision, examples, and practice.")
    action_labels = ACTION_LABELS.get(book.subject, ["Read the chapter", "Summarize it", "Try a quiz"])
    ingested = book.is_ingested and book.chunks_count > 0
    chapter_lower = book.chapter.lower()
    stored_topics = parse_json_list(book.topics_json)
    stored_key_points = parse_json_list(book.key_points_json)

    why_it_matters = {
        "math": f"This chapter strengthens problem-solving speed and step-by-step accuracy for topics around {chapter_lower}.",
        "science": f"This chapter helps students understand how {chapter_lower} connects to real-life observations, experiments, and board-style reasoning.",
        "history": f"This chapter helps students connect causes, events, and outcomes related to {chapter_lower}.",
        "geography": f"This chapter helps students read patterns, resources, and place-based ideas connected to {chapter_lower}.",
        "civics": f"This chapter builds understanding of institutions, people, and democratic systems through {chapter_lower}.",
        "economics": f"This chapter connects textbook concepts in {chapter_lower} with everyday life and decision-making.",
        "english": f"This chapter improves interpretation, expression, and confidence in writing through {chapter_lower}.",
        "physics": f"This chapter builds conceptual understanding and numerical confidence around {chapter_lower}.",
        "chemistry": f"This chapter helps students connect reactions, properties, and patterns in {chapter_lower}.",
        "biology": f"This chapter builds understanding of life processes, structures, and scientific reasoning through {chapter_lower}.",
    }.get(book.subject, f"This chapter builds confidence around {chapter_lower} and prepares students for revision and practice.")

    note_sentences = _note_sentences(book.summary_text, book.content_excerpt, *stored_key_points)
    default_key_points = stored_key_points[:]
    if not default_key_points:
        default_key_points = note_sentences[:4]
    if not default_key_points:
        default_key_points = [
            f"{book.chapter} should be revised with the textbook definitions, examples, and solved questions.",
            f"Focus on the main ideas and common question patterns from {book.chapter}.",
            "Review the NCERT examples carefully before moving to practice questions.",
        ]

    topics = stored_topics[:6] if stored_topics else [
        _title_from_point(point, book.chapter)
        for point in default_key_points
        if _title_from_point(point, book.chapter) and not _looks_generic_topic(_title_from_point(point, book.chapter))
    ][:6]
    if not topics:
        topics = [book.chapter]
    topics = [normalize_text(topic) for topic in topics if normalize_text(topic)]

    key_points = stored_key_points[:6] if stored_key_points else default_key_points
    key_points = [normalize_text(point) for point in key_points if normalize_text(point)]
    subtopic_notes = [
        {
            "title": _title_from_point(key_points[index % len(key_points)], topic) if key_points and _looks_generic_topic(topic) else topic,
            "note": " ".join(note_sentences[index:index + 2]) if note_sentences[index:index + 2] else _derive_overview(book),
            "ask_ai_prompt": f"Explain {topic} from the chapter {book.chapter} for Class {book.class_grade} in simple words with an example.",
        }
        for index, topic in enumerate(topics)
    ]

    sections = [
        {
            "title": "Chapter overview",
            "body": _derive_overview(book),
        },
        {
            "title": "Topics covered",
            "body": ", ".join(topics),
        },
        {
            "title": "Revision focus",
            "body": book.content_excerpt or "Revise this chapter by checking examples, short notes, and likely exam-style questions.",
        },
    ]

    return {
        "id": book.id,
        "class_grade": book.class_grade,
        "subject": book.subject,
        "chapter": book.chapter,
        "chapter_num": book.chapter_num,
        "is_ingested": book.is_ingested,
        "chunks_count": book.chunks_count,
        "overview": _derive_overview(book),
        "summary_text": book.summary_text or "",
        "content_excerpt": book.content_excerpt or "",
        "topics_covered": topics,
        "subtopic_notes": subtopic_notes,
        "study_focus": subject_note,
        "why_it_matters": why_it_matters,
        "key_points": key_points,
        "source_type": book.source_type,
        "learning_path": [
            "Start with the chapter overview and identify the main concept.",
            "Review the saved topics covered in this chapter.",
            "Use the summary or explain tools when something feels confusing.",
            "End with quiz practice to check retention.",
        ],
        "practice_paths": action_labels,
        "content_status": "ingested" if ingested else "catalog_only",
        "sections": sections,
        "reader_blocks": [
            {
                "title": "What to learn in this chapter",
                "body": f"Use this chapter to strengthen your grasp of {book.chapter.lower()} and connect it with previous NCERT concepts.",
            },
            {
                "title": "How to revise it well",
                "body": "Read actively, mark important lines, solve textbook questions, and use the tutor tools to fill gaps quickly.",
            },
        ],
    }
