"""Compatibility wrapper for existing imports; generation now uses Groq."""
from typing import List

from app.pipeline import try_groq_completion


def generate_os_explanation(
    query: str,
    textbook_contexts: List[str],
    topic: str,
    subtopic: str,
    sources: str,
) -> str:
    context = "\n\n---\n\n".join(textbook_contexts[:3])
    prompt = f"""You are KAIROS, a patient Operating Systems tutor. Answer the student's question using only the retrieved textbook context. Explain the concept clearly and simply, then give a key takeaway. Do not invent details that the passages do not support.

Student question: {query}
Topic: {topic} — {subtopic}
Textbook sources: {sources}

Retrieved textbook passages:
{context}

Write a clear student-friendly answer in Markdown."""
    return try_groq_completion(prompt) or "The textbook passages are available, but Groq could not generate an explanation right now. Please try again shortly."
