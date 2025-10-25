#!/usr/bin/env python3
"""
Confluence Crawler with Sub-page Discovery

This script crawls Confluence pages starting from URLs in a file, discovers sub-pages
by following links, and creates a hierarchical dataset with parent-child relationships.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
from urllib.parse import urlparse, parse_qs, urljoin
import re
import time
from collections import deque
from datetime import datetime, timedelta

from atlassian import Confluence
from bs4 import BeautifulSoup


class ConfluenceCrawler:
    """Crawls Confluence pages and discovers sub-pages."""
    
    def __init__(self, site_url: str, email: str, api_token: str):
        self.site_url = site_url
        self.client = Confluence(
            url=site_url,
            username=email,
            password=api_token,
            cloud=True
        )
        self.visited_pages = set()
        self.page_hierarchy = {}
        self.page_content = {}
    
    def _is_page_recently_modified(self, page: Dict, months_back: int) -> bool:
        """
        Check if a page was modified within the last N months.
        
        Args:
            page: Page dictionary from Confluence API
            months_back: Number of months to look back
            
        Returns:
            True if page was modified within the specified timeframe
        """
        if not months_back or months_back <= 0:
            return True  # No filtering if months_back is 0 or negative
        
        # Try multiple possible date field locations
        last_modified = None
        
        # Method 1: Check version.when
        if page.get('version', {}).get('when'):
            last_modified = page['version']['when']
        # Method 2: Check lastModified.when
        elif page.get('lastModified', {}).get('when'):
            last_modified = page['lastModified']['when']
        # Method 3: Check history.lastUpdated.when
        elif page.get('history', {}).get('lastUpdated', {}).get('when'):
            last_modified = page['history']['lastUpdated']['when']
        # Method 4: Check _expandable.lastModified
        elif page.get('_expandable', {}).get('lastModified'):
            last_modified = page['_expandable']['lastModified']
        # Method 5: Check created date as fallback
        elif page.get('created', {}).get('when'):
            last_modified = page['created']['when']
        
        if not last_modified:
            print(f"    ⚠️  Could not determine last modified date for page {page.get('id')}")
            print(f"        Available date fields: {list(page.keys())}")
            if 'version' in page:
                print(f"        Version fields: {list(page['version'].keys())}")
            if 'history' in page:
                print(f"        History fields: {list(page['history'].keys())}")
            return True  # Include page if we can't determine the date
        
        try:
            # Handle different date formats
            if isinstance(last_modified, str):
                # Remove timezone 'Z' and replace with proper timezone
                if last_modified.endswith('Z'):
                    last_modified = last_modified[:-1] + '+00:00'
                
                # Parse the date string (Confluence uses ISO format)
                modified_date = datetime.fromisoformat(last_modified)
            else:
                # If it's already a datetime object
                modified_date = last_modified
            
            # Calculate cutoff date
            cutoff_date = datetime.now(modified_date.tzinfo) - timedelta(days=months_back * 30)
            
            is_recent = modified_date >= cutoff_date
            if not is_recent:
                print(f"    ⏰ Skipping page '{page.get('title', 'Unknown')}' - "
                      f"last modified {modified_date.strftime('%Y-%m-%d')} "
                      f"(older than {months_back} months)")
            
            return is_recent
            
        except (ValueError, TypeError) as e:
            print(f"    ⚠️  Error parsing date '{last_modified}' for page {page.get('id')}: {e}")
            return True  # Include page if date parsing fails
    
    def extract_page_id_from_url(self, url: str) -> Optional[str]:
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
    
    def get_page_content(self, page_id: str) -> Optional[dict]:
        """Get the content of a Confluence page by ID."""
        try:
            # Get page content with body and links
            page = self.client.get_page_by_id(page_id, expand='body.view,body.storage')
            return page
        except Exception as e:
            print(f"Error getting page {page_id}: {e}")
            return None
    
    def extract_links_from_html(self, html: str, base_url: str) -> List[str]:
        """Extract Confluence page links from HTML content."""
        if not html:
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        links = []
        
        # Find all anchor tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                continue
            
            # Only include Confluence page links
            if self._is_confluence_page_url(full_url):
                links.append(full_url)
        
        return list(set(links))  # Remove duplicates
    
    def _is_confluence_page_url(self, url: str) -> bool:
        """Check if URL is a Confluence page URL."""
        confluence_patterns = [
            r'/wiki/spaces/[^/]+/pages/\d+',
            r'/wiki/pages/viewpage\.action\?pageId=\d+',
            r'/wiki/display/[^/]+/[^/]+'
        ]
        
        for pattern in confluence_patterns:
            if re.search(pattern, url):
                return True
        return False
    
    def extract_full_text_from_html(self, html: str) -> str:
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
    
    def crawl_pages(self, start_urls: List[str], max_depth: int = 2, 
                   max_pages: int = 50, months_back: int = 0) -> Dict[str, any]:
        """Crawl Confluence pages starting from the given URLs."""
        
        print(f"🚀 Starting crawl with max_depth={max_depth}, max_pages={max_pages}")
        if months_back > 0:
            print(f"📅 Filtering pages modified within last {months_back} months")
        print(f"📋 Starting URLs: {len(start_urls)}")
        
        # Queue of (url, depth, parent_id) tuples
        queue = deque()
        for url in start_urls:
            page_id = self.extract_page_id_from_url(url)
            if page_id:
                queue.append((url, 0, None, page_id))
        
        crawled_pages = []
        page_count = 0
        
        while queue and page_count < max_pages:
            url, depth, parent_id, page_id = queue.popleft()
            
            # Skip if already visited
            if page_id in self.visited_pages:
                continue
            
            print(f"\n📄 Crawling page {page_count + 1}/{max_pages} (depth {depth}): {url}")
            
            # Get page content
            page = self.get_page_content(page_id)
            if not page:
                continue
            
            # Check if page was recently modified (if filtering is enabled)
            if months_back > 0 and not self._is_page_recently_modified(page, months_back):
                continue
            
            # Extract page info
            title = page.get('title', f'Page_{page_id}')
            body_html = page.get('body', {}).get('view', {}).get('value', '')
            content = self.extract_full_text_from_html(body_html)
            
            # Skip pages with insufficient content
            if len(content.split()) < 50:
                print("  ⚠️  Skipping page with insufficient content")
                continue
            
            # Mark as visited
            self.visited_pages.add(page_id)
            page_count += 1
            
            # Store page data
            page_data = {
                'page_id': page_id,
                'title': title,
                'url': url,
                'content': content,
                'depth': depth,
                'parent_id': parent_id,
                'parent_url': None,
                'child_pages': []
            }
            
            # Set parent URL if exists
            if parent_id and parent_id in self.page_hierarchy:
                page_data['parent_url'] = self.page_hierarchy[parent_id]['url']
            
            self.page_hierarchy[page_id] = page_data
            crawled_pages.append(page_data)
            
            # Add to parent's child list
            if parent_id and parent_id in self.page_hierarchy:
                self.page_hierarchy[parent_id]['child_pages'].append(page_id)
            
            print(f"  ✅ Crawled: {title}")
            
            # Discover sub-pages if not at max depth
            if depth < max_depth:
                sub_links = self.extract_links_from_html(body_html, url)
                print(f"  🔗 Found {len(sub_links)} potential sub-links")
                
                for sub_url in sub_links:
                    sub_page_id = self.extract_page_id_from_url(sub_url)
                    if sub_page_id and sub_page_id not in self.visited_pages:
                        queue.append((sub_url, depth + 1, page_id, sub_page_id))
            
            # Rate limiting
            time.sleep(0.5)
        
        print(f"\n🎉 Crawl complete! Crawled {len(crawled_pages)} pages")
        return {
            'pages': crawled_pages,
            'hierarchy': self.page_hierarchy,
            'stats': {
                'total_pages': len(crawled_pages),
                'max_depth_reached': max(d['depth'] for d in crawled_pages) if crawled_pages else 0,
                'pages_with_children': len([p for p in crawled_pages if p['child_pages']])
            }
        }
    
    def save_crawled_pages(self, output_dir: str, crawled_data: Dict) -> None:
        """Save crawled pages to files with hierarchy information."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        pages = crawled_data['pages']
        
        for page in pages:
            # Create filename
            safe_title = self._sanitize_filename(page['title'])
            filename = f"{page['page_id']}_{safe_title}.txt"
            filepath = output_path / filename
            
            # Write content with hierarchy info
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Title: {page['title']}\n")
                f.write(f"URL: {page['url']}\n")
                f.write(f"Page ID: {page['page_id']}\n")
                f.write(f"Depth: {page['depth']}\n")
                
                if page['parent_id']:
                    f.write(f"Parent ID: {page['parent_id']}\n")
                    if page['parent_url']:
                        f.write(f"Parent URL: {page['parent_url']}\n")
                
                if page['child_pages']:
                    f.write(f"Child Pages: {', '.join(page['child_pages'])}\n")
                
                f.write("-" * 80 + "\n\n")
                f.write(page['content'])
            
            print(f"  💾 Saved: {filename}")
    
    def _sanitize_filename(self, title: str) -> str:
        """Convert a page title to a safe filename."""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        # Remove extra spaces and limit length
        filename = re.sub(r'\s+', ' ', filename).strip()
        if len(filename) > 100:
            filename = filename[:100]
        return filename
    
    def get_space_pages(self, space_key: str, max_pages: int = 50, 
                       random_selection: bool = True, months_back: int = 0) -> List[Dict]:
        """
        Get all pages in a space and optionally randomly select a subset.
        
        Args:
            space_key: The Confluence space key
            max_pages: Maximum number of pages to return
            random_selection: Whether to randomly select pages or take first N
            months_back: Only include pages modified within last N months (0 = no filter)
            
        Returns:
            List of page dictionaries with hierarchy information
        """
        try:
            print(f"🔍 Fetching pages from space: {space_key}")
            if months_back > 0:
                print(f"📅 Filtering pages modified within last {months_back} months")
            
            # Get all pages in the space
            all_pages = self.client.get_all_pages_from_space(
                space_key, start=0, limit=1000, 
                expand='version,history,lastModified'
            )
            
            if not all_pages:
                print(f"⚠️  No pages found in space: {space_key}")
                return []
            
            print(f"📄 Found {len(all_pages)} pages in space {space_key}")
            
            # Filter by date if specified
            if months_back > 0:
                original_count = len(all_pages)
                all_pages = [page for page in all_pages 
                           if self._is_page_recently_modified(page, months_back)]
                print(f"📅 After date filtering: {len(all_pages)} pages "
                      f"(filtered out {original_count - len(all_pages)} pages)")
            
            # Convert to our format and add hierarchy info
            pages_with_hierarchy = []
            page_id_to_info = {}
            
            # First pass: create mapping of page IDs to info
            for page in all_pages:
                page_id = page.get('id')
                if page_id:
                    page_id_to_info[page_id] = {
                        'id': page_id,
                        'title': page.get('title', ''),
                        'url': page.get('_links', {}).get('webui', ''),
                        'parent_id': page.get('ancestors', [{}])[-1].get('id') if page.get('ancestors') else None,
                        'depth': len(page.get('ancestors', [])),
                        'children': []
                    }
            
            # Second pass: build parent-child relationships
            for page_id, page_info in page_id_to_info.items():
                parent_id = page_info['parent_id']
                if parent_id and parent_id in page_id_to_info:
                    page_id_to_info[parent_id]['children'].append(page_id)
            
            # Convert to list
            pages_with_hierarchy = list(page_id_to_info.values())
            
            # Random selection if requested
            if random_selection and len(pages_with_hierarchy) > max_pages:
                import random
                selected_pages = random.sample(pages_with_hierarchy, max_pages)
                print(f"🎲 Randomly selected {max_pages} pages from {len(pages_with_hierarchy)} total pages")
            else:
                selected_pages = pages_with_hierarchy[:max_pages]
                print(f"📋 Selected first {len(selected_pages)} pages")
            
            # Sort by depth to ensure parents come before children
            selected_pages.sort(key=lambda x: x['depth'])
            
            return selected_pages
            
        except Exception as e:
            print(f"❌ Error fetching pages from space {space_key}: {e}")
            return []
    
    def get_multiple_space_pages(self, space_keys: List[str], max_pages_per_space: int = 20,
                                total_max_pages: int = 100, random_selection: bool = True,
                                months_back: int = 0) -> List[Dict]:
        """
        Get pages from multiple spaces with random selection.
        
        Args:
            space_keys: List of Confluence space keys
            max_pages_per_space: Maximum pages to select from each space
            total_max_pages: Maximum total pages across all spaces
            random_selection: Whether to randomly select pages
            months_back: Only include pages modified within last N months (0 = no filter)
            
        Returns:
            List of page dictionaries with hierarchy information
        """
        all_pages = []
        
        for space_key in space_keys:
            space_pages = self.get_space_pages(space_key, max_pages_per_space, 
                                             random_selection, months_back)
            all_pages.extend(space_pages)
            
            if len(all_pages) >= total_max_pages:
                all_pages = all_pages[:total_max_pages]
                break
        
        print(f"📊 Total pages collected from {len(space_keys)} spaces: {len(all_pages)}")
        return all_pages


def crawl_confluence_pages(
    urls_file: str,
    output_dir: str,
    site_url: str,
    email: str,
    api_token: str,
    max_depth: int = 2,
    max_pages: int = 50,
    months_back: int = 0
) -> Dict:
    """Main function to crawl Confluence pages."""
    
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
    
    print(f"Found {len(urls)} starting URLs")
    
    # Initialize crawler
    crawler = ConfluenceCrawler(site_url, email, api_token)
    
    # Crawl pages
    crawled_data = crawler.crawl_pages(urls, max_depth, max_pages, months_back)
    
    # Save pages
    print(f"\n💾 Saving crawled pages to {output_dir}...")
    crawler.save_crawled_pages(output_dir, crawled_data)
    
    # Print statistics
    stats = crawled_data['stats']
    print(f"\n📈 Crawl Statistics:")
    print(f"  Total pages crawled: {stats['total_pages']}")
    print(f"  Maximum depth reached: {stats['max_depth_reached']}")
    print(f"  Pages with children: {stats['pages_with_children']}")
    
    return crawled_data


def process_confluence_spaces(
    spaces_file: str,
    output_dir: str,
    site_url: str,
    email: str,
    api_token: str,
    max_pages_per_space: int = 20,
    total_max_pages: int = 100,
    random_selection: bool = True,
    months_back: int = 0
) -> Dict:
    """
    Process Confluence spaces to get pages with hierarchy information.
    
    Args:
        spaces_file: Text file containing space keys (one per line)
        output_dir: Directory to save crawled pages
        site_url: Confluence site URL
        email: Confluence email
        api_token: Confluence API token
        max_pages_per_space: Maximum pages to select from each space
        total_max_pages: Maximum total pages across all spaces
        random_selection: Whether to randomly select pages
        months_back: Only include pages modified within last N months (0 = no filter)
        
    Returns:
        Dictionary containing crawled pages and hierarchy information
    """
    # Read space keys from file
    try:
        with open(spaces_file, 'r', encoding='utf-8') as f:
            space_keys = [stripped_line for line in f if (stripped_line :=line.strip())]
    except FileNotFoundError:
        print(f"❌ Error: Spaces file '{spaces_file}' not found.")
        return {"pages": [], "hierarchy": {}}
    
    if not space_keys:
        print("❌ No space keys found in the file.")
        return {"pages": [], "hierarchy": {}}
    
    print(f"📋 Processing {len(space_keys)} spaces: {', '.join(space_keys)}")
    
    # Initialize crawler
    crawler = ConfluenceCrawler(site_url, email, api_token)
    
    # Get pages from all spaces
    pages_with_hierarchy = crawler.get_multiple_space_pages(
        space_keys, max_pages_per_space, total_max_pages, random_selection, months_back
    )
    
    if not pages_with_hierarchy:
        print("❌ No pages found in any of the specified spaces.")
        return {"pages": [], "hierarchy": {}}
    
    # Download content for each page
    crawled_pages = []
    hierarchy_info = {}
    
    print(f"\n📥 Downloading content for {len(pages_with_hierarchy)} pages...")
    
    for i, page_info in enumerate(pages_with_hierarchy, 1):
        page_id = page_info['id']
        print(f"  📄 Downloading {i}/{len(pages_with_hierarchy)}: {page_info['title']}")
        
        # Get page content
        page_content = crawler.get_page_content(page_id)
        if not page_content:
            print(f"    ⚠️  Failed to get content for page {page_id}")
            continue
        
        # Extract content
        body_html = page_content.get('body', {}).get('view', {}).get('value', '')
        content = crawler.extract_full_text_from_html(body_html)
        
        # Skip pages with insufficient content
        if len(content.split()) < 50:
            print("  ⚠️  Skipping page with insufficient content")
            continue
        
        # Create page data
        page_data = {
            'page_id': page_id,
            'title': page_info['title'],
            'url': page_info['url'],
            'content': content,
            'depth': page_info['depth'],
            'parent_id': page_info['parent_id'],
            'parent_url': None,  # Will be filled in next step
            'child_pages': page_info['children']
        }
        
        crawled_pages.append(page_data)
        
        # Add to hierarchy info
        hierarchy_info[page_info['url']] = {
            'depth': page_info['depth'],
            'parent_id': page_info['parent_id'],
            'parent_url': None,
            'child_pages': page_info['children']
        }
    
    # Fill in parent URLs
    page_id_to_url = {page['page_id']: page['url'] for page in crawled_pages}
    for page in crawled_pages:
        if page['parent_id'] and page['parent_id'] in page_id_to_url:
            page['parent_url'] = page_id_to_url[page['parent_id']]
            hierarchy_info[page['url']]['parent_url'] = page_id_to_url[page['parent_id']]
    
    # Save crawled pages
    crawler.save_crawled_pages(output_dir, {
        'pages': crawled_pages,
        'hierarchy': hierarchy_info,
        'metadata': {
            'total_pages': len(crawled_pages),
            'spaces_processed': space_keys,
            'max_pages_per_space': max_pages_per_space,
            'total_max_pages': total_max_pages,
            'random_selection': random_selection,
            'months_back': months_back
        }
    })
    
    print(f"\n✅ Successfully processed {len(crawled_pages)} pages from {len(space_keys)} spaces")
    
    return {
        'pages': crawled_pages,
        'hierarchy': hierarchy_info,
        'metadata': {
            'total_pages': len(crawled_pages),
            'spaces_processed': space_keys,
            'max_pages_per_space': max_pages_per_space,
            'total_max_pages': total_max_pages,
            'random_selection': random_selection,
            'months_back': months_back
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description="Crawl Confluence pages and discover sub-pages"
    )
    parser.add_argument(
        "urls_file",
        help="Text file containing starting Confluence URLs (one per line)"
    )
    parser.add_argument(
        "--output-dir",
        default="crawled_pages",
        help="Output directory for crawled pages (default: crawled_pages)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum depth to crawl from starting pages (default: 2)"
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
    missing_creds = []
    if not site_url:
        missing_creds.append("Confluence site URL")
    if not email:
        missing_creds.append("Confluence email")
    if not api_token:
        missing_creds.append("Confluence API token")
    
    if missing_creds:
        print("Error: Missing required credentials:")
        for cred in missing_creds:
            print(f"  - {cred}")
        print("\nSet them via command line arguments or environment variables.")
        sys.exit(1)
    
    # Crawl pages
    crawl_confluence_pages(
        urls_file=args.urls_file,
        output_dir=args.output_dir,
        site_url=site_url,
        email=email,
        api_token=api_token,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        months_back=args.months_back
    )


if __name__ == "__main__":
    main() 