import os
import json
import requests
import logging
from urllib.parse import quote

from .base_scraper import BaseScraper

class OpenAIScraper(BaseScraper):
    """Scraper using OpenAI's ChatGPT API for book information"""
    
    def __init__(self):
        super().__init__()
        self.name = "ChatGPT Books"
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo"  # You can also use "gpt-4" for better results
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        if not self.api_key:
            self.logger.warning("OPENAI_API_KEY not found in environment variables")
    
    def search(self, book_title):
        """Search for book information using ChatGPT API"""
        if not self.api_key:
            self.logger.error("Cannot search without OpenAI API key")
            return []
        
        self.logger.debug(f"Searching for book: {book_title}")
        
        # Format prompt for ChatGPT
        messages = self._create_messages(book_title)
        
        try:
            # Make API request
            response = self._call_openai_api(messages)
            if not response:
                return []
            
            # Parse response
            results = self._parse_response(response, book_title)
            self.logger.debug(f"Extracted {len(results)} results from ChatGPT API")
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching with ChatGPT API: {str(e)}")
            return []
    
    def _create_messages(self, book_title):
        """Create messages for the ChatGPT API"""
        prompt = f"""
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
        
        return [
            {"role": "system", "content": "You are a helpful assistant that provides book information in JSON format."},
            {"role": "user", "content": prompt}
        ]
    
    def _call_openai_api(self, messages):
        """Call the OpenAI API with the given messages"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # Lower temperature for more consistent results
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=15)
            
            if response.status_code != 200:
                self.logger.error(f"Error from OpenAI API: {response.status_code} - {response.text}")
                return None
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error calling OpenAI API: {str(e)}")
            return None
    
    def parse_results(self, response):
        """Parse results from the API response (required abstract method)"""
        # For the OpenAI API, we don't use this method from the base class
        # But we need to implement it to satisfy the abstract class requirement
        return []
    
    def _parse_response(self, response_json, original_query):
        """Parse the OpenAI API response into book results"""
        results = []
        
        try:
            # Extract text from response
            if not response_json.get("choices"):
                self.logger.error("No choices in OpenAI response")
                return results
                
            response_text = response_json["choices"][0]["message"]["content"]
            
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
            self.logger.error(f"Error parsing OpenAI response: {str(e)}")
        
        return results
