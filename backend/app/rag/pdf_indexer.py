import os
import sys
import re
import json
import logging

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

import pypdf
from typing import List, Dict, Any
from app.rag.knowledge_base import DocumentChunk

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(DATA_DIR, "data", "indexed_book.json")
PDF_DIR = os.path.join(DATA_DIR, "data")

# Some PDFs trigger one font-encoding warning per font per page. Those warnings
# drown out useful indexing progress; extraction still proceeds through pypdf.
logging.getLogger("pypdf").setLevel(logging.ERROR)

def clean_text(text: str) -> str:
    # Remove excessive whitespace, page breaks, weird characters
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def index_textbook(force_reindex: bool = False) -> List[DocumentChunk]:
    """
    Parses the 747-page Operating System Concepts textbook and notes into indexed chunks.
    Saves a cached JSON for instant loading.
    """
    if os.path.exists(INDEX_FILE) and not force_reindex:
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [DocumentChunk(**item) for item in data]
        except Exception as e:
            print(f"Error loading cached index: {e}, reindexing...")

    chunks: List[DocumentChunk] = []
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')]

    for filename in pdf_files:
        filepath = os.path.join(PDF_DIR, filename)
        textbook_title = (
            "Operating System Concepts, 10th Edition"
            if filename == "os_textbook_10e.pdf"
            else "Operating System Concepts Essentials"
        )
        try:
            reader = pypdf.PdfReader(filepath)
            total_pages = len(reader.pages)
            print(f"Indexing {filename} ({total_pages} pages)...")

            # Book chapter detection regex
            current_chapter = "Operating Systems General"
            page_buffer = []
            buffer_start_page = 1

            for page_idx in range(total_pages):
                page_num = page_idx + 1
                try:
                    page_text = reader.pages[page_idx].extract_text() or ""
                except Exception:
                    page_text = ""

                cleaned = clean_text(page_text)
                if not cleaned or len(cleaned) < 50:
                    continue

                # Filter out homework exercises, bibliography, index, table of contents
                lower_text = cleaned.lower()
                if any(lower_text.startswith(bad) for bad in ["exercises", "practice exercises", "index", "contents", "brief contents", "preface"]):
                    continue
                if "exercises 3" in lower_text or "exercises 7." in lower_text or "exercises 8." in lower_text:
                    continue

                # Check if this page introduces a new chapter
                ch_match = re.search(r'(CHAPTER\s+\d+[\s\w:]+|PART\s+\w+[\s\w:]+)', cleaned, re.IGNORECASE)
                if ch_match:
                    found_ch = ch_match.group(1).strip()
                    if len(found_ch) < 60:
                        current_chapter = found_ch.title()

                page_buffer.append((page_num, cleaned))

                # Create a chunk every 2-3 pages or ~600 words for optimal retrieval
                combined_words = sum(len(p[1].split()) for p in page_buffer)
                if combined_words >= 500 or page_idx == total_pages - 1:
                    chunk_text = " ".join(p[1] for p in page_buffer)
                    start_p = page_buffer[0][0]
                    end_p = page_buffer[-1][0]
                    page_ref = f"Page {start_p}" if start_p == end_p else f"Pages {start_p}-{end_p}"

                    # Extract common technical terms in this chunk as keywords
                    potential_keywords = re.findall(r'\b[a-zA-Z]{4,}\b', chunk_text.lower())
                    freq = {}
                    for kw in potential_keywords:
                        if kw not in ['this', 'that', 'with', 'from', 'have', 'were', 'which', 'their', 'there', 'system', 'operating']:
                            freq[kw] = freq.get(kw, 0) + 1
                    top_keywords = sorted(freq.keys(), key=lambda k: freq[k], reverse=True)[:12]

                    # Extract the first sentence or heading as subtopic
                    first_words = " ".join(chunk_text.split()[:8]) + "..."

                    source_label = f"{textbook_title} ({page_ref}, {current_chapter})"

                    chunk = DocumentChunk(
                        id=f"{filename}-p{start_p}",
                        topic=current_chapter,
                        subtopic=f"Excerpt: {first_words}",
                        source=source_label,
                        content=chunk_text[:1800],  # Keep comprehensive excerpt
                        keywords=top_keywords
                    )
                    chunks.append(chunk)
                    page_buffer = []

        except Exception as e:
            print(f"Failed to index {filename}: {e}")

    # Save to cache
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump([chunk.model_dump() for chunk in chunks], f, indent=2)

    print(f"Successfully indexed {len(chunks)} textbook sections from uploaded files.")
    return chunks

if __name__ == "__main__":
    index_textbook(force_reindex=True)
