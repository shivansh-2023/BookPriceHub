import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .base_scraper import BaseScraper

class BarnesNobleScraper(BaseScraper):
    """Scraper for Barnes & Noble"""
    
    def __init__(self):
        super().__init__()
        self.name = "Barnes & Noble"
        self.base_url = "https://www.barnesandnoble.com"
        self.search_url = urljoin(self.base_url, "/s/")
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
    
    def search(self, book_title):
        """Search for a book on Barnes & Noble by title"""
        params = {
            'Ntt': book_title,
            'page': '1'
        }
        
        self.logger.debug(f"Searching Barnes & Noble for: {book_title}")
        
        # First try the standard search API
        response = self._make_request(self.search_url, params=params)
        
        # If first attempt fails, try alternative URL structure
        if not response:
            self.logger.debug("Trying alternative Barnes & Noble search method")
            alt_url = f"https://www.barnesandnoble.com/s/{book_title.replace(' ', '%20')}"
            response = self._make_request(alt_url)
        
        if not response:
            self.logger.error("No response from Barnes & Noble")
            return []
            
        return self.parse_results(response)
    
    def parse_results(self, response):
        """Parse search results from Barnes & Noble"""
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Debug the HTML response to a file
        with open("bn_debug.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        
        # Find all product cards
        product_cards = soup.select('.product-shelf-tile')
        self.logger.debug(f"Found {len(product_cards)} product cards")
        
        if not product_cards:
            # Try alternate product card selectors
            product_cards = soup.select('.product-info-view')
            self.logger.debug(f"Found {len(product_cards)} product cards with alternate selector")
            
            if not product_cards:
                product_cards = soup.select('.product')
                self.logger.debug(f"Found {len(product_cards)} product cards with second alternate selector")
        
        for card in product_cards[:10]:  # Limit to first 10 results
            try:
                result = self._parse_item(card)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Error parsing B&N item: {str(e)}")
                continue
        
        self.logger.debug(f"Extracted {len(results)} valid results from Barnes & Noble")
        return results
    
    def _parse_item(self, card):
        """Parse an individual product card"""
        result = {
            'source': self.name,
            'format': 'Unknown',
            'link': '#'
        }
        
        # Extract title and link
        title_element = card.select_one('.product-info-title a, .product-title a, h3.product-info-title a')
        if not title_element:
            self.logger.debug("No title element found")
            return None
        
        result['title'] = title_element.get_text().strip()
        
        # Get link - crucial
        link = title_element.get('href')
        if link:
            # Ensure link is absolute
            if link.startswith('/'):
                result['link'] = urljoin(self.base_url, link)
            else:
                result['link'] = link
            
            self.logger.debug(f"Extracted link: {result['link']}")
        else:
            self.logger.debug("No link found")
            return None
        
        # Extract author
        author_element = card.select_one('.product-shelf-author a, .product-info-author a, .product-creator-link a')
        if author_element:
            result['author'] = author_element.get_text().strip()
            self.logger.debug(f"Author: {result['author']}")
        
        # Extract price
        price_element = card.select_one('.sale, .current-price, .product-info-price .price')
        if price_element:
            price_text = price_element.get_text().strip()
            # Clean up price text
            price_text = re.sub(r'\s+', ' ', price_text)
            result['price'] = price_text
            self.logger.debug(f"Price: {price_text}")
        else:
            # Try alternate price elements
            price_element = card.select_one('[data-price], [itemprop="price"]')
            if price_element:
                price = price_element.get('data-price') or price_element.get('content')
                if price:
                    result['price'] = f"${price}"
                    self.logger.debug(f"Alternate price: {result['price']}")
        
        # Extract format
        format_element = card.select_one('.format, .product-shelf-format, .product-info-format')
        if format_element:
            format_text = format_element.get_text().strip().lower()
            
            if 'hardcover' in format_text:
                result['format'] = 'Hardcover'
            elif 'paperback' in format_text:
                result['format'] = 'Paperback'
            elif 'audiobook' in format_text or 'audio cd' in format_text or 'audio book' in format_text:
                result['format'] = 'Audiobook'
            elif 'nook' in format_text or 'ebook' in format_text:
                result['format'] = 'Ebook'
            
            self.logger.debug(f"Format: {result['format']}")
        
        # Extract image URL
        img_element = card.select_one('img.full-shadow, img.product-image')
        if img_element:
            img_url = img_element.get('src')
            if img_url:
                result['image_url'] = img_url
                self.logger.debug(f"Image URL: {img_url}")
        
        # Extract rating
        rating_element = card.select_one('.product-shelf-stars')
        if rating_element:
            rating = rating_element.get('aria-label', 'No rating')
            result['rating'] = rating
            self.logger.debug(f"Rating: {rating}")
        
        # Log final result
        self.logger.debug(f"Extracted result: {result}")
        return result
