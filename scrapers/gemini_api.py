import os
import json
import requests
import logging
from urllib.parse import quote

from .base_scraper import BaseScraper

class GeminiScraper(BaseScraper):
    """Scraper using Google's Gemini API for book information"""
    
    def __init__(self):
        super().__init__()
        self.name = "Gemini Books"
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        if not self.api_key:
            self.logger.warning("GEMINI_API_KEY not found in environment variables")
    
    def search(self, book_title):
        """Search for book information using Gemini API"""
        if not self.api_key or self.api_key == "AIzaSyDFdkB-IraeB2amnYBrm988HQUKPcxfzbc":
            self.logger.error("Cannot search without valid Gemini API key")
            return []
        
        self.logger.debug(f"Searching for book: {book_title}")
        print(f"[GeminiScraper] Using API key: {self.api_key[:5]}...{self.api_key[-4:]} (masked for security)")
        print(f"[GeminiScraper] API endpoint: {self.base_url}")
        
        # Format prompt for Gemini
        prompt = self._create_prompt(book_title)
        print(f"[GeminiScraper] Created prompt of length: {len(prompt)}")
        
        try:
            # Make API request
            response = self._call_gemini_api(prompt)
            if not response:
                return []
            
            # Parse response
            results = self._parse_response(response, book_title)
            self.logger.debug(f"Extracted {len(results)} results from Gemini API")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching with Gemini API: {str(e)}")
            return []
    
    def _create_prompt(self, book_title):
        """Create a prompt for the Gemini API"""
        return f"""
        I'm looking for information about the book titled "{book_title}".
        
        Please provide the following information in JSON format:
        1. Full title
        2. Author
        3. Available formats (hardcover, paperback, ebook, audiobook)
        4. Prices for each format at different retailers (Amazon, Barnes & Noble, Book Depository)
        5. Direct purchase links for each retailer
        6. Book cover image URL
        
        Format your response as valid JSON with this structure:
        {{
          "title": "Full Book Title",
          "author": "Author Name",
          "formats": [
            {{
              "format": "Hardcover",
              "retailers": [
                {{
                  "name": "Amazon",
                  "price": "$XX.XX",
                  "link": "https://www.amazon.com/..."
                }},
                ...
              ]
            }},
            ...
          ],
          "cover_image": "https://..."
        }}
        
        Only respond with valid JSON. Don't include any other text.
        """
    
    def _call_gemini_api(self, prompt):
        """Call the Gemini API with the given prompt"""
        url = f"{self.base_url}?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        
        try:
            print(f"[GeminiScraper] Making API request to: {self.base_url}")
            response = requests.post(url, headers=headers, json=data, timeout=15)
            
            print(f"[GeminiScraper] API response status: {response.status_code}")
            if response.status_code != 200:
                self.logger.error(f"Error from Gemini API: {response.status_code} - {response.text}")
                print(f"[GeminiScraper] API error response: {response.text[:500]}")
                return None
            
            print(f"[GeminiScraper] API success! Response size: {len(response.text)} bytes")
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error calling Gemini API: {str(e)}")
            print(f"[GeminiScraper] Exception during API call: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_results(self, response):
        """Parse results from the API response (required abstract method)"""
        # For the Gemini API, we don't use this method from the base class
        # But we need to implement it to satisfy the abstract class requirement
        return []
    
    def _parse_response(self, response_json, original_query):
        """Parse the Gemini API response into book results"""
        results = []
        
        try:
            # Extract text from response
            if not response_json.get("candidates"):
                self.logger.error("No candidates in Gemini response")
                return results
                
            response_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from response text (sometimes it includes markdown code blocks)
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_text = response_text.strip()
                
            self.logger.debug(f"Extracted JSON: {json_text[:500]}...")
            
            # Parse JSON
            book_data = json.loads(json_text)
            
            # Create a result for each format and retailer combination
            for format_info in book_data.get("formats", []):
                format_type = format_info.get("format", "Unknown")
                
                for retailer in format_info.get("retailers", []):
                    result = {
                        "title": book_data.get("title", original_query),
                        "author": book_data.get("author", "Unknown Author"),
                        "source": retailer.get("name", "Unknown Retailer"),
                        "format": format_type,
                        "price": retailer.get("price", "Price not available"),
                        "link": retailer.get("link", "#"),
                        "image_url": book_data.get("cover_image", "")
                    }
                    
                    # Validate the result has required fields
                    if result["title"] and result["link"] != "#":
                        results.append(result)
                        self.logger.debug(f"Added result: {result['title']} - {result['source']} - {result['format']} - {result['price']}")
        
        except Exception as e:
            self.logger.error(f"Error parsing Gemini response: {str(e)}")
        
        return results
