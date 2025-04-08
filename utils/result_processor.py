import re
from decimal import Decimal
from urllib.parse import urlparse
import math

# Define a large number to use instead of infinity for JSON serialization
MAX_PRICE = 999999.99

def process_results(results, format_filter='all'):
    """
    Process and format search results from different sources
    
    Args:
        results (dict): Dictionary of results from different sources
        format_filter (str): Filter results by format (all, paperback, hardcover, ebook, audiobook)
        
    Returns:
        dict: Processed and formatted results
    """
    all_results = []
    
    # Print total result counts by source
    print("\n=== PROCESSING RESULTS ===")
    for source, source_results in results.items():
        print(f"{source}: {len(source_results)} results")
    
    # Combine results from all sources
    for source, source_results in results.items():
        for result in source_results:
            # Ensure all required fields exist
            if 'title' not in result or not result['title']:
                continue
                
            # Validate and fix links
            result['link'] = validate_link(result.get('link', '#'))
            
            # Debug each result link - handle encoding safely
            try:
                safe_title = str(result.get('title', 'Unknown')[:30]).encode('ascii', 'replace').decode('ascii')
                print(f"Link from {source} for '{safe_title}...': {result.get('link', 'No link')}")
            except Exception as e:
                print(f"Error logging title from {source}: {str(e)}")
            
            # Ensure source is properly set
            result['source'] = source if 'source' not in result or not result['source'] else result['source']
                
            # Add result to the combined list
            all_results.append(result)
    
    # Apply format filter if specified
    if format_filter and format_filter.lower() != 'all':
        filtered_results = {}
        for source, source_results in results.items():
            filtered_source_results = []
            for result in source_results:
                result_format = result.get('format', '').lower()
                if result_format and format_filter.lower() in result_format.lower():
                    filtered_source_results.append(result)
            filtered_results[source] = filtered_source_results
        results = filtered_results
    
    # Standardize prices for comparison
    standardize_prices(all_results)
    
    # Group results by book (based on title similarity)
    grouped_results = group_by_book(all_results)
    
    # Find best price for each book
    for book_group in grouped_results:
        find_best_price(book_group['sources'])
        
    # Verify final results have links
    print("\n=== FINAL GROUPED RESULTS ===")
    for i, group in enumerate(grouped_results):
        print(f"Group {i+1}: {group['title']}")
        for j, source in enumerate(group['sources']):
            print(f"  Source {j+1}: {source['source']} - Price: {source.get('price', 'No Price')} - Link: {source.get('link', 'No Link')}")
    
    return sanitize_json_values({
        'results': grouped_results,
        'count': len(grouped_results),
        'format_filter': format_filter
    })

def sanitize_json_values(data):
    """Recursively process data to ensure all values are JSON serializable"""
    if isinstance(data, dict):
        return {k: sanitize_json_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json_values(item) for item in data]
    elif isinstance(data, float) and (math.isinf(data) or math.isnan(data)):
        return "N/A"  # Replace infinity and NaN with a string
    else:
        return data

def standardize_prices(results):
    """
    Standardize prices for comparison
    
    Args:
        results (list): List of result dictionaries to standardize
    """
    for result in results:
        if 'price' not in result or not result['price']:
            result['price'] = 'Price not available'
            result['price_value'] = float('inf')
            continue
            
        # Extract price value if it's a string
        if isinstance(result['price'], str):
            # Try to extract numeric price value using regex
            price_match = re.search(r'[\$£€]?\s*(\d+[.,]\d+|\d+)', result['price'])
            
            if price_match:
                # Extract price value and remove non-numeric characters except decimal
                price_str = price_match.group(1).replace(',', '.')
                try:
                    # Convert price to float for comparison
                    price_value = float(price_str)
                    
                    # Ensure price is never 0
                    if price_value == 0 or price_value < 0.01:
                        result['price'] = 'Price not available'
                        result['price_value'] = float('inf')
                    else:
                        # Format price consistently with Rupee symbol
                        result['price'] = f"₹{price_value:.2f}"
                        result['price_value'] = price_value
                except ValueError:
                    result['price'] = 'Price not available'
                    result['price_value'] = float('inf')
            else:
                result['price'] = 'Price not available'
                result['price_value'] = float('inf')
        elif isinstance(result['price'], (int, float)):
            # Handle numeric prices
            price_value = float(result['price'])
            
            # Ensure price is never 0
            if price_value == 0 or price_value < 0.01:
                result['price'] = 'Price not available'
                result['price_value'] = float('inf')
            else:
                # Format price consistently with Rupee symbol
                result['price'] = f"₹{price_value:.2f}"
                result['price_value'] = price_value
        else:
            result['price'] = 'Price not available'
            result['price_value'] = float('inf')

def validate_link(link):
    """
    Validate and normalize link URL
    
    Args:
        link (str): Link URL to validate
        
    Returns:
        str: Validated and normalized link or '#' if invalid
    """
    if not link or not isinstance(link, str) or link == '#':
        return '#'
        
    # Remove whitespace
    link = link.strip()
    
    # Check if it's a valid URL
    try:
        # If it doesn't start with http or https, add https://
        if not link.startswith(('http://', 'https://')):
            if link.startswith('//'):
                link = 'https:' + link
            else:
                link = 'https://' + link
                
        # Try parsing the URL to validate it
        result = urlparse(link)
        if not all([result.scheme, result.netloc]):
            return '#'
            
        return link
    except Exception:
        return '#'

def group_by_book(results):
    """
    Group results by book based on title similarity
    
    Args:
        results (list): List of result dictionaries
        
    Returns:
        list: List of grouped results
    """
    grouped = []
    processed_indices = set()
    
    for i, result in enumerate(results):
        if i in processed_indices:
            continue
        
        title = result.get('title', '').lower()
        author = result.get('author', '').lower()
        
        # Create a new group
        group = {
            'title': result.get('title', ''),
            'author': result.get('author', ''),
            'image_url': result.get('image_url', ''),
            'sources': [result]
        }
        processed_indices.add(i)
        
        # Find similar books
        for j, other_result in enumerate(results):
            if j in processed_indices:
                continue
            
            other_title = other_result.get('title', '').lower()
            other_author = other_result.get('author', '').lower()
            
            # Check if titles are similar
            if title_similarity(title, other_title) > 0.8 and author_similarity(author, other_author) > 0.6:
                group['sources'].append(other_result)
                processed_indices.add(j)
                
                # Use the best image (prefer higher resolution)
                if len(other_result.get('image_url', '')) > len(group['image_url']):
                    group['image_url'] = other_result.get('image_url', '')
        
        grouped.append(group)
    
    return grouped

def title_similarity(title1, title2):
    """
    Calculate similarity between two book titles
    
    Args:
        title1 (str): First title
        title2 (str): Second title
        
    Returns:
        float: Similarity score between 0 and 1
    """
    # Remove common words and punctuation
    words1 = set(re.sub(r'[^\w\s]', '', title1).lower().split())
    words2 = set(re.sub(r'[^\w\s]', '', title2).lower().split())
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
    words1 = words1 - stop_words
    words2 = words2 - stop_words
    
    if not words1 or not words2:
        return 0
    
    # Calculate Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0

def author_similarity(author1, author2):
    """
    Calculate similarity between two author names
    
    Args:
        author1 (str): First author
        author2 (str): Second author
        
    Returns:
        float: Similarity score between 0 and 1
    """
    # Handle "Unknown Author" case
    if author1 == 'unknown author' or author2 == 'unknown author':
        return 0.5
    
    # Remove titles and punctuation
    author1 = re.sub(r'(dr\.|mr\.|mrs\.|ms\.|prof\.)', '', author1.lower())
    author2 = re.sub(r'(dr\.|mr\.|mrs\.|ms\.|prof\.)', '', author2.lower())
    
    # Split into words
    words1 = author1.split()
    words2 = author2.split()
    
    if not words1 or not words2:
        return 0
    
    # Check if last names match
    if words1[-1] == words2[-1]:
        return 1.0
    
    # Calculate word overlap
    common_words = sum(1 for word in words1 if word in words2)
    total_words = len(set(words1 + words2))
    
    return common_words / total_words if total_words > 0 else 0

def find_best_price(sources):
    """
    Find the best price among sources and mark it
    
    Args:
        sources (list): List of source dictionaries
    """
    min_price = MAX_PRICE
    min_price_index = -1
    
    # Find minimum price
    for i, source in enumerate(sources):
        price_value = source.get('price_value', MAX_PRICE)
        
        # Skip if price is not available
        if price_value == MAX_PRICE:
            continue
        
        if price_value < min_price:
            min_price = price_value
            min_price_index = i
    
    # Mark the best price
    for i, source in enumerate(sources):
        source['best_price'] = (i == min_price_index)
