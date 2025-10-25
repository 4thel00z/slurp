import pandas as pd
import json
import uuid
from pathlib import Path


def convert_tsv_to_agentic_eval_format(tsv_file: str, 
                                      output_file: str = None) -> str:
    """
    Convert TSV evaluation dataset to agentic-eval JSON format.
    
    Args:
        tsv_file: Path to the input TSV file
        output_file: Path to the output JSON file (default: input_file.json)
    
    Returns:
        Path to the created JSON file
    """
    # Set output file path
    if output_file:
        json_output_file = output_file
    else:
        # Use input filename with .json extension
        input_path = Path(tsv_file)
        json_output_file = input_path.with_suffix('.json')
    
    # Check if input file exists
    if not Path(tsv_file).exists():
        raise FileNotFoundError(f"Input file not found at {tsv_file}")
    
    print(f"Reading data from: {tsv_file}")
    df = pd.read_csv(tsv_file, sep='\t')
    
    # Convert DataFrame to JSON format
    json_data = []
    
    for _, row in df.iterrows():
        # Extract question and answer
        question = row['Question']
        answer_facts = row['Answer/ Facts']
        
        # Split answer facts into list (assuming they are separated by delimiter)
        if isinstance(answer_facts, str):
            # Try to split by common delimiters or treat as single fact
            if '===' in answer_facts:
                facts_list = [fact.strip() for fact in answer_facts.split('===') 
                             if fact.strip()]
            else:
                # If no delimiter found, treat as single fact
                facts_list = ([answer_facts.strip()] 
                             if answer_facts.strip() else [])
        else:
            facts_list = [str(answer_facts)]
        
        # Create JSON object with new format
        json_obj = {
            "input": {
                "objective": question,
                "max_turns": 5,
                "attachment": None
            },
            "expected_output": {
                "expected_facts": facts_list
            },
            "id": str(uuid.uuid4()),
            "metadata": None
        }
        
        json_data.append(json_obj)
    
    # Save to JSON file
    print(f"Saving output to: {json_output_file}")
    with open(json_output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_output_file


def convert_rag_dataset_to_agentic_eval_format(rag_dataset_file: str,
                                              output_file: str = None) -> str:
    """
    Convert RAG dataset JSON to agentic-eval JSONL format.
    
    Each line in the output file contains a single JSON object with:
    - input: Contains objective, max_turns, and attachment
    - expected_output: Contains expected_facts
    - id: Unique UUID for each sample
    - metadata: Additional metadata (currently None)
    
    Args:
        rag_dataset_file: Path to the RAG dataset JSON file
        output_file: Path to the output JSONL file 
                    (default: rag_dataset_agentic_eval.jsonl in datasets dir)
    
    Returns:
        Path to the created JSONL file
    """
    # Set output file path
    if output_file:
        jsonl_output_file = output_file
    else:
        # Use input filename with agentic_eval suffix and .jsonl extension
        input_path = Path(rag_dataset_file)
        # Create datasets directory if it doesn't exist
        datasets_dir = Path("datasets")
        datasets_dir.mkdir(exist_ok=True)
        jsonl_output_file = datasets_dir / f"{input_path.stem}_agentic_eval.jsonl"
    
    # Check if input file exists
    if not Path(rag_dataset_file).exists():
        raise FileNotFoundError(f"RAG dataset file not found at {rag_dataset_file}")
    
    print(f"Reading RAG dataset from: {rag_dataset_file}")
    
    # Read RAG dataset
    with open(rag_dataset_file, 'r', encoding='utf-8') as f:
        rag_data = json.load(f)
    
    # Convert to agentic-eval format and write as JSONL
    print(f"Saving agentic-eval format to: {jsonl_output_file}")
    
    with open(jsonl_output_file, 'w', encoding='utf-8') as f:
        for question_data in rag_data.get('questions', []):
            question = question_data.get('question', '')
            answer = question_data.get('answer', '')
            
            # Split answer into facts (using chunk separators or treating as single fact)
            if isinstance(answer, str):
                if '===' in answer:
                    facts_list = [fact.strip() for fact in answer.split('===')
                                 if fact.strip()]
                else:
                    # If no delimiter found, treat as single fact
                    facts_list = [answer.strip()] if answer.strip() else []
            else:
                facts_list = [str(answer)]
            
            # Create JSON object with new format
            json_obj = {
                "input": {
                    "objective": question,
                    "max_turns": 5,
                    "attachment": None
                },
                "expected_output": {
                    "expected_facts": facts_list
                },
                "id": str(uuid.uuid4()),
                "metadata": None
            }
            
            # Write as JSONL (one JSON object per line)
            f.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
    
    return jsonl_output_file










