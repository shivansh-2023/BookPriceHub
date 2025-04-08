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
        self.max_retries = 3  # Add max retries for request attempts
        self.retry_status_codes = {403, 429, 500, 502, 503, 504}  # Status codes that should trigger a retry
    
    def search(self, book_title):
        """Search for a book on Barnes & Noble by title"""
        params = {
            'Ntt': book_title,
            'page': '1',
            'N': '2290',  # Category filter for Computer & Technology Books
            'Ntk': 'ALLPRODUCT'  # Search across all product fields
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
        """Parse search results from Barnes & Noble with enhanced error handling"""
        try:
            # Try parsing as JSON first
            try:
                json_data = response.json()
                if json_data and isinstance(json_data, dict):
                    return self._parse_json_results(json_data)
            except (ValueError, AttributeError) as e:
                self.logger.debug(f"Not a JSON response: {str(e)}")
            
            # Fall back to HTML parsing
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Debug the HTML response to a file
            with open("bn_debug.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            
            # Enhanced error page and anti-bot detection
            error_indicators = {
                '#no-results': 'No results found',
                '.error-page': 'Error page detected',
                '#robot-verification': 'Bot detection triggered',
                '.captcha': 'Captcha verification required',
                '.access-denied': 'Access denied',
                '.maintenance': 'Site maintenance',
                '.rate-limit': 'Rate limit exceeded'
            }
            
            for selector, message in error_indicators.items():
                if soup.select_one(selector):
                    self.logger.warning(f"{message} ({selector})")
                    return []
                    
            # Check for empty or invalid response content
            if len(soup.text.strip()) < 100:
                self.logger.warning("Suspiciously short page content - likely an error page")
                return []
                
            # Verify expected page structure
            if not soup.select_one('.product-shelf-tile, .product-info-view, .product'):
                self.logger.warning("Missing expected page structure elements")
                return []
            
            # Try multiple selectors for product cards
            selectors = [
                '.product-shelf-tile',
                '.product-info-view',
                '.product',
                '.product-item',
                '[data-product]'
            ]
            
            product_cards = []
            for selector in selectors:
                cards = soup.select(selector)
                if cards:
                    self.logger.debug(f"Found {len(cards)} product cards with selector: {selector}")
                    product_cards = cards
                    break
            
            if not product_cards:
                self.logger.warning("No product cards found with any selector")
                return []
            
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
            
        except Exception as e:
            self.logger.error(f"Critical error parsing results: {str(e)}")
            return []
            
    def _parse_json_results(self, json_data):
        """Parse JSON response from Barnes & Noble API"""
        results = []
        try:
            # Adapt this based on actual B&N JSON structure
            items = json_data.get('items', []) or json_data.get('products', [])
            
            for item in items[:10]:  # Limit to first 10 results
                try:
                    result = {
                        'source': self.name,
                        'title': item.get('title', '').strip(),
                        'author': item.get('author', '').strip(),
                        'price': item.get('price', {}).get('current', ''),
                        'format': item.get('format', 'Unknown'),
                        'link': urljoin(self.base_url, item.get('url', ''))
                    }
                    
                    if result['title'] and result['link'] != self.base_url + '':
                        results.append(result)
                        
                except Exception as e:
                    self.logger.error(f"Error parsing JSON item: {str(e)}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error parsing JSON data: {str(e)}")
            
        return results
            
    def _validate_result(self, result):
        """Validate parsed result has required fields and data quality"""
        required_fields = ['title', 'link', 'source']
        
        for field in required_fields:
            if not result.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
            
            # Additional validation for non-empty strings
            if not isinstance(result[field], str) or not result[field].strip():
                self.logger.warning(f"Invalid or empty {field}")
                return False
                
        # Validate URL format and domain
        if not result['link'].startswith(('http://', 'https://')):
            self.logger.warning(f"Invalid URL format: {result['link']}")
            return False
            
        try:
            parsed_url = urlparse(result['link'])
            if not parsed_url.netloc or not parsed_url.netloc.endswith('barnesandnoble.com'):
                self.logger.warning(f"Invalid domain in URL: {result['link']}")
                return False
        except Exception as e:
            self.logger.error(f"Error parsing URL {result['link']}: {str(e)}")
            return False
            
        # Validate price format if present
        if 'price' in result and result['price']:
            if not re.match(r'\$?\d+\.?\d*', result['price']):
                self.logger.warning(f"Invalid price format: {result['price']}")
                result['price'] = None
            
        return True
    
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
        
        # Extract format with enhanced selectors and validation
        format_element = card.select_one('.format, .product-shelf-format, .product-info-format, [data-format], [itemprop="bookFormat"]')
        if format_element:
            format_text = format_element.get_text().strip().lower()
            data_format = format_element.get('data-format', '').lower()
            
            # Check both text content and data attributes
            format_indicators = format_text + ' ' + data_format
            
            if any(x in format_indicators for x in ['hardcover', 'hardback', 'hard cover']):
                result['format'] = 'Hardcover'
            elif any(x in format_indicators for x in ['paperback', 'softcover', 'soft cover']):
                result['format'] = 'Paperback'
            elif any(x in format_indicators for x in ['audiobook', 'audio cd', 'audio book', 'mp3']):
                result['format'] = 'Audiobook'
            elif any(x in format_indicators for x in ['nook', 'ebook', 'digital', 'electronic']):
                result['format'] = 'Ebook'
            
            self.logger.debug(f"Format: {result['format']} (from: {format_text})")
        
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
