import re
import os
import json
from typing import List, Tuple, Optional
from rank_bm25 import BM25Okapi
from app.rag.knowledge_base import COURSE_MATERIAL, DocumentChunk

INDEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "indexed_book.json")

def load_full_corpus() -> List[DocumentChunk]:
    corpus = list(COURSE_MATERIAL)
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                book_chunks = [DocumentChunk(**item) for item in data]
                corpus.extend(book_chunks)
        except Exception as e:
            print(f"Warning: could not load indexed book: {e}")
    return corpus

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "about",
    "is", "are", "was", "were", "what", "how", "why", "when", "where", "which", "who",
    "does", "do", "did", "can", "could", "should", "would", "tell", "explain", "describe",
    "work", "works", "me", "you", "my", "your", "of", "from", "algorithm", "algorithms",
    "concept", "method", "problem", "problems", "definition"
}

# Broad abbreviations and common nouns create many false exact matches in a
# textbook index. Let BM25 rank these instead of treating them as decisive.
GENERIC_KEYWORDS = {"os", "system", "process", "memory", "computer", "operating system"}

def tokenize(text: str) -> List[str]:
    words = re.findall(r'\b[a-zA-Z0-9_\-]+\b', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]

class CourseMaterialRetriever:
    def __init__(self, corpus: Optional[List[DocumentChunk]] = None):
        self.corpus = corpus or load_full_corpus()
        self.tokenized_corpus = [
            tokenize(f"{chunk.topic} {chunk.subtopic} {chunk.content} {' '.join(chunk.keywords)}")
            for chunk in self.corpus
        ]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
        # Minimum score threshold for domain keywords
        self.relevance_threshold = 0.5

    def search(self, query: str, top_k: int = 2) -> Tuple[List[DocumentChunk], bool]:
        q_lower = query.lower()
        normalized_query = re.sub(r'\bos\b', 'operating system', q_lower)
        query_forms = [normalized_query]
        if "what is operating system" in normalized_query:
            query_forms.append(normalized_query.replace("what is operating system", "what is an operating system"))

        # For broad introductory questions, retrieve the definition plus the
        # book's own implementation examples instead of matching on "implementation" alone.
        asks_about_os = bool(re.search(r'\b(os|operating systems?)\b', q_lower))
        asks_for_examples = bool(re.search(r'\b(example|examples|real[- ]life|implementation|practice|used)\b', q_lower))
        if asks_about_os and re.search(r'\bwhat\s+is\b|\bexample|\bimplementation|\breal[- ]life', q_lower):
            definition = next((c for c in self.corpus if c.id == "ostep-ch2-intro"), None)
            book_definition = next((c for c in self.corpus if "an operating system provides the environment within which programs are executed" in c.content.lower() and "chapter 2 operating" in c.source.lower()), None)
            results = [c for c in (definition, book_definition) if c is not None]
            if asks_for_examples:
                implementation = next((c for c in self.corpus if "1.13 open-source operating systems" in c.subtopic.lower() and "which can act as web servers as well as clients" in c.content.lower()), None)
                tenth_edition_example = next((
                    c for c in self.corpus
                    if c.source.startswith("Operating System Concepts, 10th Edition")
                    and "cloud computing" in c.content.lower()
                    and "load balancer" in c.content.lower()
                ), None)
                if tenth_edition_example is not None:
                    results.append(tenth_edition_example)
                elif implementation is not None:
                    results.append(implementation)
            if results:
                return results[:top_k], True

        tokens = tokenize(" ".join(query_forms))
        
        # 1. Exact technical keyword check with specificity scoring
        scored_exact = []
        for chunk in self.corpus:
            chunk_score = 0
            # Higher score if the query closely matches the subtopic or topic title
            if any(chunk.subtopic.lower() in form or form in chunk.subtopic.lower() for form in query_forms):
                chunk_score += 10
            if any(chunk.topic.lower() in form for form in query_forms):
                chunk_score += 5

            for kw in chunk.keywords:
                if kw.lower() not in GENERIC_KEYWORDS and len(kw.strip()) > 2 and any(re.search(r'\b' + re.escape(kw) + r'\b', form) for form in query_forms):
                    # Longer matching keyword phrases get higher weight (e.g. "mutual exclusion" > "lock")
                    chunk_score += len(kw)

            if chunk_score > 0:
                scored_exact.append((chunk, chunk_score))

        # Combine precise title/keyword matches with BM25 so a strong phrase
        # match doesn't prevent useful supporting textbook passages from joining it.
        if not tokens:
            return [chunk for chunk, _ in sorted(scored_exact, key=lambda x: x[1], reverse=True)[:top_k]], bool(scored_exact)

        scores = self.bm25.get_scores(tokens)
        scored_pairs = sorted(zip(self.corpus, scores), key=lambda x: x[1], reverse=True)

        top_score = scored_pairs[0][1] if scored_pairs else 0.0
        
        exact_sorted = [chunk for chunk, _ in sorted(scored_exact, key=lambda x: x[1], reverse=True)]
        if top_score < self.relevance_threshold and not exact_sorted:
            return [], False

        results = list(exact_sorted)
        for chunk, score in scored_pairs:
            if score >= self.relevance_threshold and all(chunk.id != existing.id for existing in results):
                results.append(chunk)
            if len(results) >= top_k:
                break
        return results[:top_k], bool(results)
