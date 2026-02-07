"""Skill extraction, keyword extraction, and text utilities."""

import re
from collections import Counter

# Common tech skills for extraction
TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    "sql", "html", "css", "bash", "shell", "powershell",
    # Frameworks & Libraries
    "react", "angular", "vue", "next.js", "nextjs", "node.js", "nodejs",
    "django", "flask", "fastapi", "spring", "express", ".net", "dotnet",
    "rails", "laravel", "svelte", "remix", "gatsby",
    # Cloud & Infra
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "github actions", "ci/cd", "cicd",
    "linux", "nginx", "apache",
    # Data & ML
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "spark",
    "hadoop", "airflow", "kafka", "elasticsearch",
    # Databases
    "postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra",
    "dynamodb", "sqlite", "oracle", "sql server",
    # Tools & Practices
    "git", "agile", "scrum", "rest", "graphql", "grpc", "microservices",
    "api", "devops", "sre", "tdd", "unit testing",
}

# Common Silicon Valley location indicators
SILICON_VALLEY_LOCATIONS = {
    "silicon valley", "san francisco", "san jose", "palo alto", "mountain view",
    "sunnyvale", "cupertino", "menlo park", "santa clara", "redwood city",
    "fremont", "oakland", "berkeley", "south bay", "bay area", "sf bay",
    "sf", "san mateo", "foster city",
}


def extract_skills(text: str) -> set[str]:
    """Extract recognized tech skills from text."""
    text_lower = text.lower()
    found = set()

    for skill in TECH_SKILLS:
        # Use word boundary matching for short skills to avoid false positives
        if len(skill) <= 2:
            if re.search(rf"\b{re.escape(skill)}\b", text_lower):
                found.add(skill)
        elif skill in text_lower:
            found.add(skill)

    return found


def extract_keywords(text: str, top_n: int = 30) -> list[str]:
    """Extract top keywords from text by frequency (excluding stop words)."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "shall", "this", "that",
        "these", "those", "i", "you", "he", "she", "it", "we", "they", "me",
        "him", "her", "us", "them", "my", "your", "his", "its", "our", "their",
        "not", "no", "nor", "so", "if", "then", "than", "too", "very", "just",
        "about", "up", "out", "all", "also", "as", "into", "over", "after",
        "before", "between", "through", "during", "above", "below", "each",
        "few", "more", "most", "other", "some", "such", "only", "own", "same",
        "when", "where", "how", "what", "which", "who", "whom", "why",
        "work", "experience", "team", "company", "role", "ability",
    }

    words = re.findall(r"\b[a-z][a-z+#.]{1,30}\b", text.lower())
    filtered = [w for w in words if w not in stop_words]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def normalize_title(title: str) -> str:
    """Normalize a job title for comparison."""
    title = title.lower().strip()
    # Remove common prefixes/suffixes
    for prefix in ["senior ", "sr. ", "sr ", "junior ", "jr. ", "jr ", "lead ", "staff ", "principal "]:
        title = title.removeprefix(prefix)
    for suffix in [" i", " ii", " iii", " iv", " v"]:
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    return title.strip()


def title_similarity(title1: str, title2: str) -> float:
    """Compute similarity between two job titles (0.0-1.0)."""
    t1 = normalize_title(title1)
    t2 = normalize_title(title2)

    if t1 == t2:
        return 1.0

    words1 = set(t1.split())
    words2 = set(t2.split())

    if not words1 or not words2:
        return 0.0

    overlap = words1 & words2
    return len(overlap) / max(len(words1), len(words2))


def is_silicon_valley_location(location: str) -> bool:
    """Check if a location string refers to Silicon Valley / Bay Area."""
    location_lower = location.lower()
    return any(loc in location_lower for loc in SILICON_VALLEY_LOCATIONS)


def extract_years_experience(text: str) -> int | None:
    """Try to extract years of experience from text (e.g., '5+ years')."""
    patterns = [
        r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)",
        r"(?:experience|exp)\s*(?:of\s*)?(\d+)\+?\s*(?:years?|yrs?)",
        r"(\d+)\+?\s*(?:years?|yrs?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return None
