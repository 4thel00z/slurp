#!/usr/bin/env python3
"""
OpenRouter client for generating questions and answers from documents
"""

import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from openai import OpenAI

# Import prompts based on language
from prompts.prompts_en import (
    ANSWER_AND_CHUNKS_PROMPT as ANSWER_AND_CHUNKS_PROMPT_EN,
    CROSS_PAGE_PROMPT as CROSS_PAGE_PROMPT_EN,
    EASY_PROMPT as EASY_PROMPT_EN,
    HARD_PROMPT as HARD_PROMPT_EN,
    HIERARCHICAL_PROMPT as HIERARCHICAL_PROMPT_EN,
    MEDIUM_PROMPT as MEDIUM_PROMPT_EN,
    MIXED_PROMPT as MIXED_PROMPT_EN,
    LONG_EASY_PROMPT as LONG_EASY_PROMPT_EN,
    LONG_MEDIUM_PROMPT as LONG_MEDIUM_PROMPT_EN,
    LONG_HARD_PROMPT as LONG_HARD_PROMPT_EN,
    LONG_MIXED_PROMPT as LONG_MIXED_PROMPT_EN
)

from prompts.prompts_de import (
    ANSWER_AND_CHUNKS_PROMPT as ANSWER_AND_CHUNKS_PROMPT_DE,
    CROSS_PAGE_PROMPT as CROSS_PAGE_PROMPT_DE,
    EASY_PROMPT as EASY_PROMPT_DE,
    HARD_PROMPT as HARD_PROMPT_DE,
    HIERARCHICAL_PROMPT as HIERARCHICAL_PROMPT_DE,
    MEDIUM_PROMPT as MEDIUM_PROMPT_DE,
    MIXED_PROMPT as MIXED_PROMPT_DE,
    LONG_EASY_PROMPT as LONG_EASY_PROMPT_DE,
    LONG_MEDIUM_PROMPT as LONG_MEDIUM_PROMPT_DE,
    LONG_HARD_PROMPT as LONG_HARD_PROMPT_DE,
    LONG_MIXED_PROMPT as LONG_MIXED_PROMPT_DE
)

@dataclass
class QuestionAnswer:
    """Represents a question-answer pair with relevant chunks."""
    question: str
    answer: str
    relevant_chunks: List[str]
    document_title: str
    document_url: str


class OpenRouterClient:
    """Client for interacting with OpenRouter API using OpenAI client."""
    
    def __init__(self, api_key: Optional[str] = None, 
                 model: str = "google/gemini-2.0-flash-exp",
                 language: str = "en"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. "
                           "Set OPENROUTER_API_KEY environment variable.")
        
        self.model = model
        self.language = language.lower()
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        self.extra_headers = {
            "HTTP-Referer": "https://github.com/your-repo",  # Update as needed
            "X-Title": "Confluence RAG Dataset Generator"
        }
        
        # Initialize language-specific prompts
        self._init_language_prompts()
    
    def _init_language_prompts(self):
        """Initialize prompts based on the selected language."""
        if self.language == "de":
            self.ANSWER_AND_CHUNKS_PROMPT = ANSWER_AND_CHUNKS_PROMPT_DE
            self.CROSS_PAGE_PROMPT = CROSS_PAGE_PROMPT_DE
            self.EASY_PROMPT = EASY_PROMPT_DE
            self.HARD_PROMPT = HARD_PROMPT_DE
            self.HIERARCHICAL_PROMPT = HIERARCHICAL_PROMPT_DE
            self.MEDIUM_PROMPT = MEDIUM_PROMPT_DE
            self.MIXED_PROMPT = MIXED_PROMPT_DE
            self.LONG_EASY_PROMPT = LONG_EASY_PROMPT_DE
            self.LONG_MEDIUM_PROMPT = LONG_MEDIUM_PROMPT_DE
            self.LONG_HARD_PROMPT = LONG_HARD_PROMPT_DE
            self.LONG_MIXED_PROMPT = LONG_MIXED_PROMPT_DE
        else:  # Default to English
            self.ANSWER_AND_CHUNKS_PROMPT = ANSWER_AND_CHUNKS_PROMPT_EN
            self.CROSS_PAGE_PROMPT = CROSS_PAGE_PROMPT_EN
            self.EASY_PROMPT = EASY_PROMPT_EN
            self.HARD_PROMPT = HARD_PROMPT_EN
            self.HIERARCHICAL_PROMPT = HIERARCHICAL_PROMPT_EN
            self.MEDIUM_PROMPT = MEDIUM_PROMPT_EN
            self.MIXED_PROMPT = MIXED_PROMPT_EN
            self.LONG_EASY_PROMPT = LONG_EASY_PROMPT_EN
            self.LONG_MEDIUM_PROMPT = LONG_MEDIUM_PROMPT_EN
            self.LONG_HARD_PROMPT = LONG_HARD_PROMPT_EN
            self.LONG_MIXED_PROMPT = LONG_MIXED_PROMPT_EN
    
    def _make_request(self, messages: List[Dict[str, str]], 
                     max_tokens: int = 2000) -> str:
        """Make a request to OpenRouter API using OpenAI client."""
        try:
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return completion.choices[0].message.content
        
        except Exception as e:
            print(f"Error making request to OpenRouter: {e}")
            return ""
    
    def generate_questions(self, document_content: str, document_title: str, 
                          document_url: str, difficulty_ratio: str = "mixed") -> List[QuestionAnswer]:
        """Generate questions and answers from document content with difficulty control."""
        
        # Determine number of questions based on document size
        word_count = len(document_content.split())
        if word_count < 500:
            num_questions = 1
        elif word_count < 1000:
            num_questions = 2
        elif word_count < 2000:
            num_questions = 3
        elif word_count < 4000:
            num_questions = 4
        else:
            num_questions = 5
        
        print(f"Generating {num_questions} questions for document: {document_title}")
        
        # Create chunks for better processing
        chunks = self._create_chunks(document_content)
        
        questions_answers = []
        
        # Define difficulty distribution based on ratio
        difficulty_distributions = {
            "easy": ["easy"] * num_questions,
            "medium": ["medium"] * num_questions,
            "hard": ["hard"] * num_questions,
            "mixed": self._create_mixed_difficulty_distribution(num_questions),
            "balanced": self._create_balanced_difficulty_distribution(num_questions)
        }
        
        # Get difficulty sequence for this document
        difficulties = difficulty_distributions.get(difficulty_ratio, 
                                                   difficulty_distributions["mixed"])
        
        for i in range(num_questions):
            difficulty = difficulties[i] if i < len(difficulties) else "mixed"
            print(f"  Generating {difficulty} question {i+1}/{num_questions}...")
            
            # Generate question with specified difficulty
            question = self._generate_question(document_content, 
                                             document_title, i+1, difficulty)
            if not question:
                continue
            
            # Generate answer and find relevant chunks
            answer, relevant_chunks = self._generate_answer_and_chunks(
                document_content, question, chunks
            )
            
            if answer and relevant_chunks:
                qa = QuestionAnswer(
                    question=question,
                    answer=answer,
                    relevant_chunks=relevant_chunks,
                    document_title=document_title,
                    document_url=document_url
                )
                questions_answers.append(qa)
            
            # Rate limiting
            time.sleep(1)
        
        return questions_answers
    
    def _create_chunks(self, content: str, chunk_size: int = 1000) -> List[str]:
        """Create chunks from document content."""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
        
        return chunks
    
    def _generate_question(self, content: str, title: str, 
                          question_num: int, difficulty: str = "mixed") -> str:
        """Generate a question from the document with specified difficulty level."""
        
        # Ensure content is a string and limit its length
        if not isinstance(content, str):
            content = str(content)
        content_preview = content[:3000] if len(content) > 3000 else content
        
        # Define difficulty-based prompts using language-specific prompts
        difficulty_prompts = {
            "easy": self.EASY_PROMPT,
            "medium": self.MEDIUM_PROMPT,
            "hard": self.HARD_PROMPT,
            "mixed": self.MIXED_PROMPT,
        }
        
        # Get the appropriate prompt based on difficulty
        prompt_template = difficulty_prompts.get(difficulty, difficulty_prompts["mixed"])
        prompt = prompt_template.format(title=title, content=content_preview, question_num=question_num)
        
        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, max_tokens=500)
        
        # Clean up the response - more robust parsing
        question = response.strip()
        
        # Remove common prefixes that might be added
        prefixes_to_remove = [
            f"Question {question_num}:",
            "Question:",
            f"Q{question_num}:",
            "Q:",
            f"{question_num}.",
            "Here's a question:",
            "Question:"
        ]
        
        for prefix in prefixes_to_remove:
            if question.startswith(prefix):
                question = question[len(prefix):].strip()
                break
        
        # Remove quotes if the entire question is wrapped in them
        if question.startswith('"') and question.endswith('"'):
            question = question[1:-1].strip()
        elif question.startswith("'") and question.endswith("'"):
            question = question[1:-1].strip()
        
        return question
    
    def _generate_answer_and_chunks(self, content: str, question: str, 
                                   chunks: List[str]) -> tuple[str, List[str]]:
        """Generate answer and find relevant chunks for the question."""
        
        # Use language-specific prompt
        prompt = self.ANSWER_AND_CHUNKS_PROMPT.format(content=content, question=question)
        
        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, max_tokens=1500)
        
        # Parse the response
        if "ANSWER:" not in response or "CHUNKS:" not in response:
            return "", []
        
        # Extract answer
        answer_start = response.find("ANSWER:") + 7
        chunks_start = response.find("CHUNKS:")
        answer = response[answer_start:chunks_start].strip()
        
        # Extract chunks
        chunks_text = response[chunks_start + 7:].strip()
        relevant_chunks = []
        
        if "===" in chunks_text:
            # Split by === and clean up
            chunk_parts = chunks_text.split("===")
            for part in chunk_parts:
                chunk = part.strip()
                if chunk and len(chunk) > 50:  # Minimum chunk size
                    relevant_chunks.append(chunk)
        
        return answer, relevant_chunks
    
    def _generate_hierarchical_question(self, content: str, title: str, 
                                      parent_id: str, child_pages: List[str], 
                                      question_num: int) -> str:
        """Generate a question that considers hierarchical context."""
        
        hierarchy_context = ""
        if parent_id:
            hierarchy_context += f"This page has a parent page (ID: {parent_id}). "
        if child_pages:
            hierarchy_context += f"This page has {len(child_pages)} child pages. "
        
        # Use language-specific prompt
        prompt = self.HIERARCHICAL_PROMPT.format(
            title=title, 
            hierarchy_context=hierarchy_context, 
            content=content[:3000],
            question_num=question_num
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, max_tokens=500)
        
        # Clean up the response
        question = response.strip()
        if question.startswith("Question"):
            question = question.split(":", 1)[1].strip()
        
        return question
    
    def _generate_cross_page_question(self, combined_content: str, 
                                    parent_title: str, 
                                    children: List[Dict]) -> str:
        """Generate a question that spans multiple related pages."""
        
        children_info = "\n".join([f"- {child['title']}" for child in children])
        
        # Use language-specific prompt
        prompt = self.CROSS_PAGE_PROMPT.format(
            parent_title=parent_title,
            children_info=children_info,
            combined_content=combined_content
        )
        
        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, max_tokens=500)
        
        # Clean up the response
        question = response.strip()
        if question.startswith("Question"):
            question = question.split(":", 1)[1].strip()
        
        return question
    
    def _create_mixed_difficulty_distribution(self, num_questions: int) -> List[str]:
        """Create a mixed distribution of difficulties."""
        import random
        
        difficulties = ["easy", "medium", "hard"]
        weights = [0.3, 0.4, 0.3]  # 30% easy, 40% medium, 30% hard
        
        return random.choices(difficulties, weights=weights, k=num_questions)
    
    def _create_balanced_difficulty_distribution(self, num_questions: int) -> List[str]:
        """Create a balanced distribution ensuring all difficulty levels are represented."""
        difficulties = []
        
        # Ensure at least one of each difficulty level
        difficulties.extend(["easy", "medium", "hard"])
        
        # Fill remaining slots with balanced distribution
        remaining = num_questions - 3
        if remaining > 0:
            balanced = ["easy", "medium", "hard"] * (remaining // 3)
            balanced.extend(["easy", "medium", "hard"][:remaining % 3])
            difficulties.extend(balanced)
        
        # Shuffle to avoid predictable patterns
        import random
        random.shuffle(difficulties)
        
        return difficulties[:num_questions]
    
    def _generate_long_question(self, documents: List[Dict], 
                            question_num: int, difficulty: str = "mixed") -> str:
        """
        Generate a long, complex query that spans multiple documents.
        Always produces multi-sentence queries with context, scenarios, or detailed requests.
        
        Args:
            documents: List of document dictionaries with 'title' and 'content' keys
            question_num: Question number for the prompt
            difficulty: Difficulty level (easy, medium, hard, mixed)
        
        Returns:
            Generated long query string (always multi-sentence with context)
        """
        # Combine document content with titles
        combined_content = ""
        for i, doc in enumerate(documents, 1):
            combined_content += f"Document {i}: {doc['title']}\n"
            combined_content += f"{doc['content'][:2000]}...\n\n"  # Limit each doc to 2000 chars
        
        # Ensure content is a string and limit total length
        if not isinstance(combined_content, str):
            combined_content = str(combined_content)
        combined_content = combined_content[:5000] if len(combined_content) > 5000 else combined_content
        
        # Define difficulty-based prompts for multi-document queries using language-specific prompts
        difficulty_prompts = {
            "easy": self.LONG_EASY_PROMPT,
            "medium": self.LONG_MEDIUM_PROMPT,
            "hard": self.LONG_HARD_PROMPT,
            "mixed": self.LONG_MIXED_PROMPT,
        }
        
        # Get the appropriate prompt based on difficulty
        prompt_template = difficulty_prompts.get(difficulty, difficulty_prompts["mixed"])
        prompt = prompt_template.format(content=combined_content, question_num=question_num)
        
        messages = [{"role": "user", "content": prompt}]
        response = self._make_request(messages, max_tokens=1000)  # Allow longer responses for complex queries
        
        # Clean up the response - more robust parsing
        query = response.strip()
        
        # Remove common prefixes that might be added
        prefixes_to_remove = [
            f"Query {question_num}:",
            f"Question {question_num}:",
            "Query:",
            "Question:",
            f"Q{question_num}:",
            "Q:",
            f"{question_num}.",
            "Here's a query:",
            "Here's a question:",
            "Query:",
            "Question:"
        ]
        
        for prefix in prefixes_to_remove:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                break
        
        # Remove quotes if the entire query is wrapped in them
        if query.startswith('"') and query.endswith('"'):
            query = query[1:-1].strip()
        elif query.startswith("'") and query.endswith("'"):
            query = query[1:-1].strip()
        
        return query


class DatasetManager:
    """Manages the RAG dataset JSON file."""
    
    def __init__(self, dataset_file: str = "rag_dataset.json"):
        self.dataset_file = dataset_file
        self.dataset = self._load_dataset()
    
    def _load_dataset(self) -> Dict[str, Any]:
        """Load existing dataset or create new one."""
        if os.path.exists(self.dataset_file):
            try:
                with open(self.dataset_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {self.dataset_file}. "
                      f"Creating new dataset.")
        
        return {
            "metadata": {
                "created": "",
                "total_questions": 0,
                "total_documents": 0
            },
            "questions": []
        }
    
    def add_questions(self, questions: List[QuestionAnswer]) -> None:
        """Add new questions to the dataset."""
        for qa in questions:
            question_data = {
                "document_title": qa.document_title,
                "document_url": qa.document_url,
                "question": qa.question,
                "answer": qa.answer,
                "relevant_chunks": qa.relevant_chunks
            }
            self.dataset["questions"].append(question_data)
        
        # Update metadata
        self.dataset["metadata"]["total_questions"] = len(self.dataset["questions"])
        self.dataset["metadata"]["total_documents"] = len(set(
            q["document_title"] for q in self.dataset["questions"]
        ))
        
        self._save_dataset()
    
    def _save_dataset(self) -> None:
        """Save dataset to JSON file."""
        with open(self.dataset_file, 'w', encoding='utf-8') as f:
            json.dump(self.dataset, f, indent=2, ensure_ascii=False)
        
        print(f"Dataset saved to {self.dataset_file}")
        print(f"Total questions: {self.dataset['metadata']['total_questions']}")
        print(f"Total documents: {self.dataset['metadata']['total_documents']}")
    
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        return self.dataset["metadata"] 