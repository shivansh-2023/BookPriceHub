from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
import re
import json
import math
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from urllib.parse import quote

class EbookSourcesScraper(BaseScraper):
    """Scraper for ebook sources including free legal downloads"""
    
    def __init__(self):
        super().__init__()
        self.gutenberg_url = "https://www.gutenberg.org/ebooks/search/"
        self.open_library_url = "https://openlibrary.org/search.json"
        self.google_books_url = "https://www.googleapis.com/books/v1/volumes"
        self.kobo_url = "https://www.kobo.com/us/en/search"
        self.bookfinder_url = "https://www.bookfinder.com/search/"
        self.perlego_url = "https://www.perlego.com/search"
        self.bookshop_url = "https://bookshop.org/books/search"
        
        # Initialize aiohttp session
        self.timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds timeout
    
    async def _fetch_source(self, session: aiohttp.ClientSession, search_func, source_name: str, book_title: str) -> List[Dict[str, Any]]:
        """Fetch results from a single source asynchronously"""
        try:
            results = await search_func(session, book_title)
            if results:
                print(f"Found {len(results)} results from {source_name}")
                return results
        except Exception as e:
            print(f"Error searching {source_name}: {str(e)}")
        return []

    def search(self, book_title: str) -> List[Dict[str, Any]]:
        """Search for ebooks across selected platforms using async requests"""
        async def _async_search():
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                sources = [
                    (self._search_google_books, 'Google Books'),
                    (self._search_bookfinder, 'BookFinder'),
                    (self._search_perlego, 'Perlego'),
                    (self._search_bookshop, 'Bookshop.org'),
                    (self._search_gutenberg, 'Project Gutenberg'),
                    (self._search_kobo, 'Kobo')
                ]
                
                tasks = [self._fetch_source(session, func, name, book_title) for func, name in sources]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Flatten results and filter out errors
                all_results = []
                for result in results:
                    if isinstance(result, list):
                        all_results.extend(result)
                return all_results

        # Run async search in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(_async_search())
        finally:
            loop.close()
        
        return results
    
    async def _search_gutenberg(self, session: aiohttp.ClientSession, book_title: str) -> List[Dict[str, Any]]:
        """Search for free ebooks on Project Gutenberg"""
        params = {
            'query': book_title
        }
        
        try:
            async with session.get(self.gutenberg_url, params=params) as response:
                if response.status != 200:
                    return []
                return await self._parse_gutenberg_results(response)
        except Exception as e:
            print(f"Error searching Project Gutenberg: {str(e)}")
            return []
    
    async def _parse_gutenberg_results(self, response):
        """Parse Project Gutenberg search results"""
        soup = BeautifulSoup(await response.text(), 'html.parser')
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
    
    async def _search_google_books(self, session: aiohttp.ClientSession, book_title: str) -> List[Dict[str, Any]]:
        """Search for books on Google Books"""
        params = {
            'q': book_title,
            'maxResults': 15,
            'printType': 'books',
            'orderBy': 'relevance',
            'filter': 'paid-ebooks',  # Focus on available ebooks
            'langRestrict': 'en'  # English language books
        }
        
        print(f"Searching Google Books for: {book_title}")
        try:
            async with session.get(self.google_books_url, params=params) as response:
                if response.status != 200:
                    print("No response from Google Books API")
                    return []
                
                data = await response.json()
            results = []
            
            if 'items' not in data:
                print("No items found in Google Books API response")
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
                                price = f"₹{float_amount}" if currency == 'USD' else f"{float_amount} {currency}"
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
    
    async def _parse_kobo_results(self, response):
        """Parse Kobo search results"""
        soup = BeautifulSoup(await response.text(), 'html.parser')
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

    async def _search_bookfinder(self, session: aiohttp.ClientSession, book_title: str) -> List[Dict[str, Any]]:
        """Search for books on BookFinder.com"""
        params = {
            'title': book_title,
            'new_used': 'all',
            'destination': 'us',
            'currency': 'USD',
            'mode': 'basic',
            'st': 'sr',
            'ac': 'qr'
        }
        
        try:
            async with session.get(self.bookfinder_url, params=params) as response:
                if response.status != 200:
                    return []
                    
                soup = BeautifulSoup(await response.text(), 'html.parser')
                results = []
                
                # Find book entries
                book_entries = soup.select('.results-table .item-info')
                
                for entry in book_entries[:3]:
                    title_element = entry.select_one('.details-title')
                    author_element = entry.select_one('.details-author')
                    price_element = entry.select_one('.results-price')
                    link_element = entry.select_one('.details-title a')
                    
                    title = title_element.text.strip() if title_element else 'Unknown Title'
                    author = author_element.text.strip() if author_element else 'Unknown Author'
                    price = price_element.text.strip() if price_element else 'Price not available'
                    link = link_element.get('href', '') if link_element else ''
                    
                    results.append({
                        'title': title,
                        'author': author,
                        'price': price,
                        'link': link,
                        'source': 'BookFinder',
                        'format': 'Multiple formats'
                    })
                    
                return results
                
        except Exception as e:
            print(f"Error searching BookFinder: {str(e)}")
            return []

    async def _search_perlego(self, session: aiohttp.ClientSession, book_title: str) -> List[Dict[str, Any]]:
        """Search for books on Perlego"""
        params = {
            'query': book_title,
            'page': 1
        }
        
        try:
            async with session.get(self.perlego_url, params=params) as response:
                if response.status != 200:
                    return []
                    
                soup = BeautifulSoup(await response.text(), 'html.parser')
                results = []
                
                # Find book cards
                book_cards = soup.select('.book-card')
                
                for card in book_cards[:3]:
                    title_element = card.select_one('.book-title')
                    author_element = card.select_one('.book-author')
                    link_element = card.select_one('a')
                    img_element = card.select_one('img')
                    
                    title = title_element.text.strip() if title_element else 'Unknown Title'
                    author = author_element.text.strip() if author_element else 'Unknown Author'
                    link = link_element.get('href', '') if link_element else ''
                    img_url = img_element.get('src', '') if img_element else ''
                    
                    if link and not link.startswith('http'):
                        link = f"https://www.perlego.com{link}"
                    
                    results.append({
                        'title': title,
                        'author': author,
                        'price': 'Subscription required',
                        'link': link,
                        'image_url': img_url,
                        'source': 'Perlego',
                        'format': 'Ebook'
                    })
                    
                return results
                
        except Exception as e:
            print(f"Error searching Perlego: {str(e)}")
            return []

    async def _search_bookshop(self, session: aiohttp.ClientSession, book_title: str) -> List[Dict[str, Any]]:
        """Search for books on Bookshop.org"""
        params = {
            'q': book_title
        }
        
        try:
            async with session.get(self.bookshop_url, params=params) as response:
                if response.status != 200:
                    return []
                    
                soup = BeautifulSoup(await response.text(), 'html.parser')
                results = []
                
                # Find book entries
                book_entries = soup.select('.book-block')
                
                for entry in book_entries[:3]:
                    title_element = entry.select_one('.book-title')
                    author_element = entry.select_one('.book-author')
                    price_element = entry.select_one('.book-price')
                    link_element = entry.select_one('a.book-link')
                    img_element = entry.select_one('img.book-image')
                    
                    title = title_element.text.strip() if title_element else 'Unknown Title'
                    author = author_element.text.strip() if author_element else 'Unknown Author'
                    price = price_element.text.strip() if price_element else 'Price not available'
                    link = link_element.get('href', '') if link_element else ''
                    img_url = img_element.get('src', '') if img_element else ''
                    
                    if link and not link.startswith('http'):
                        link = f"https://bookshop.org{link}"
                    
                    results.append({
                        'title': title,
                        'author': author,
                        'price': price,
                        'link': link,
                        'image_url': img_url,
                        'source': 'Bookshop.org',
                        'format': 'Physical Book'
                    })
                    
                return results
                
        except Exception as e:
            print(f"Error searching Bookshop.org: {str(e)}")
            return []
    
    def parse_results(self, response):
        """Base implementation of parse_results required by BaseScraper"""
        # This is a composite scraper that uses specialized parsing methods for each source
        # This method is implemented to satisfy the BaseScraper abstract method requirement
        # but is not actually used - we call the specific parsers directly
        return []
