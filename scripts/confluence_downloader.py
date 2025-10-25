#!/usr/bin/env python3
"""
Confluence Page Downloader (Download Only)

This script downloads and extracts text content from Confluence pages based on a list of URLs.
This is the download-only version without question generation.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs
import re

from atlassian import Confluence
from bs4 import BeautifulSoup


def get_confluence_client(site_url: str, email: str, api_token: str) -> Confluence:
    """Create and return a Confluence client instance."""
    return Confluence(
        url=site_url,
        username=email,
        password=api_token,
        cloud=True
    )


def extract_page_id_from_url(url: str) -> Optional[str]:
    """Extract the page ID from a Confluence URL."""
    # Handle different URL formats
    # Format 1: https://domain.atlassian.net/wiki/spaces/SPACE/pages/123456/Page+Title
    # Format 2: https://domain.atlassian.net/wiki/pages/viewpage.action?pageId=123456
    # Format 3: https://domain.atlassian.net/wiki/display/SPACE/Page+Title
    
    # Try to extract from path
    path_match = re.search(r'/pages/(\d+)/', url)
    if path_match:
        return path_match.group(1)
    
    # Try to extract from query parameters
    parsed_url = urlparse(url)
    if parsed_url.query:
        query_params = parse_qs(parsed_url.query)
        if 'pageId' in query_params:
            return query_params['pageId'][0]
    
    return None


def extract_full_text_from_html(html: str) -> str:
    """Extract plain text from HTML content while preserving formatting."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Replace <br> tags with newlines
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # Replace block elements with newlines (except <li>)
    for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                             'blockquote', 'pre', 'table']):
        tag.insert_before('\n')
        tag.insert_after('\n')

    # Handle unordered and ordered lists
    for ul in soup.find_all(['ul', 'ol']):
        ul.insert_before('\n')
        ul.insert_after('\n')

    # Handle list items: only insert bullet/number and newline after, not before
    for parent in soup.find_all(['ul', 'ol']):
        is_ol = parent.name == 'ol'
        for idx, li in enumerate(parent.find_all('li', recursive=False), 1):
            if is_ol:
                li.insert_before(f'{idx}. ')
            else:
                li.insert_before('• ')
            li.insert_after('\n')

    # Get text with newlines preserved
    text = soup.get_text()

    # Clean up the text
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
        else:
            # Only add a blank line if the previous line is not blank
            if cleaned_lines and cleaned_lines[-1] != '':
                cleaned_lines.append('')
    # Remove trailing empty lines
    while cleaned_lines and cleaned_lines[-1] == '':
        cleaned_lines.pop()
    return '\n'.join(cleaned_lines)


def get_page_content(client: Confluence, page_id: str) -> Optional[dict]:
    """Get the content of a Confluence page by ID."""
    try:
        # Get page content with body
        page = client.get_page_by_id(page_id, expand='body.view')
        return page
    except Exception as e:
        print(f"Error getting page {page_id}: {e}")
        return None


def sanitize_filename(title: str) -> str:
    """Convert a page title to a safe filename."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', title)
    # Remove extra spaces and limit length
    filename = re.sub(r'\s+', ' ', filename).strip()
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def download_confluence_pages(
    urls_file: str,
    output_dir: str,
    site_url: str,
    email: str,
    api_token: str
) -> list:
    """Download and extract text from Confluence pages listed in the URLs file."""
    
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Initialize Confluence client
    client = get_confluence_client(site_url, email, api_token)
    
    # Read URLs from file
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and 
                   not line.strip().startswith('#')]
    except FileNotFoundError:
        print(f"Error: File '{urls_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{urls_file}': {e}")
        sys.exit(1)
    
    print(f"Found {len(urls)} URLs to process")
    
    successful_downloads = 0
    failed_downloads = 0
    downloaded_pages = []
    
    for i, url in enumerate(urls, 1):
        print(f"\nProcessing {i}/{len(urls)}: {url}")
        
        # Extract page ID from URL
        page_id = extract_page_id_from_url(url)
        if not page_id:
            print(f"  ❌ Could not extract page ID from URL: {url}")
            failed_downloads += 1
            continue
        
        # Get page content
        page = get_page_content(client, page_id)
        if not page:
            print(f"  ❌ Failed to get page content for ID: {page_id}")
            failed_downloads += 1
            continue
        
        # Extract title and content
        title = page.get('title', f'Page_{page_id}')
        body_html = page.get('body', {}).get('view', {}).get('value', '')
        content = extract_full_text_from_html(body_html)
        
        if not content.strip():
            print(f"  ⚠️  No content found for page: {title}")
        
        # Create filename
        safe_title = sanitize_filename(title)
        filename = f"{page_id}_{safe_title}.txt"
        filepath = output_path / filename
        
        # Save content to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Title: {title}\n")
                f.write(f"URL: {url}\n")
                f.write(f"Page ID: {page_id}\n")
                f.write("-" * 80 + "\n\n")
                f.write(content)
            
            print(f"  ✅ Saved: {filename}")
            successful_downloads += 1
            
            # Add to downloaded pages list for question generation
            downloaded_pages.append({
                'title': title,
                'url': url,
                'page_id': page_id,
                'content': content,
                'filepath': str(filepath)
            })
            
        except Exception as e:
            print(f"  ❌ Error saving file: {e}")
            failed_downloads += 1
    
    print("\n" + "="*50)
    print("Download Summary:")
    print(f"  Successful: {successful_downloads}")
    print(f"  Failed: {failed_downloads}")
    print(f"  Total: {len(urls)}")
    print(f"  Output directory: {output_path.absolute()}")
    
    return downloaded_pages


def main():
    parser = argparse.ArgumentParser(
        description="Download and extract text from Confluence pages (download only)"
    )
    parser.add_argument(
        "urls_file",
        help="Text file containing Confluence URLs (one per line)"
    )
    parser.add_argument(
        "--output-dir",
        default="downloaded_pages",
        help="Output directory for downloaded pages (default: downloaded_pages)"
    )
    parser.add_argument(
        "--site-url",
        help="Confluence site URL (e.g., https://your-domain.atlassian.net). "
             "Can also be set via CONFLUENCE_SITE_URL environment variable."
    )
    parser.add_argument(
        "--email",
        help="Confluence email address. Can also be set via CONFLUENCE_EMAIL "
             "environment variable."
    )
    parser.add_argument(
        "--api-token",
        help="Confluence API token. Can also be set via CONFLUENCE_API_TOKEN "
             "environment variable."
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.urls_file):
        print(f"Error: URLs file '{args.urls_file}' not found.")
        sys.exit(1)
    
    # Get credentials from args or environment variables
    site_url = args.site_url or os.getenv("CONFLUENCE_SITE_URL")
    email = args.email or os.getenv("CONFLUENCE_EMAIL")
    api_token = args.api_token or os.getenv("CONFLUENCE_API_TOKEN")
    
    # Validate required credentials
    if not site_url:
        print("Error: Confluence site URL is required. "
              "Set --site-url or CONFLUENCE_SITE_URL environment variable.")
        sys.exit(1)
    
    if not email:
        print("Error: Confluence email is required. "
              "Set --email or CONFLUENCE_EMAIL environment variable.")
        sys.exit(1)
    
    if not api_token:
        print("Error: Confluence API token is required. "
              "Set --api-token or CONFLUENCE_API_TOKEN environment variable.")
        sys.exit(1)
    
    download_confluence_pages(
        urls_file=args.urls_file,
        output_dir=args.output_dir,
        site_url=site_url,
        email=email,
        api_token=api_token
    )


if __name__ == "__main__":
    main() 