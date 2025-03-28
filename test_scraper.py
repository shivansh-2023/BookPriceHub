from scrapers.barnes_noble import BarnesNobleScraper
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize scraper
scraper = BarnesNobleScraper()

# Search for a book
results = scraper.search('The Great Gatsby')

# Print results
print('\nSearch Results:')
for result in results:
    print(f"\nTitle: {result.get('title', 'N/A')}")
    print(f"Author: {result.get('author', 'N/A')}")
    print(f"Price: {result.get('price', 'N/A')}")
    print(f"Format: {result.get('format', 'N/A')}")
    print(f"Link: {result.get('link', 'N/A')}")