from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import re

class BooksAMillionScraper(BaseScraper):
    """Scraper for Books-A-Million listings"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.booksamillion.com"
        self.search_url = f"{self.base_url}/search"
    
    def search(self, book_title):
        """Search for a book on Books-A-Million by title"""
        params = {
            'query': book_title,
            'filter': 'product_type:Books'
        }
        
        response = self._make_request(self.search_url, params=params)
        if not response:
            return []
        
        return self.parse_results(response)
    
    def parse_results(self, response):
        """Parse Books-A-Million search results page"""
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Find all product cards
        product_cards = soup.select('.product-info')
        
        for card in product_cards[:5]:  # Limit to first 5 results
            try:
                # Extract title
                title_element = card.select_one('.title a')
                title = title_element.text.strip() if title_element else 'Unknown Title'
                
                # Extract author
                author_element = card.select_one('.author')
                author = author_element.text.replace('by', '').strip() if author_element else 'Unknown Author'
                
                # Extract price
                price_element = card.select_one('.our-price')
                price = price_element.text.strip() if price_element else 'Price not available'
                
                # Extract image URL
                img_element = card.find_previous('div', class_='product-image').select_one('img')
                img_url = img_element.get('src') if img_element else ''
                
                # Extract link
                link_element = card.select_one('.title a')
                link = self.base_url + link_element.get('href') if link_element else ''
                
                # Extract format
                format_element = card.select_one('.format')
                format_text = format_element.text.strip() if format_element else ''
                
                book_format = 'Unknown'
                if 'paperback' in format_text.lower():
                    book_format = 'Paperback'
                elif 'hardcover' in format_text.lower():
                    book_format = 'Hardcover'
                elif 'ebook' in format_text.lower():
                    book_format = 'Ebook'
                elif 'audio' in format_text.lower():
                    book_format = 'Audiobook'
                
                results.append({
                    'title': title,
                    'author': author,
                    'price': price,
                    'format': book_format,
                    'image_url': img_url,
                    'link': link,
                    'source': 'Books-A-Million'
                })
                
            except Exception as e:
                print(f"Error parsing Books-A-Million result: {str(e)}")
                continue
        
        return results
