#!/usr/bin/env python3
"""
RAG Dataset Generator with Hierarchical Crawling

This script downloads Confluence pages with sub-page discovery and generates a
comprehensive RAG dataset with questions and answers, including hierarchical
relationships.
"""

import argparse
import os
import sys
import json
import uuid
from typing import Dict, List

from confluence_crawler import crawl_confluence_pages, process_confluence_spaces
from openrouter_client import OpenRouterClient, DatasetManager, QuestionAnswer
from eval_data_conversion_script import (
    convert_rag_dataset_to_agentic_eval_format
)


class HierarchicalDatasetManager(DatasetManager):
    """Dataset manager that handles hierarchical relationships."""
    
    def __init__(self, dataset_file: str = "rag_dataset.json"):
        super().__init__(dataset_file)
        self.dataset["metadata"]["hierarchical"] = True
    
    def add_hierarchical_questions(
        self, questions: List[QuestionAnswer], hierarchy_info: Dict
    ) -> None:
        """Add questions with hierarchical context."""
        for qa in questions:
            # Get hierarchy info for this page
            page_hierarchy = hierarchy_info.get(qa.document_url, {})
            
            question_data = {
                "id": str(uuid.uuid4()),  # Add unique UUID
                "document_title": qa.document_title,
                "document_url": qa.document_url,
                "question": qa.question,
                "answer": qa.answer,
                "relevant_chunks": qa.relevant_chunks,
                # Add hierarchical information
                "hierarchy": {
                    "depth": page_hierarchy.get("depth", 0),
                    "parent_id": page_hierarchy.get("parent_id"),
                    "parent_title": page_hierarchy.get("parent_title"),
                    "parent_url": page_hierarchy.get("parent_url"),
                    "child_pages": page_hierarchy.get("child_pages", []),
                    "is_root": page_hierarchy.get("depth", 0) == 0
                }
            }
            self.dataset["questions"].append(question_data)
        
        # Update metadata
        self.dataset["metadata"]["total_questions"] = len(
            self.dataset["questions"]
        )
        self.dataset["metadata"]["total_documents"] = len(set(
            q["document_title"] for q in self.dataset["questions"]
        ))
        
        self._save_dataset()


def generate_hierarchical_questions(
    client: OpenRouterClient, 
    page_data: Dict, 
    hierarchy_info: Dict,
    difficulty_ratio: str = "mixed",
    long_question_ratio: float = 0.2
) -> List[QuestionAnswer]:
    """Generate questions for a page with hierarchy info preserved in metadata."""
    
    # Determine number of questions based on content and hierarchy
    word_count = len(page_data['content'].split())
    depth = page_data.get('depth', 0)
    
    # Adjust question count based on depth and content
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
    
    # Reduce questions for deeper pages to avoid overwhelming
    if depth > 1:
        num_questions = max(1, num_questions - depth)
    
    print(f"  Generating {num_questions} questions for document: "
          f"{page_data['title']} (depth {depth})")
    
    questions_answers = []
    
    for i in range(num_questions):
        print(f"    Generating question {i+1}/{num_questions}...")
        
        # Decide whether to generate a long question based on ratio
        import random
        use_long_question = random.random() < long_question_ratio
        
        if use_long_question and depth > 0:  # Only use long questions for non-root pages
            # For long questions, we need to include parent document(s)
            parent_docs = []
            current_page = page_data
            
            # Add current page
            parent_docs.append({
                'title': current_page['title'],
                'content': current_page['content']
            })
            
            # Add parent pages if available
            if current_page.get('parent_id'):
                # In a real scenario, you'd fetch parent documents
                # For now, we'll use the current page as a proxy
                parent_docs.append({
                    'title': f"Parent: {current_page['title']}",
                    'content': current_page['content'][:1000]  # Use partial content as parent
                })
            
            # Generate long question using multiple documents
            question = client._generate_long_question(
                parent_docs, i+1, difficulty_ratio
            )
        else:
            # Generate regular question using the standard method
            question = client._generate_question(
                page_data['content'], 
                page_data['title'], 
                i+1,
                difficulty_ratio
            )
        
        if not question:
            continue
        
        # Generate answer and find relevant chunks
        answer, relevant_chunks = client._generate_answer_and_chunks(
            page_data['content'], question, 
            client._create_chunks(page_data['content'])
        )
        
        if answer and relevant_chunks:
            qa = QuestionAnswer(
                question=question,
                answer=answer,
                relevant_chunks=relevant_chunks,
                document_title=page_data['title'],
                document_url=page_data['url']
            )
            questions_answers.append(qa)
    
    return questions_answers


def generate_cross_page_questions(
    client: OpenRouterClient, 
    pages: List[Dict], 
    hierarchy_info: Dict
) -> List[QuestionAnswer]:
    """Generate questions that span multiple related pages."""
    
    cross_questions = []
    
    # Find parent-child relationships
    parent_child_groups = {}
    for page in pages:
        if page.get('parent_id'):
            parent_id = page['parent_id']
            if parent_id not in parent_child_groups:
                parent_child_groups[parent_id] = []
            parent_child_groups[parent_id].append(page)
    
    # Generate cross-page questions for groups with multiple children
    for parent_id, children in parent_child_groups.items():
        if len(children) >= 2:  # Only for groups with multiple children
            parent_page = next(
                (p for p in pages if p['page_id'] == parent_id), 
                None
            )
            if not parent_page:
                continue
            
            # Combine content from parent and children
            combined_content = (f"Parent Page: {parent_page['title']}\n"
                              f"{parent_page['content']}\n\nChild Pages:\n")
            
            for child in children:
                combined_content += (f"- {child['title']}: "
                                   f"{child['content'][:500]}...\n\n")
            
            # Generate cross-page question using standard method
            question = client._generate_question(
                combined_content, 
                f"{parent_page['title']} (with children)", 
                1,
                "hard"  # Cross-page questions are typically harder
            )
            
            if question:
                answer, relevant_chunks = client._generate_answer_and_chunks(
                    combined_content, question, 
                    client._create_chunks(combined_content)
                )
                
                if answer and relevant_chunks:
                    qa = QuestionAnswer(
                        question=question,
                        answer=answer,
                        relevant_chunks=relevant_chunks,
                        document_title=f"{parent_page['title']} (with children)",
                        document_url=parent_page['url']
                    )
                    cross_questions.append(qa)
    
    return cross_questions


def export_to_tsv(json_file: str, tsv_file: str = None) -> None:
    """Export RAG dataset from JSON to TSV format."""
    
    # Read JSON file
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file}': {e}")
        return
    
    # Generate TSV filename if not provided
    if not tsv_file:
        tsv_file = json_file.replace('.json', '.tsv')
    
    # Extract questions
    questions = data.get('questions', [])
    if not questions:
        print("Warning: No questions found in the dataset.")
        return
    
    # Define TSV headers
    headers = [
        'Question ID',
        'UUID',
        'Question',
        'Tool Used',
        'Document Name',
        'Chunk Text',
        'Answer/ Facts',
        'URI',
        'Parent URI'
    ]
    
    # Write TSV file
    with open(tsv_file, 'w', encoding='utf-8') as f:
        # Write headers
        f.write('\t'.join(headers) + '\n')
        
        # Write data rows
        for i, q in enumerate(questions, 1):
            hierarchy = q.get('hierarchy', {})
            
            # Prepare chunk text
            chunks = q.get('relevant_chunks', [])
            chunk_text = ' | '.join(chunks).replace('\t', ' ').replace('\n', ' ')
            
            row = [
                str(i),
                q.get('id', ''),  # Include UUID
                q.get('question', '').replace('\t', ' ').replace('\n', ' '),
                'RAG Dataset Generator',
                q.get('document_title', ''),
                chunk_text,
                q.get('answer', '').replace('\t', ' ').replace('\n', ' '),
                q.get('document_url', ''),
                str(hierarchy.get('parent_url', ''))
            ]
            
            f.write('\t'.join(row) + '\n')
    
    print(f"✅ Exported {len(questions)} questions to {tsv_file}")


def generate_rag_dataset(
    urls_file: str,
    dataset_name: str = "rag_dataset",
    output_dir: str = "crawled_pages",
    site_url: str = None,
    email: str = None,
    api_token: str = None,
    openrouter_key: str = None,
    model: str = "google/gemini-2.5-flash",
    max_depth: int = 2,
    max_pages: int = 50,
    months_back: int = 0,
    difficulty_ratio: str = "mixed",
    long_question_ratio: float = 0.2,
    export_tsv: bool = False,
    export_agentic_eval: bool = False,
    language: str = "en"
) -> None:
    """Generate RAG dataset with hierarchical relationships."""
    
    # Create datasets directory
    datasets_dir = "datasets"
    os.makedirs(datasets_dir, exist_ok=True)
    
    dataset_file = os.path.join(datasets_dir, f"{dataset_name}.json")
    
    print("=" * 60)
    print("RAG Dataset Generator with Hierarchical Crawling")
    print("=" * 60)
    
    # Step 1: Crawl Confluence pages
    print("\n📥 Step 1: Crawling Confluence pages...")
    crawled_data = crawl_confluence_pages(
        urls_file=urls_file,
        output_dir=output_dir,
        site_url=site_url,
        email=email,
        api_token=api_token,
        max_depth=max_depth,
        max_pages=max_pages,
        months_back=months_back
    )
    
    if not crawled_data['pages']:
        print("❌ No pages were crawled successfully. Exiting.")
        return
    
    print(f"✅ Crawled {len(crawled_data['pages'])} pages successfully.")
    
    # Step 2: Initialize OpenRouter client and dataset manager
    print("\n🤖 Step 2: Initializing question generation...")
    try:
        client = OpenRouterClient(api_key=openrouter_key, model=model, language=language)
        dataset_manager = HierarchicalDatasetManager(dataset_file)
    except Exception as e:
        print(f"❌ Error initializing OpenRouter client: {e}")
        return
    
    # Step 3: Generate questions for each page with hierarchy context
    print(f"\n❓ Step 3: Generating questions (difficulty: {difficulty_ratio}, language: {language})...")
    total_questions = 0
    
    # Create URL to hierarchy mapping with parent titles
    url_to_hierarchy = {}
    for page in crawled_data['pages']:
        parent_title = None
        if page.get('parent_id'):
            parent_page = next((p for p in crawled_data['pages'] 
                              if p['page_id'] == page['parent_id']), None)
            if parent_page:
                parent_title = parent_page['title']
        
        url_to_hierarchy[page['url']] = {
            'depth': page['depth'],
            'parent_id': page['parent_id'],
            'parent_title': parent_title,
            'parent_url': page['parent_url'],
            'child_pages': page['child_pages']
        }
    
    for i, page in enumerate(crawled_data['pages'], 1):
        print(f"📄 Processing page {i}/{len(crawled_data['pages'])}: {page['title']}")
        
        # Skip pages with very little content
        if len(page['content'].split()) < 100:
            print(f"  ⚠️  Skipping page with insufficient content")
            continue
        
        try:
            # Generate questions for this page with hierarchy context
            questions = generate_hierarchical_questions(
                client, page, url_to_hierarchy[page['url']], difficulty_ratio, long_question_ratio
            )
            
            if questions:
                # Add questions to dataset with hierarchy info
                dataset_manager.add_hierarchical_questions(
                    questions, url_to_hierarchy
                )
                total_questions += len(questions)
                print(f"  ✅ Generated {len(questions)} questions")
            else:
                print("  ⚠️  No questions generated for this page")
                
        except Exception as e:
            print(f"  ❌ Error generating questions: {e}")
            continue
    
    # Step 4: Generate cross-page questions
    print("\n🔗 Step 4: Generating cross-page questions...")
    cross_page_questions = generate_cross_page_questions(
        client, crawled_data['pages'], url_to_hierarchy
    )
    
    if cross_page_questions:
        dataset_manager.add_hierarchical_questions(
            cross_page_questions, url_to_hierarchy
        )
        total_questions += len(cross_page_questions)
        print(f"  ✅ Generated {len(cross_page_questions)} cross-page questions")
    
    # Step 5: Export to TSV if requested
    if export_tsv:
        print(f"\n📊 Exporting to TSV format...")
        tsv_file = os.path.join(datasets_dir, f"{dataset_name}.tsv")
        export_to_tsv(dataset_file, tsv_file)
    
    # Step 6: Export to agentic-eval format if requested
    if export_agentic_eval:
        print(f"\n🤖 Exporting to agentic-eval format...")
        try:
            agentic_eval_file = convert_rag_dataset_to_agentic_eval_format(dataset_file)
            print(f"  ✅ Generated agentic-eval format: {agentic_eval_file}")
        except Exception as e:
            print(f"  ❌ Error generating agentic-eval format: {e}")
    
    # Step 7: Final summary
    print("\n" + "=" * 60)
    print("🎉 RAG Dataset Generation Complete!")
    print("=" * 60)
    
    stats = dataset_manager.get_dataset_stats()
    print(f"📊 Dataset: {dataset_file}")
    print(f"📈 Total questions: {stats['total_questions']}")
    print(f"📄 Total documents: {stats['total_documents']}")
    if export_tsv:
        print(f"📋 TSV export: {os.path.join(datasets_dir, dataset_name)}.tsv")
    if export_agentic_eval:
        print(f"🤖 Agentic-eval export: {os.path.join(datasets_dir, dataset_name)}_agentic_eval.jsonl")


def generate_rag_dataset_from_spaces(
    spaces_file: str,
    dataset_name: str = "rag_dataset",
    output_dir: str = "crawled_pages",
    site_url: str = None,
    email: str = None,
    api_token: str = None,
    openrouter_key: str = None,
    model: str = "google/gemini-2.5-flash",
    max_pages_per_space: int = 20,
    total_max_pages: int = 100,
    random_selection: bool = True,
    months_back: int = 0,
    difficulty_ratio: str = "mixed",
    long_question_ratio: float = 0.2,
    export_tsv: bool = False,
    export_agentic_eval: bool = False,
    language: str = "en"
) -> None:
    """Generate RAG dataset from Confluence spaces with random page selection."""
    
    # Create datasets directory
    datasets_dir = "datasets"
    os.makedirs(datasets_dir, exist_ok=True)
    
    dataset_file = os.path.join(datasets_dir, f"{dataset_name}.json")
    
    print("=" * 60)
    print("RAG Dataset Generator from Confluence Spaces")
    print("=" * 60)
    
    # Step 1: Process Confluence spaces
    print("\n📥 Step 1: Processing Confluence spaces...")
    crawled_data = process_confluence_spaces(
        spaces_file=spaces_file,
        output_dir=output_dir,
        site_url=site_url,
        email=email,
        api_token=api_token,
        max_pages_per_space=max_pages_per_space,
        total_max_pages=total_max_pages,
        random_selection=random_selection,
        months_back=months_back
    )
    
    if not crawled_data['pages']:
        print("❌ No pages were processed successfully. Exiting.")
        return
    
    print(f"✅ Processed {len(crawled_data['pages'])} pages successfully.")
    
    # Step 2: Initialize OpenRouter client and dataset manager
    print("\n🤖 Step 2: Initializing question generation...")
    try:
        client = OpenRouterClient(api_key=openrouter_key, model=model, language=language)
        dataset_manager = HierarchicalDatasetManager(dataset_file)
    except Exception as e:
        print(f"❌ Error initializing OpenRouter client: {e}")
        return
    
    # Step 3: Generate questions for each page with hierarchy context
    print(f"\n❓ Step 3: Generating questions (difficulty: {difficulty_ratio}, language: {language})...")
    total_questions = 0
    
    # Create URL to hierarchy mapping with parent titles
    url_to_hierarchy = {}
    for page in crawled_data['pages']:
        parent_title = None
        if page.get('parent_id'):
            parent_page = next((p for p in crawled_data['pages'] 
                              if p['page_id'] == page['parent_id']), None)
            if parent_page:
                parent_title = parent_page['title']
        
        url_to_hierarchy[page['url']] = {
            'depth': page['depth'],
            'parent_id': page['parent_id'],
            'parent_title': parent_title,
            'parent_url': page['parent_url'],
            'child_pages': page['child_pages']
        }
    
    for i, page in enumerate(crawled_data['pages'], 1):
        print(f"📄 Processing page {i}/{len(crawled_data['pages'])}: {page['title']}")
        
        # Skip pages with very little content
        if len(page['content'].split()) < 100:
            print("  ⚠️  Skipping page with insufficient content")
            continue
        
        try:
            # Generate questions for this page with hierarchy context
            questions = generate_hierarchical_questions(
                client, page, url_to_hierarchy[page['url']], difficulty_ratio, long_question_ratio
            )
            
            if questions:
                # Add questions to dataset with hierarchy info
                dataset_manager.add_hierarchical_questions(
                    questions, url_to_hierarchy
                )
                total_questions += len(questions)
                print(f"  ✅ Generated {len(questions)} questions")
            else:
                print("  ⚠️  No questions generated for this page")
                
        except Exception as e:
            print(f"  ❌ Error generating questions: {e}")
            continue
    
    # Step 4: Generate cross-page questions
    print("\n🔗 Step 4: Generating cross-page questions...")
    cross_page_questions = generate_cross_page_questions(
        client, crawled_data['pages'], url_to_hierarchy
    )
    
    if cross_page_questions:
        dataset_manager.add_hierarchical_questions(
            cross_page_questions, url_to_hierarchy
        )
        total_questions += len(cross_page_questions)
        print(f"  ✅ Generated {len(cross_page_questions)} cross-page questions")
    
    # Step 5: Export to TSV if requested
    if export_tsv:
        print("\n📊 Exporting to TSV format...")
        tsv_file = os.path.join(datasets_dir, f"{dataset_name}.tsv")
        export_to_tsv(dataset_file, tsv_file)
    
    # Step 6: Export to agentic-eval format if requested
    if export_agentic_eval:
        print("\n🤖 Exporting to agentic-eval format...")
        try:
            agentic_eval_file = convert_rag_dataset_to_agentic_eval_format(dataset_file)
            print(f"  ✅ Generated agentic-eval format: {agentic_eval_file}")
        except Exception as e:
            print(f"  ❌ Error generating agentic-eval format: {e}")
    
    # Step 7: Final summary
    print("\n" + "=" * 60)
    print("🎉 RAG Dataset Generation Complete!")
    print("=" * 60)
    
    stats = dataset_manager.get_dataset_stats()
    print(f"📊 Dataset: {dataset_file}")
    print(f"📈 Total questions: {stats['total_questions']}")
    print(f"📄 Total documents: {stats['total_documents']}")
    if export_tsv:
        print(f"📋 TSV export: {os.path.join(datasets_dir, dataset_name)}.tsv")
    if export_agentic_eval:
        print(f"🤖 Agentic-eval export: {os.path.join(datasets_dir, dataset_name)}_agentic_eval.jsonl")


def main():
    parser = argparse.ArgumentParser(
        description="Generate RAG dataset from Confluence pages or spaces"
    )
    parser.add_argument(
        "input_file",
        help="Text file containing Confluence URLs (one per line) or space keys (one per line)"
    )
    parser.add_argument(
        "--mode",
        choices=["urls", "spaces"],
        default="urls",
        help="Mode: 'urls' for crawling specific pages, 'spaces' for random selection from spaces (default: urls)"
    )
    parser.add_argument(
        "--output-dir",
        default="crawled_pages",
        help="Output directory for crawled pages (default: crawled_pages)"
    )
    parser.add_argument(
        "--dataset-name",
        default="rag_dataset",
        help="Name of the output dataset file (default: rag_dataset)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum depth to crawl from starting pages (default: 2, only for URL mode)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum total pages to crawl (default: 50)"
    )
    parser.add_argument(
        "--months-back",
        type=int,
        default=0,
        help="Only crawl pages modified within last N months (0 = no filter, default: 0)"
    )
    parser.add_argument(
        "--max-pages-per-space",
        type=int,
        default=20,
        help="Maximum pages to select from each space (default: 20, only for spaces mode)"
    )
    parser.add_argument(
        "--total-max-pages",
        type=int,
        default=100,
        help="Maximum total pages across all spaces (default: 100, only for spaces mode)"
    )
    parser.add_argument(
        "--no-random-selection",
        action="store_true",
        help="Disable random selection, take first N pages (only for spaces mode)"
    )
    parser.add_argument(
        "--site-url",
        help="Confluence site URL. Can also be set via CONFLUENCE_SITE_URL env var."
    )
    parser.add_argument(
        "--email",
        help="Confluence email. Can also be set via CONFLUENCE_EMAIL env var."
    )
    parser.add_argument(
        "--api-token",
        help="Confluence API token. Can also be set via CONFLUENCE_API_TOKEN env var."
    )
    parser.add_argument(
        "--openrouter-key",
        help="OpenRouter API key. Can also be set via OPENROUTER_API_KEY env var."
    )
    parser.add_argument(
        "--model",
        default="google/gemini-2.5-flash",
        help="OpenRouter model to use (default: google/gemini-2.5-flash)"
    )
    parser.add_argument(
        "--difficulty-ratio",
        default="mixed",
        choices=["easy", "medium", "hard", "mixed", "balanced"],
        help="Difficulty distribution for questions (default: mixed)"
    )
    parser.add_argument(
        "--long-question-ratio",
        type=float,
        default=0.2,
        help="Ratio of long questions to generate (0.0-1.0, default: 0.2)"
    )
    parser.add_argument(
        "--language",
        default="en",
        choices=["en", "de"],
        help="Language for question generation (default: en)"
    )
    parser.add_argument(
        "--export-tsv",
        action="store_true",
        help="Export dataset to TSV format after generation"
    )
    parser.add_argument(
        "--export-agentic-eval",
        action="store_true",
        help="Export dataset to agentic-eval format after generation"
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found.")
        sys.exit(1)
    
    # Get credentials from args or environment variables
    site_url = args.site_url or os.getenv("CONFLUENCE_SITE_URL")
    email = args.email or os.getenv("CONFLUENCE_EMAIL")
    api_token = args.api_token or os.getenv("CONFLUENCE_API_TOKEN")
    openrouter_key = args.openrouter_key or os.getenv("OPENROUTER_API_KEY")
    
    # Validate required credentials
    missing_creds = []
    if not site_url:
        missing_creds.append("Confluence site URL")
    if not email:
        missing_creds.append("Confluence email")
    if not api_token:
        missing_creds.append("Confluence API token")
    if not openrouter_key:
        missing_creds.append("OpenRouter API key")
    
    if missing_creds:
        print("Error: Missing required credentials:")
        for cred in missing_creds:
            print(f"  - {cred}")
        print("\nSet them via command line arguments or environment variables.")
        sys.exit(1)
    
    # Generate the dataset based on mode
    if args.mode == "spaces":
        generate_rag_dataset_from_spaces(
            spaces_file=args.input_file,
            dataset_name=args.dataset_name,
            output_dir=args.output_dir,
            site_url=site_url,
            email=email,
            api_token=api_token,
            openrouter_key=openrouter_key,
            model=args.model,
            max_pages_per_space=args.max_pages_per_space,
            total_max_pages=args.total_max_pages,
            random_selection=not args.no_random_selection,
            months_back=args.months_back,
            difficulty_ratio=args.difficulty_ratio,
            long_question_ratio=args.long_question_ratio,
            export_tsv=args.export_tsv,
            export_agentic_eval=args.export_agentic_eval,
            language=args.language
        )
    else:  # urls mode
        generate_rag_dataset(
            urls_file=args.input_file,
            dataset_name=args.dataset_name,
            output_dir=args.output_dir,
            site_url=site_url,
            email=email,
            api_token=api_token,
            openrouter_key=openrouter_key,
            model=args.model,
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            months_back=args.months_back,
            difficulty_ratio=args.difficulty_ratio,
            long_question_ratio=args.long_question_ratio,
            export_tsv=args.export_tsv,
            export_agentic_eval=args.export_agentic_eval,
            language=args.language
        )


if __name__ == "__main__":
    main() 