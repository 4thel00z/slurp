from textwrap import dedent


EASY_PROMPT = dedent(
    """You are creating evaluation questions for a conversational RAG (Retrieval-Augmented Generation) system.

IMPORTANT CONTEXT: The questions you generate will be used to test a RAG system where this document will be stored in a vector database. Users will ask questions WITHOUT seeing the document, so avoid vague references like "this document", "this team", "this policy", "the above", etc. Instead, use specific names, terms, and details from the document content.

Document Title: {title}

Document Content:
{content}

Generate ONE easy question that a user might naturally ask when they need information that would be found in this type of document. The question should:

CHARACTERISTICS:
- Be answerable through direct text matching or simple keyword search
- Focus on explicit facts, definitions, or basic details mentioned in the document
- Use natural, conversational language (as if someone is asking a chatbot)
- Be specific enough to have a clear, factual answer

QUESTION TYPES TO CONSIDER:
- "What is [specific term/concept]?"
- "How much/many [specific detail]?"
- "When did [specific event] happen?"
- "Who is responsible for [specific thing]?"
- "Where is [specific location/item]?"

AVOID VAGUE REFERENCES:
- "What is the purpose of this team?" (use specific team name instead)
- "How does this process work?" (specify which process)
- "What does this document say about..." (refer to specific topics directly)

IMPORTANT: Use varied question starters. Avoid repetitive patterns like "Can you tell me more about..." or "What can you tell me about...". Mix different question types and formats.

Generate ONE conversational question that tests basic factual retrieval."""
)

MEDIUM_PROMPT = dedent(
    """You are creating evaluation questions for a conversational RAG (Retrieval-Augmented Generation) system.

IMPORTANT CONTEXT: The questions you generate will be used to test a RAG system where this document will be stored in a vector database. Users will ask questions WITHOUT seeing the document, so avoid vague references like "this document", "this policy", "these requirements", "the above", etc. Instead, use specific names, terms, and details from the document content.

Document Title: {title}

Document Content:
{content}

Generate ONE medium-difficulty question that a user might naturally ask when seeking information that would be found in this type of document. The question should:

CHARACTERISTICS:
- Require connecting 2-3 related pieces of information from the document
- Need some interpretation or explanation beyond direct quotes
- Use natural, conversational language
- Test the system's ability to understand relationships and context

Generate ONE conversational question that tests reasoning and connection-making."""
)

HARD_PROMPT = dedent(
    """You are creating evaluation questions for a conversational RAG (Retrieval-Augmented Generation) system.

IMPORTANT CONTEXT: The questions you generate will be used to test a RAG system where this document will be stored in a vector database. Users will ask questions WITHOUT seeing the document, so avoid vague references like "this document", "this approach", "these guidelines", "the mentioned", etc. Instead, use specific names, terms, and details from the document content.

Document Title: {title}

Document Content:
{content}

Generate ONE challenging question that a user might naturally ask when seeking complex information that would be found in this type of document. The question should:

CHARACTERISTICS:
- Require synthesizing information from multiple sections or concepts
- Need inference, analysis, or complex reasoning beyond what's explicitly stated
- Test edge cases, implications, or deeper understanding
- Use natural, conversational language
- May require the system to identify gaps or limitations in the provided information

Generate ONE conversational question that tests complex reasoning and synthesis."""
)

MIXED_PROMPT = dedent(
    """You are creating evaluation questions for a conversational RAG (Retrieval-Augmented Generation) system.

IMPORTANT CONTEXT: The questions you generate will be used to test a RAG system where this document will be stored in a vector database. Users will ask questions WITHOUT seeing the document, so avoid vague references like "this document", "this information", "the above", "these guidelines", etc. Instead, use specific names, terms, and details from the document content.

Document Title: {title}

Document Content:
{content}

Generate ONE question that a user might naturally ask when seeking information that would be found in this type of document.

ADAPTIVE DIFFICULTY:
- For simple documents: Focus on factual questions and basic understanding
- For complex documents: Include reasoning, comparison, or application questions
- For technical documents: Test both concept understanding and practical application
- For policy documents: Test both rule comprehension and scenario application

QUESTION CHARACTERISTICS:
- Use natural, conversational language (as if talking to a helpful assistant)
- Be specific and actionable when possible
- Match the complexity and depth of the source material
- Test the most important or useful aspects of the document

QUESTION TYPES (choose based on content):
BASIC: "What is [specific term]...", "How many [specific items]...", "When does [specific event]..."
REASONING: "How does [specific system A] relate to [specific system B]?", "What's the difference between [specific option X] and [specific option Y]..."
APPLICATION: "What should I do if [specific scenario]...", "How can I apply [specific process] to..."
SYNTHESIS: "What would happen if [specific condition]...", "How do [specific requirements] interact..."

AVOID VAGUE REFERENCES - Always be specific:
❌ "What should I do if this happens?"
✅ "What should I do if the server crashes during deployment?"

❌ "How does this relate to that?"
✅ "How does the backup policy relate to disaster recovery procedures?"

IMPORTANT: Use varied question starters. Avoid repetitive patterns like "Can you tell me more about..." Create diverse, specific questions that match the document content.

Generate ONE conversational question appropriate for this document's complexity."""
)

ANSWER_AND_CHUNKS_PROMPT = dedent(
    """You are an expert at answering questions and identifying relevant document chunks for RAG evaluation.

Document Content:
{content}

Question:
{question}

Please provide:
1. A comprehensive answer to the question
2. Identify 2-3 most relevant chunks from the document that support your answer
"""
)

HIERARCHICAL_PROMPT = dedent(
    """You are an expert at creating questions for RAG model evaluation with hierarchical document structures.

Document Title: {title}
Hierarchy Context: {hierarchy_context}

Document Content:
{content}

Generate ONE challenging, non-trivial question that tests understanding of the hierarchy context."""
)

CROSS_PAGE_PROMPT = dedent(
    """You are an expert at creating cross-document questions for RAG model evaluation.

Combined Content from multiple documents with titles, content and urls:
{combined_content}

Generate ONE challenging question requiring cross-references between pages."""
)

LONG_EASY_PROMPT = dedent(
    """You are creating evaluation queries for a conversational RAG (Retrieval-Augmented Generation) system that can access multiple documents.

IMPORTANT CONTEXT: The queries you generate will be used to test a RAG system where these documents will be stored in a vector database. Users will ask questions WITHOUT seeing the documents, so avoid vague references like "these documents", "the above", "this information", etc. Instead, use specific names, terms, and details from the document content.

Multiple Documents:
{content}

Generate ONE long, multi-sentence, context-rich query for basic factual retrieval across documents."""
)

LONG_MEDIUM_PROMPT = dedent(
    """You are creating evaluation queries for a conversational RAG (Retrieval-Augmented Generation) system that can access multiple documents.

IMPORTANT CONTEXT: The queries you generate will be used to test a RAG system where these documents will be stored in a vector database. Users will ask questions WITHOUT seeing the documents, so avoid vague references like "these documents", "the policies", "the requirements", etc. Instead, use specific names, terms, and details from the document content.

Multiple Documents:
{content}

Generate ONE medium-difficulty, multi-document query requiring linking information across sources."""
)

LONG_HARD_PROMPT = dedent(
    """You are creating evaluation queries for a conversational RAG (Retrieval-Augmented Generation) system that can access multiple documents.

IMPORTANT CONTEXT: The queries you generate will be used to test a RAG system where these documents will be stored in a vector database. Users will ask questions WITHOUT seeing the documents, so avoid vague references like "these documents", "the approaches", "the guidelines", etc. Instead, use specific names, terms, and details from the document content.

Multiple Documents:
{content}

Generate ONE challenging, multi-document query demanding complex synthesis and analysis."""
)

LONG_MIXED_PROMPT = dedent(
    """You are creating evaluation queries for a conversational RAG (Retrieval-Augmented Generation) system that can access multiple documents.

IMPORTANT CONTEXT: The queries you generate will be used to test a RAG system where these documents will be stored in a vector database. Users will ask questions WITHOUT seeing the documents, so avoid vague references like "these documents", "this information", "the above", etc. Instead, use specific names, terms, and details from the document content.

Multiple Documents:
{content}

Generate ONE adaptive-complexity, multi-document query appropriate for the given documents."""
)
