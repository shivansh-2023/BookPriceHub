from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
import concurrent.futures
from flask_cors import CORS
from scrapers.amazon import AmazonScraper
from scrapers.barnes_noble import BarnesNobleScraper
from scrapers.book_depository import BookDepositoryScraper
from scrapers.books_a_million import BooksAMillionScraper
from scrapers.ebook_sources import EbookSourcesScraper
from scrapers.gemini_api import GeminiScraper
from scrapers.isbndb import IsbnDBScraper
from utils.cache_manager import CacheManager
from utils.result_processor import process_results

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS with specific settings
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})
cache_manager = CacheManager()

def create_scrapers():
    """Initialize all scrapers"""
    scrapers = {
        'amazon': AmazonScraper(),
        'barnes_noble': BarnesNobleScraper(),
        'book_depository': BookDepositoryScraper(),
        'books_a_million': BooksAMillionScraper(),
        'ebook_sources': EbookSourcesScraper(),
        'gemini': GeminiScraper(),
        'isbndb': IsbnDBScraper()
    }
    return scrapers

scrapers = create_scrapers()

# Initialize scrapers
try:
    print("All scrapers initialized successfully")
except Exception as e:
    print(f"Error initializing scrapers: {str(e)}")
    raise

@app.route('/')
def index():
    return render_template('index.html')

def execute_search(scraper, book_title):
    """Execute a single scraper search with error handling"""
    try:
        print(f"Starting search with {scraper.__class__.__name__} for '{book_title}'")
        results = scraper.search(book_title)
        print(f"Search completed with {scraper.__class__.__name__}: {len(results)} results found")
        return results
    except Exception as e:
        print(f"Error searching with {scraper.__class__.__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

@app.route('/api/search', methods=['POST'])
def search():
    try:
        print("=== Received search request ===")
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No JSON data provided'}), 400
            
        book_title = data.get('title', '')
        format_filter = data.get('format', 'all')
        
        print(f"Searching for: {book_title}, format: {format_filter}")
        
        if not book_title:
            return jsonify({'error': 'Please enter a book title'}), 400
        
        # Check cache first
        cached_results = cache_manager.get_results(book_title, format_filter)
        if cached_results:
            print("Returning cached results")
            return jsonify(cached_results)
        
        # First try with Gemini for most reliable results
        try:
            print(f"Attempting to use Gemini API for '{book_title}'")
            gemini_results = scrapers['gemini'].search(book_title)
            print(f"Gemini API returned {len(gemini_results) if gemini_results else 0} results")
            if gemini_results and len(gemini_results) >= 3:
                # If we get good results from Gemini, use those
                print(f"Using Gemini results: {len(gemini_results)} items found")
                results = {'Gemini Books': gemini_results}
                processed_results = process_results(results, format_filter)
                cache_manager.cache_results(book_title, format_filter, processed_results)
                return jsonify(processed_results)
            else:
                print(f"Gemini results insufficient, falling back to web scrapers")
        except Exception as e:
            print(f"Error with Gemini search: {str(e)}")
            import traceback
            traceback.print_exc()
            # Continue with other scrapers if Gemini fails
            
        # Define search tasks
        search_tasks = {
            'amazon': (execute_search, scrapers['amazon'], book_title),
            'barnes_noble': (execute_search, scrapers['barnes_noble'], book_title),
            'book_depository': (execute_search, scrapers['book_depository'], book_title),
            'books_a_million': (execute_search, scrapers['books_a_million'], book_title),
            'ebook_sources': (execute_search, scrapers['ebook_sources'], book_title),
            'isbndb': (execute_search, scrapers['isbndb'], book_title)
        }
        
        # Execute searches in parallel
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start the search operations and mark each future with its source
            future_to_source = {
                executor.submit(task[0], task[1], task[2]): source 
                for source, task in search_tasks.items()
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    results[source] = future.result()
                    print(f"Got results from {source}: {len(results[source])} items")
                    
                    # Debug the first result's link from each source
                    if results[source] and len(results[source]) > 0:
                        first_result = results[source][0]
                        print(f"First result from {source}: {first_result.get('title', 'No title')} - Link: {first_result.get('link', 'No link')}")
                except Exception as e:
                    print(f"Error processing results from {source}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    results[source] = []
        
        # Check if we have any results
        has_results = False
        for source, source_results in results.items():
            if source_results and len(source_results) > 0:
                has_results = True
                break
                
        if not has_results:
            print("No results found from any source")
            # Return empty results instead of error to allow frontend to show "no results" message
            return jsonify({
                'results': [],
                'count': 0,
                'format_filter': format_filter,
                'message': 'No results found. Please try a different book title.'
            })
        
        # Process and format results
        print("Processing and formatting results...")
        processed_results = process_results(results, format_filter)
        
        # Cache results
        cache_manager.cache_results(book_title, format_filter, processed_results)
        
        print(f"Returning {len(processed_results.get('results', []))} results")
        
        # Debug the links in the final results
        for i, book in enumerate(processed_results.get('results', [])):
            try:
                safe_title = str(book.get('title', 'No title')).encode('ascii', 'replace').decode('ascii')
                print(f"Book {i+1}: {safe_title}")
                for src in book.get('sources', []):
                    print(f"  Source: {src.get('source', 'Unknown')} - Link: {src.get('link', 'No link')}")
            except Exception as e:
                print(f"Error logging book details: {str(e)}")
        
        return jsonify(processed_results)
    
    except Exception as e:
        print(f"Error in search route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True)
