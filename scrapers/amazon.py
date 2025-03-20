from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import logging

from .base_scraper import BaseScraper

class AmazonScraper(BaseScraper):
    """Scraper for Amazon"""
    
    def __init__(self):
        super().__init__()
        self.name = "Amazon"
        self.base_url = "https://www.amazon.com"
        self.search_url = urljoin(self.base_url, "/s")
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
    
    def search(self, book_title):
        """Search for a book on Amazon by title"""
        params = {
            'k': book_title,
            'i': 'stripbooks',
            'ref': 'nb_sb_noss'
        }
        
        self.logger.debug(f"Searching Amazon for: {book_title}")
        
        # Try different country domains if the main one fails
        domains = [
            "https://www.amazon.com",
            "https://www.amazon.co.uk",
            "https://www.amazon.ca"
        ]
        
        for domain in domains:
            self.base_url = domain
            self.search_url = urljoin(self.base_url, "/s")
            
            self.logger.debug(f"Trying Amazon domain: {domain}")
            response = self._make_request(self.search_url, params=params)
            
            if response:
                self.logger.debug(f"Successfully connected to {domain}")
                return self.parse_results(response)
        
        self.logger.error("No response from any Amazon domain")
        return []
    
    def parse_results(self, response):
        """Parse search results from Amazon"""
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Debug the HTML response to a file for inspection
        with open("amazon_debug.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        
        # Look for the search results container
        search_results = soup.select('div[data-component-type="s-search-result"]')
        self.logger.debug(f"Found {len(search_results)} search results")
        
        for item in search_results:
            try:
                result = self._parse_item(item)
                if result:
                    results.append(result)
            except Exception as e:
                self.logger.error(f"Error parsing item: {str(e)}")
                continue
        
        self.logger.debug(f"Extracted {len(results)} valid results")
        return results
    
    def _parse_item(self, item):
        """Parse an individual search result item"""
        result = {
            'source': self.name,
            'format': 'Unknown',
            'link': '#'
        }
        
        # Find the title and link
        title_element = item.select_one('h2 a.a-link-normal')
        
        if not title_element:
            self.logger.debug("No title element found")
            return None
            
        result['title'] = title_element.get_text().strip()
        
        # Get the link - this is crucial
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
            return None  # Skip items without links
        
        # Find the author
        author_element = item.select_one('.a-row .a-size-base')
        if author_element:
            author_text = author_element.get_text().strip()
            if 'by ' in author_text.lower():
                result['author'] = author_text.split('by ', 1)[1].strip()
            else:
                result['author'] = author_text
        
        # Get the price
        price_element = item.select_one('.a-price .a-offscreen')
        if price_element:
            price_text = price_element.get_text().strip()
            self.logger.debug(f"Found price: {price_text}")
            result['price'] = price_text
        else:
            self.logger.debug("No price element found")
            whole_price = item.select_one('.a-price .a-price-whole')
            fraction_price = item.select_one('.a-price .a-price-fraction')
            
            if whole_price and fraction_price:
                price_text = f"${whole_price.get_text().strip()}.{fraction_price.get_text().strip()}"
                self.logger.debug(f"Constructed price: {price_text}")
                result['price'] = price_text
            else:
                # Look for Kindle edition prices
                kindle_price = item.select_one('.a-color-secondary .a-size-base')
                if kindle_price and '$' in kindle_price.get_text():
                    price_text = kindle_price.get_text().strip()
                    price_match = re.search(r'\$\d+\.\d+', price_text)
                    if price_match:
                        result['price'] = price_match.group(0)
                        self.logger.debug(f"Found Kindle price: {result['price']}")
                        result['format'] = 'Ebook'
        
        # Determine format
        format_element = item.select_one('.a-size-base.a-color-secondary:contains("Hardcover"), .a-size-base.a-color-secondary:contains("Paperback"), .a-size-base.a-color-secondary:contains("Audiobook")')
        
        if format_element:
            format_text = format_element.get_text().strip().lower()
            if 'hardcover' in format_text:
                result['format'] = 'Hardcover'
            elif 'paperback' in format_text:
                result['format'] = 'Paperback'
            elif 'audiobook' in format_text or 'audio cd' in format_text:
                result['format'] = 'Audiobook'
            elif 'kindle' in format_text or 'ebook' in format_text:
                result['format'] = 'Ebook'
        else:
            # Try alternate format detection
            format_text = item.get_text().lower()
            if 'hardcover' in format_text:
                result['format'] = 'Hardcover'
            elif 'paperback' in format_text:
                result['format'] = 'Paperback'
            elif 'audiobook' in format_text or 'audio cd' in format_text:
                result['format'] = 'Audiobook'
            elif 'kindle' in format_text or 'ebook' in format_text:
                result['format'] = 'Ebook'
        
        # Get image URL
        img_element = item.select_one('img.s-image')
        if img_element:
            result['image_url'] = img_element.get('src')
        
        # Log the extracted result
        self.logger.debug(f"Extracted result: {result}")
        
        return result
