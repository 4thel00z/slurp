#!/usr/bin/env python3
"""
Update agentic-eval JSON files with attachments metadata.

This script takes an agentic-eval JSON file containing a list of JSON elements
and updates the "attachments" field from null to include namespace, collection,
and index information.
"""

import argparse
import json
import sys
from pathlib import Path


def update_agentic_eval_attachments(
    input_file: str,
    namespace: str,
    collection: str,
    index: str,
    output_file: str = None
) -> str:
    """
    Update agentic-eval JSON file with attachments metadata.
    
    Args:
        input_file: Path to the input JSON file
        namespace: Namespace for the attachments
        collection: Collection name for the attachments
        index: Index name for the attachments
        output_file: Path to the output JSON file (auto-generated if not
                    provided)
    
    Returns:
        Path to the created JSON file
    """
    # Check if input file exists
    if not Path(input_file).exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Generate output filename if not provided
    if not output_file:
        input_path = Path(input_file)
        # Create new filename with namespace, collection, and index info
        new_filename = (input_path.stem + "_" + namespace + "_" + 
                       collection + "_" + index + ".json")
        output_file = input_path.parent / new_filename
    
    print(f"📖 Reading agentic-eval file: {input_file}")
    print(f"📝 Updating attachments with namespace: '{namespace}', "
          f"collection: '{collection}', index: '{index}'")
    
    updated_count = 0
    total_count = 0
    
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as infile:
        try:
            data = json.load(infile)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}")
    
    # Ensure data is a list
    if not isinstance(data, list):
        raise ValueError("JSON file must contain a list of JSON elements")
    
    # Update each element in the list
    for i, json_obj in enumerate(data):
        total_count += 1
        
        # Update the attachments field
        if 'attachments' in json_obj:
            # Replace null with the new attachments structure
            json_obj['attachments'] = {
                "collection": collection,
                "namespace": namespace,
                "index": index
            }
            updated_count += 1
        else:
            print(f"⚠️  Warning: Element {i+1} missing 'attachments' field")
    
    # Write the updated JSON file
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=2)
    
    print(f"✅ Successfully updated {updated_count}/{total_count} records")
    print(f"💾 Output saved to: {output_file}")
    
    return str(output_file)


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Update agentic-eval JSON files with attachments metadata"
    )
    parser.add_argument(
        "input_file",
        help="Path to the input agentic-eval JSON file"
    )
    parser.add_argument(
        "namespace",
        help="Namespace for the attachments (e.g., 'Assistant')"
    )
    parser.add_argument(
        "collection",
        help="Collection name for the attachments "
             "(e.g., 'Assistant-File-Upload-Collection-QA-dir00001-"
             "internal-EN')"
    )
    parser.add_argument(
        "index",
        help="Index name for the attachments (e.g., 'Pottery')"
    )
    parser.add_argument(
        "--output-file",
        help="Path to the output JSON file (auto-generated if not provided)"
    )
    
    args = parser.parse_args()
    
    try:
        output_file = update_agentic_eval_attachments(
            input_file=args.input_file,
            namespace=args.namespace,
            collection=args.collection,
            index=args.index,
            output_file=args.output_file
        )
        
        print("\n🎉 Successfully updated agentic-eval file!")
        print(f"📊 Output file: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 