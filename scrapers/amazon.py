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
        """Search for a book on Amazon by title with enhanced error handling"""
        params = {
            'k': book_title,
            'i': 'stripbooks',
            'rh': 'n:5,n:283155,n:3839,n:5,p_n_feature_nine_browse-bin:3291437011,p_n_feature_browse-bin:618073011',  # Computer & Technology Books + Programming
            'ref': 'nb_sb_noss',
            'sort': 'relevance',  # Sort by relevance to find best matches
            'dc': 'All',  # Include all formats (Kindle, hardcover, paperback)
            'qid': None  # Ensure fresh search results
        }
        
        self.logger.debug(f"Searching Amazon for: {book_title}")
        
        # Try different country domains with fallback logic
        domains = [
            "https://www.amazon.com",
            "https://www.amazon.co.uk",
            "https://www.amazon.ca",
            "https://www.amazon.de",  # Additional fallback domains
            "https://www.amazon.fr"
        ]
        
        results = []
        for domain in domains:
            try:
                self.base_url = domain
                self.search_url = urljoin(self.base_url, "/s")
                
                self.logger.debug(f"Trying Amazon domain: {domain}")
                response = self._make_request(self.search_url, params=params)
                
                if response:
                    self.logger.debug(f"Successfully connected to {domain}")
                    domain_results = self.parse_results(response)
                    if domain_results:  # Only return if we got valid results
                        return domain_results
                    else:
                        self.logger.warning(f"No valid results from {domain}, trying next domain")
                else:
                    self.logger.warning(f"Failed to get response from {domain}, trying next domain")
            except Exception as e:
                self.logger.error(f"Error searching {domain}: {str(e)}")
                continue
        
        self.logger.error("No valid response from any Amazon domain")
        return []
    
    def parse_results(self, response):
        """Parse search results from Amazon with enhanced error handling"""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Debug the HTML response to a file for inspection
            with open("amazon_debug.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            
            # Check for CAPTCHA or access denied
            if soup.select_one('#captchacharacters') or soup.select_one('#robot-verification-page'):
                self.logger.error("CAPTCHA or robot verification detected")
                return []
                
            # Try multiple selectors for search results
            search_results = []
            selectors = [
                'div[data-component-type="s-search-result"]',
                '.s-result-item',
                '.sg-col-inner',
                '.s-include-content-margin'
            ]
            
            for selector in selectors:
                search_results = soup.select(selector)
                if search_results:
                    self.logger.debug(f"Found {len(search_results)} results with selector: {selector}")
                    break
                    
            if not search_results:
                self.logger.warning("No search results found with any selector")
                return []
            
            for item in search_results:
                try:
                    result = self._parse_item(item)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error parsing item: {str(e)}")
                    continue
            
            self.logger.debug(f"Extracted {len(results)} valid results")
            
            # Validate results
            if not results and len(search_results) > 0:
                self.logger.warning("Found search results but failed to parse any items")
            
            return results
        except Exception as e:
            self.logger.error(f"Critical error parsing results: {str(e)}")
            return []
    
    def _parse_item(self, item):
        """Parse an individual search result item"""
        result = {
            'source': self.name,
            'format': 'Unknown',
            'link': '#'
        }
        
        # Find the title and link using multiple selectors
        title_selectors = ['h2 a.a-link-normal', '.a-link-normal .a-text-normal']
        title_element = None
        for selector in title_selectors:
            title_element = item.select_one(selector)
            if title_element:
                break
                
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
        
        # Find the author with multiple selectors
        author_selectors = ['.a-row .a-size-base', '.a-row .a-link-normal']
        for selector in author_selectors:
            author_element = item.select_one(selector)
            if author_element:
                author_text = author_element.get_text().strip()
                if 'by ' in author_text.lower():
                    result['author'] = author_text.split('by ', 1)[1].strip()
                    break
                elif not any(keyword in author_text.lower() for keyword in ['hardcover', 'paperback', 'kindle']):
                    result['author'] = author_text
                    break
        
        # Get the price with multiple selectors
        price_found = False
        price_selectors = [
            '.a-price .a-offscreen',
            '.a-price span[aria-hidden="true"]',
            '.a-color-base .a-text-price'
        ]
        
        for selector in price_selectors:
            price_element = item.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                price_match = re.search(r'\$\d+\.\d+', price_text)
                if price_match:
                    # Replace $ with ₹
                    result['price'] = price_match.group(0).replace('$', '₹')
                    price_found = True
                    self.logger.debug(f"Found price: {result['price']}")
                    break
        
        if not price_found:
            # Try to construct price from whole and fraction parts
            whole_price = item.select_one('.a-price .a-price-whole')
            fraction_price = item.select_one('.a-price .a-price-fraction')
            if whole_price and fraction_price:
                price_text = f"₹{whole_price.get_text().strip()}.{fraction_price.get_text().strip()}"
                result['price'] = price_text
                self.logger.debug(f"Constructed price: {price_text}")
        
        # Determine format with multiple approaches
        format_selectors = [
            '.a-size-base.a-color-secondary',
            '.a-row .a-text-bold',
            '.a-row .a-size-base'
        ]
        
        format_found = False
        for selector in format_selectors:
            format_elements = item.select(selector)
            for element in format_elements:
                format_text = element.get_text().strip().lower()
                if 'hardcover' in format_text:
                    result['format'] = 'Hardcover'
                    format_found = True
                    break
                elif 'paperback' in format_text:
                    result['format'] = 'Paperback'
                    format_found = True
                    break
                elif 'audiobook' in format_text or 'audio cd' in format_text:
                    result['format'] = 'Audiobook'
                    format_found = True
                    break
                elif 'kindle' in format_text or 'ebook' in format_text:
                    result['format'] = 'Ebook'
                    format_found = True
                    break
            if format_found:
                break
        
        # Get image URL
        image_element = item.select_one('img.s-image')
        if image_element:
            result['image_url'] = image_element.get('src')
            
        self.logger.debug(f"Parsed result: {result}")
        return result
        
        # Get image URL
        img_element = item.select_one('img.s-image')
        if img_element:
            result['image_url'] = img_element.get('src')
        
        # Log the extracted result
        self.logger.debug(f"Extracted result: {result}")
        
        return result
