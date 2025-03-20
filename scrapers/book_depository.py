from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import re

class BookDepositoryScraper(BaseScraper):
    """Scraper for Book Depository listings"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.bookdepository.com"
        self.search_url = f"{self.base_url}/search"
    
    def search(self, book_title):
        """Search for a book on Book Depository by title"""
        params = {
            'searchTerm': book_title,
            'search': 'Find book'
        }
        
        response = self._make_request(self.search_url, params=params)
        if not response:
            return []
        
        return self.parse_results(response)
    
    def parse_results(self, response):
        """Parse Book Depository search results page"""
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Find all product cards
        product_cards = soup.select('.book-item')
        
        for card in product_cards[:5]:  # Limit to first 5 results
            try:
                # Extract title
                title_element = card.select_one('h3.title a')
                title = title_element.text.strip() if title_element else 'Unknown Title'
                
                # Extract author
                author_element = card.select_one('p.author a')
                author = author_element.text.strip() if author_element else 'Unknown Author'
                
                # Extract price
                price_element = card.select_one('.price')
                price = price_element.text.strip() if price_element else 'Price not available'
                
                # Extract image URL
                img_element = card.select_one('.item-img img')
                img_url = img_element.get('data-lazy') if img_element and img_element.get('data-lazy') else img_element.get('src') if img_element else ''
                
                # Extract link
                link_element = card.select_one('h3.title a')
                link = self.base_url + link_element.get('href') if link_element else ''
                
                # Extract format
                format_element = card.select_one('.format')
                format_text = format_element.text.strip() if format_element else ''
                
                book_format = 'Unknown'
                if 'paperback' in format_text.lower():
                    book_format = 'Paperback'
                elif 'hardback' in format_text.lower() or 'hardcover' in format_text.lower():
                    book_format = 'Hardcover'
                elif 'ebook' in format_text.lower():
                    book_format = 'Ebook'
                elif 'cd' in format_text.lower() or 'audio' in format_text.lower():
                    book_format = 'Audiobook'
                
                # Extract publication date
                pub_date_element = card.select_one('.published')
                pub_date = pub_date_element.text.strip() if pub_date_element else 'Unknown'
                
                results.append({
                    'title': title,
                    'author': author,
                    'price': price,
                    'format': book_format,
                    'image_url': img_url,
                    'link': link,
                    'publication_date': pub_date,
                    'source': 'Book Depository'
                })
                
            except Exception as e:
                print(f"Error parsing Book Depository result: {str(e)}")
                continue
        
        return results
