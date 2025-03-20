# BookPriceHub - Book Price Comparison Tool

BookPriceHub is a web application that allows users to search for books across multiple retailers and compare prices to find the best deals. The application also checks for ebook availability and provides links to legally download free ebooks when available.

## Features

- **Simple Search**: Enter a book title to search across major retailers
- **Price Comparison**: View prices from Amazon, Barnes & Noble, Book Depository, Books-A-Million, and more
- **Format Filtering**: Filter results by format (hardcover, paperback, ebook, audiobook)
- **Ebook Availability**: Check for ebook availability across platforms (Kindle, Kobo, Google Books)
- **Free Ebook Sources**: Find legally free ebooks from sources like Project Gutenberg and Open Library
- **Responsive Design**: Works on desktop and mobile devices
- **Caching**: Recent search results are cached for improved performance

## Technical Implementation

- **Backend**: Python with Flask web framework
- **Frontend**: HTML, CSS, JavaScript
- **Data Collection**: Web scraping with BeautifulSoup and requests
- **Rate Limiting**: Implemented to avoid overloading retailer websites
- **User Agent Rotation**: Prevents detection of scraping activities
- **Caching**: TTL-based caching system for search results

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/bookpricehub.git
cd bookpricehub
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. Enter a book title in the search box
2. Optionally select a format filter (All, Hardcover, Paperback, Ebook, Audiobook)
3. Click the "Search" button
4. View the search results with the best price highlighted
5. Click "Compare All Prices" to see detailed price comparison and retailer links
6. Sort results by price or title using the sort dropdown

## Privacy and Security

- No user login required for basic functionality
- No storage of user search history on servers
- All data is fetched in real-time from retailer websites
- No personal information is collected or stored

## Disclaimer

This application is for educational purposes only. Please respect the terms of service of all retailer websites. The application implements appropriate rate limiting and user agent rotation to minimize impact on the scraped websites.

## License

MIT License
