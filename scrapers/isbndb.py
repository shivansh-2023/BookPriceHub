"""
IsbnDB API Scraper for BookPriceHub
"""
import os
import json
from urllib.parse import urljoin
from .base_scraper import BaseScraper

class IsbnDBScraper(BaseScraper):
    """Scraper for IsbnDB API"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://api2.isbndb.com"
        self.search_url = urljoin(self.base_url, "/books")
        self.api_key = os.getenv("ISBNDB_API_KEY", "")
        
    def _get_headers(self):
        """Get headers with API key for IsbnDB"""
        headers = super()._get_headers()
        if self.api_key:
            headers["Authorization"] = self.api_key
        return headers
    
    def search(self, book_title):
        """Search for books on IsbnDB by title"""
        if not self.api_key:
            self.logger.warning("IsbnDB API key not set. Using alternate method.")
            # Fall back to OpenLibrary API which doesn't require a key
            return self._search_openlibrary(book_title)
            
        params = {
            "q": book_title,
            "page": 1,
            "pageSize": 10
        }
        
        self.logger.debug(f"Searching IsbnDB for: {book_title}")
        response = self._make_request(self.search_url, params=params)
        
        if not response:
            self.logger.error("No response from IsbnDB")
            return self._search_openlibrary(book_title)
            
        return self.parse_results(response)
    
    def parse_results(self, response):
        """Parse search results from IsbnDB"""
        results = []
        
        try:
            data = response.json()
            books = data.get("books", [])
            
            for book in books:
                title = book.get("title", "")
                authors = book.get("authors", [])
                author = ", ".join(authors) if authors else "Unknown Author"
                
                # Get price - IsbnDB doesn't provide price info directly
                # but we can look at marketplace offers
                price = "Price not available"
                marketplace = book.get("marketplace", [])
                if marketplace and len(marketplace) > 0:
                    # Get the lowest price available
                    try:
                        prices = [float(item.get("price", "999999").replace("$", "")) 
                                 for item in marketplace if item.get("price")]
                        if prices:
                            min_price = min(prices)
                            price = f"${min_price:.2f}"
                    except (ValueError, AttributeError):
                        pass
                
                # Generate link - IsbnDB doesn't provide direct purchase links
                # Link to Amazon using ISBN if available
                isbn = book.get("isbn13", book.get("isbn", ""))
                if isbn:
                    link = f"https://www.amazon.com/dp/{isbn}"
                else:
                    # Use a generic search link if no ISBN
                    safe_title = title.replace(" ", "+")
                    link = f"https://www.amazon.com/s?k={safe_title}"
                
                # Get available formats
                formats = []
                if book.get("binding"):
                    formats.append(book.get("binding"))
                
                results.append({
                    "title": title,
                    "author": author,
                    "price": price,
                    "link": link,
                    "source": "IsbnDB",
                    "formats": formats,
                    "image_url": book.get("image", "")
                })
                
        except Exception as e:
            self.logger.error(f"Error parsing IsbnDB results: {str(e)}")
            
        return results
    
    def _search_openlibrary(self, book_title):
        """Fallback to OpenLibrary search if IsbnDB fails"""
        base_url = "https://openlibrary.org/search.json"
        params = {
            "q": book_title,
            "limit": 10
        }
        
        response = self._make_request(base_url, params=params)
        if not response:
            return []
            
        try:
            data = response.json()
            results = []
            
            for doc in data.get("docs", [])[:10]:
                title = doc.get("title", "")
                author_names = doc.get("author_name", ["Unknown Author"])
                author = ", ".join(author_names[:2]) if author_names else "Unknown Author"
                
                # Get cover image if available
                cover_id = doc.get("cover_i")
                image_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ""
                
                # Create link to Open Library work
                key = doc.get("key", "")
                if key:
                    link = f"https://openlibrary.org{key}"
                else:
                    # Use a fallback link with the title
                    safe_title = title.replace(" ", "+")
                    link = f"https://openlibrary.org/search?q={safe_title}"
                
                results.append({
                    "title": title,
                    "author": author,
                    "price": "Price not available",  # OpenLibrary doesn't provide prices
                    "link": link,
                    "source": "Open Library",
                    "image_url": image_url
                })
                
            return results
                
        except Exception as e:
            self.logger.error(f"Error parsing OpenLibrary results: {str(e)}")
            return []
