from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import re
import json
import math

class EbookSourcesScraper(BaseScraper):
    """Scraper for ebook sources including free legal downloads"""
    
    def __init__(self):
        super().__init__()
        self.gutenberg_url = "https://www.gutenberg.org/ebooks/search/"
        self.open_library_url = "https://openlibrary.org/search.json"
        self.google_books_url = "https://www.googleapis.com/books/v1/volumes"
        self.kobo_url = "https://www.kobo.com/us/en/search"
    
    def search(self, book_title):
        """Search for ebooks across multiple platforms"""
        results = []
        
        # Search Project Gutenberg
        gutenberg_results = self._search_gutenberg(book_title)
        if gutenberg_results:
            results.extend(gutenberg_results)
        
        # Search Open Library
        open_library_results = self._search_open_library(book_title)
        if open_library_results:
            results.extend(open_library_results)
        
        # Search Google Books
        google_books_results = self._search_google_books(book_title)
        if google_books_results:
            results.extend(google_books_results)
        
        # Search Kobo
        kobo_results = self._search_kobo(book_title)
        if kobo_results:
            results.extend(kobo_results)
        
        return results
    
    def _search_gutenberg(self, book_title):
        """Search for free ebooks on Project Gutenberg"""
        params = {
            'query': book_title
        }
        
        response = self._make_request(self.gutenberg_url, params=params)
        if not response:
            return []
        
        return self._parse_gutenberg_results(response)
    
    def _parse_gutenberg_results(self, response):
        """Parse Project Gutenberg search results"""
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Find all book entries
        book_entries = soup.select('.booklink')
        
        for entry in book_entries[:3]:  # Limit to first 3 results
            try:
                # Extract title
                title_element = entry.select_one('.title')
                title = title_element.text.strip() if title_element else 'Unknown Title'
                
                # Extract author
                author_element = entry.select_one('.subtitle')
                author = author_element.text.strip() if author_element else 'Unknown Author'
                
                # Extract link
                link_element = entry.select_one('a.link')
                book_id = link_element.get('href').split('/')[-1] if link_element else ''
                link = f"https://www.gutenberg.org/ebooks/{book_id}" if book_id else ''
                
                # Construct download links
                download_links = {
                    'HTML': f"https://www.gutenberg.org/files/{book_id}/{book_id}-h/{book_id}-h.htm" if book_id else '',
                    'EPUB': f"https://www.gutenberg.org/ebooks/{book_id}.epub.noimages" if book_id else '',
                    'Kindle': f"https://www.gutenberg.org/ebooks/{book_id}.kindle.noimages" if book_id else '',
                    'Plain Text': f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt" if book_id else ''
                }
                
                results.append({
                    'title': title,
                    'author': author,
                    'price': 'Free',
                    'format': 'Ebook',
                    'image_url': f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.cover.medium.jpg" if book_id else '',
                    'link': link,
                    'download_links': download_links,
                    'source': 'Project Gutenberg',
                    'is_free': True
                })
                
            except Exception as e:
                print(f"Error parsing Project Gutenberg result: {str(e)}")
                continue
        
        return results
    
    def _search_open_library(self, book_title):
        """Search for ebooks on Open Library"""
        params = {
            'q': book_title,
            'limit': 5
        }
        
        response = self._make_request(self.open_library_url, params=params)
        if not response:
            return []
        
        return self._parse_open_library_results(response)
    
    def _parse_open_library_results(self, response):
        """Parse Open Library search results"""
        results = []
        
        try:
            data = response.json()
            docs = data.get('docs', [])
            
            for doc in docs[:3]:  # Limit to first 3 results
                title = doc.get('title', 'Unknown Title')
                author_names = doc.get('author_name', ['Unknown Author'])
                author = author_names[0] if author_names else 'Unknown Author'
                
                # Get Open Library ID
                key = doc.get('key', '')
                
                # Check if ebook is available
                ebook = doc.get('ebook_access', 'no_ebook')
                is_free = ebook in ['public', 'borrowable']
                
                # Construct image URL
                cover_id = doc.get('cover_i')
                image_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else ''
                
                # Construct book URL
                book_url = f"https://openlibrary.org{key}" if key else ''
                
                results.append({
                    'title': title,
                    'author': author,
                    'price': 'Free' if is_free else 'Borrowable',
                    'format': 'Ebook',
                    'image_url': image_url,
                    'link': book_url,
                    'source': 'Open Library',
                    'is_free': is_free
                })
                
        except Exception as e:
            print(f"Error parsing Open Library results: {str(e)}")
        
        return results
    
    def _search_google_books(self, book_title):
        """Search for books on Google Books"""
        base_url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            'q': book_title,
            'maxResults': 15,
            'printType': 'books',
            'orderBy': 'relevance'
        }
        
        response = self._make_request(base_url, params=params)
        if not response:
            return []
        
        try:
            data = response.json()
            results = []
            
            if 'items' not in data:
                return []
                
            for item in data['items']:
                volume_info = item.get('volumeInfo', {})
                sale_info = item.get('saleInfo', {})
                
                title = volume_info.get('title', '')
                authors = volume_info.get('authors', [])
                author = ', '.join(authors) if authors else 'Unknown Author'
                
                # Extract price information
                price = 'Price not available'
                if sale_info.get('saleability') == 'FOR_SALE' and 'retailPrice' in sale_info:
                    amount = sale_info['retailPrice'].get('amount')
                    currency = sale_info['retailPrice'].get('currencyCode', 'USD')
                    
                    if amount:
                        # Make sure price is a valid number (not infinity or NaN)
                        try:
                            float_amount = float(amount)
                            if float_amount > 10000 or math.isinf(float_amount) or math.isnan(float_amount):
                                price = 'Price not available'
                            else:
                                price = f"${float_amount}" if currency == 'USD' else f"{float_amount} {currency}"
                        except (ValueError, TypeError):
                            price = 'Price not available'
                
                # Check if preview is available
                is_preview_available = volume_info.get('previewLink') is not None
                
                # Generate link
                link = volume_info.get('infoLink', '')
                if not link and 'id' in item:
                    link = f"https://play.google.com/store/books/details?id={item['id']}&source=gbs_api"
                
                # Get image URL
                image_url = None
                if 'imageLinks' in volume_info:
                    image_url = volume_info['imageLinks'].get('thumbnail', '')
                    # Convert HTTP to HTTPS to avoid mixed content
                    if image_url and image_url.startswith('http:'):
                        image_url = image_url.replace('http:', 'https:')
                
                results.append({
                    'title': title,
                    'author': author,
                    'price': price,
                    'link': link,
                    'source': 'Google Books',
                    'image_url': image_url,
                    'availability': 'Available' if sale_info.get('saleability') == 'FOR_SALE' else 'Preview Only' if is_preview_available else 'Not Available'
                })
                
            return results
        except Exception as e:
            self.logger.error(f"Error parsing Google Books response: {str(e)}")
            return []
    
    def _search_kobo(self, book_title):
        """Search for ebooks on Kobo"""
        params = {
            'query': book_title
        }
        
        response = self._make_request(self.kobo_url, params=params)
        if not response:
            return []
        
        return self._parse_kobo_results(response)
    
    def _parse_kobo_results(self, response):
        """Parse Kobo search results"""
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Find all product cards
        product_cards = soup.select('.item-wrapper')
        
        for card in product_cards[:3]:  # Limit to first 3 results
            try:
                # Extract title
                title_element = card.select_one('.title.product-field a')
                title = title_element.text.strip() if title_element else 'Unknown Title'
                
                # Extract author
                author_element = card.select_one('.contributor-name a')
                author = author_element.text.strip() if author_element else 'Unknown Author'
                
                # Extract price
                price_element = card.select_one('.price-wrapper .price')
                price = price_element.text.strip() if price_element else 'Price not available'
                
                # Extract image URL
                img_element = card.select_one('.item-image img')
                img_url = img_element.get('src') if img_element else ''
                
                # Extract link
                link = title_element.get('href') if title_element else ''
                if link and not link.startswith('http'):
                    link = f"https://www.kobo.com{link}"
                
                results.append({
                    'title': title,
                    'author': author,
                    'price': price,
                    'format': 'Ebook',
                    'image_url': img_url,
                    'link': link,
                    'source': 'Kobo',
                    'is_free': 'free' in price.lower()
                })
                
            except Exception as e:
                print(f"Error parsing Kobo result: {str(e)}")
                continue
        
        return results
    
    def parse_results(self, response):
        """Base implementation of parse_results required by BaseScraper"""
        # This is a composite scraper that uses specialized parsing methods for each source
        # This method is implemented to satisfy the BaseScraper abstract method requirement
        # but is not actually used - we call the specific parsers directly
        return []
