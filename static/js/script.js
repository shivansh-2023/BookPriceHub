document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const searchForm = document.getElementById('search-form');
    const bookTitleInput = document.getElementById('book-title');
    const formatRadios = document.querySelectorAll('input[name="format"]');
    const loadingSection = document.getElementById('loading-section');
    const resultsSection = document.getElementById('results-section');
    const noResultsSection = document.getElementById('no-results-section');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    const resultsContainer = document.getElementById('results-container');
    const sortBySelect = document.getElementById('sort-by');
    const bookDetailsModal = document.getElementById('book-details-modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.querySelector('.close-modal');
    
    // Templates
    const bookCardTemplate = document.getElementById('book-card-template');
    const bookDetailsTemplate = document.getElementById('book-details-template');
    
    // Current search results
    let currentResults = [];
    
    // Event Listeners
    searchForm.addEventListener('submit', handleSearch);
    sortBySelect.addEventListener('change', handleSort);
    closeModal.addEventListener('click', closeBookDetailsModal);
    window.addEventListener('click', function(event) {
        if (event.target === bookDetailsModal) {
            closeBookDetailsModal();
        }
    });
    
    // Handle search form submission
    function handleSearch(event) {
        event.preventDefault();
        
        const bookTitle = bookTitleInput.value.trim();
        if (!bookTitle) {
            showError('Please enter a book title');
            return;
        }
        
        // Get selected format
        let selectedFormat = 'all';
        formatRadios.forEach(radio => {
            if (radio.checked) {
                selectedFormat = radio.value;
            }
        });
        
        // Show loading section, hide others
        hideAllSections();
        loadingSection.style.display = 'block';
        
        // Make API request
        searchBooks(bookTitle, selectedFormat);
    }
    
    // Search books API call
    function searchBooks(title, format) {
        console.log('Sending search request for:', title, 'format:', format);
        
        fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                format: format
            })
        })
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);
            currentResults = data.results;
            displayResults(data);
        })
        .catch(error => {
            console.error('Error details:', error);
            showError(`Failed to fetch results: ${error.message}. Please try again later.`);
        });
    }
    
    /**
     * Display search results in the UI
     * @param {Object} data - Search results data
     */
    function displayResults(data) {
        console.log("Displaying results:", data);
        
        // Hide loading section and other sections that might be visible
        hideAllSections();
        
        // Show results section
        const resultsSection = document.getElementById('results-section');
        if (resultsSection) {
            resultsSection.style.display = 'block';
        }
        
        const resultsContainer = document.getElementById('results-container');
        if (!resultsContainer) {
            console.error("Results container element not found!");
            return;
        }
        
        resultsContainer.innerHTML = '';
        
        if (!data.results || data.results.length === 0 || data.count === 0) {
            // Show no results section
            const noResultsSection = document.getElementById('no-results-section');
            if (noResultsSection) {
                noResultsSection.style.display = 'block';
            }
            return;
        }
        
        // Create result cards
        data.results.forEach(book => {
            // Create book card using DOM methods instead of templates
            const card = document.createElement('div');
            card.className = 'book-card';
            
            // Create image section
            const imageDiv = document.createElement('div');
            imageDiv.className = 'book-image';
            
            const image = document.createElement('img');
            // Use the first source's image or a placeholder
            image.src = (book.sources && book.sources.length > 0 && book.sources[0].image_url) 
                ? book.sources[0].image_url 
                : 'static/img/book-placeholder.png';
            image.alt = book.title;
            
            imageDiv.appendChild(image);
            
            // Create info section
            const infoDiv = document.createElement('div');
            infoDiv.className = 'book-info';
            
            const title = document.createElement('h3');
            title.className = 'book-title';
            title.textContent = book.title;
            
            const author = document.createElement('p');
            author.className = 'book-author';
            if (book.sources && book.sources.length > 0) {
                author.textContent = book.sources[0].author || 'Unknown Author';
            } else {
                author.textContent = 'Unknown Author';
            }
            
            // Create price comparison section
            const priceDiv = document.createElement('div');
            priceDiv.className = 'price-comparison';
            
            // Find best price
            let bestPrice = 'Not available';
            let bestSource = null;
            
            if (book.sources && book.sources.length > 0) {
                for (const source of book.sources) {
                    if (source.best_price) {
                        bestPrice = source.price || 'Price not available';
                        bestSource = source;
                        break;
                    }
                }
            }
            
            const bestPriceDiv = document.createElement('div');
            bestPriceDiv.className = 'best-price';
            
            const bestPriceLabel = document.createElement('span');
            bestPriceLabel.className = 'best-price-label';
            bestPriceLabel.textContent = 'Best Price';
            
            const bestPriceValue = document.createElement('span');
            bestPriceValue.className = 'best-price-value';
            bestPriceValue.textContent = bestPrice;
            
            bestPriceDiv.appendChild(bestPriceLabel);
            bestPriceDiv.appendChild(bestPriceValue);
            
            // Create Compare button
            const compareButton = document.createElement('button');
            compareButton.className = 'compare-button';
            compareButton.textContent = 'Compare All Prices';
            compareButton.addEventListener('click', function() {
                openBookDetailsModal(book);
            });
            
            // Assemble price comparison section
            priceDiv.appendChild(bestPriceDiv);
            priceDiv.appendChild(compareButton);
            
            // Assemble info section
            infoDiv.appendChild(title);
            infoDiv.appendChild(author);
            infoDiv.appendChild(priceDiv);
            
            // Assemble card
            card.appendChild(imageDiv);
            card.appendChild(infoDiv);
            
            // Add card to results container
            resultsContainer.appendChild(card);
        });
    }
    
    /**
     * Open book details modal
     * @param {Object} book - Book object
     */
    function openBookDetailsModal(book) {
        console.log("Opening details for book:", book);
        
        const modal = document.getElementById('book-details-modal');
        const modalBody = document.getElementById('modal-body');
        
        if (!modal || !modalBody) {
            console.error("Modal elements not found!");
            return;
        }
        
        // Clear previous modal content
        modalBody.innerHTML = '';
        
        // Create book details using the template
        const template = document.getElementById('book-details-template');
        if (!template) {
            console.error("Book details template not found!");
            return;
        }
        
        const bookDetails = template.content.cloneNode(true);
        
        // Set book details
        const titleEl = bookDetails.querySelector('.book-details-title');
        if (titleEl) titleEl.textContent = book.title;
        
        const authorEl = bookDetails.querySelector('.book-details-author');
        if (authorEl) {
            if (book.sources && book.sources.length > 0) {
                authorEl.textContent = book.sources[0].author || 'Unknown Author';
            } else {
                authorEl.textContent = 'Unknown Author';
            }
        }
        
        // Set image
        const imageEl = bookDetails.querySelector('.book-details-image img');
        if (imageEl) {
            if (book.sources && book.sources.length > 0 && book.sources[0].image_url) {
                imageEl.src = book.sources[0].image_url;
            } else {
                imageEl.src = 'static/img/book-placeholder.png';
            }
            imageEl.alt = book.title;
        }
        
        // Add price rows to table
        const tableBody = bookDetails.querySelector('.price-table-body');
        if (tableBody) {
            if (book.sources && book.sources.length > 0) {
                book.sources.forEach(source => {
                    const row = document.createElement('tr');
                    
                    // Format links properly
                    let buyLink = source.link || '#';
                    if (buyLink.startsWith('//')) {
                        buyLink = 'https://' + buyLink.replace(/^\/\//, '');
                    }
                    
                    // Create buy button based on link availability
                    let buyButtonHTML = '';
                    if (buyLink && buyLink !== '#') {
                        buyButtonHTML = `<a href="${buyLink}" target="_blank" class="buy-button">Buy Now</a>`;
                    } else {
                        buyButtonHTML = `<button class="buy-button disabled" disabled>Not Available</button>`;
                    }
                    
                    row.innerHTML = `
                        <td>${source.source}</td>
                        <td>${source.format || 'Unknown'}</td>
                        <td>${source.price || 'Price not available'}</td>
                        <td>${buyButtonHTML}</td>
                    `;
                    
                    tableBody.appendChild(row);
                });
            } else {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="4" class="no-results">No price information available</td>';
                tableBody.appendChild(row);
            }
        }
        
        // Handle ebook availability if present
        const ebookSources = bookDetails.querySelector('.ebook-sources');
        if (ebookSources) {
            // Clear previous content
            ebookSources.innerHTML = '';
            
            // Find ebook sources
            const ebookResults = book.sources ? book.sources.filter(s => s.format === 'Ebook') : [];
            
            if (ebookResults.length > 0) {
                ebookResults.forEach(source => {
                    const ebookSource = document.createElement('div');
                    ebookSource.className = 'ebook-source';
                    
                    // Format links properly
                    let viewLink = source.link || '#';
                    if (viewLink.startsWith('//')) {
                        viewLink = 'https://' + viewLink.replace(/^\/\//, '');
                    }
                    
                    // Create view button based on link availability
                    let viewButtonHTML = '';
                    if (viewLink && viewLink !== '#') {
                        viewButtonHTML = `<a href="${viewLink}" target="_blank" class="ebook-source-link">View</a>`;
                    } else {
                        viewButtonHTML = `<button class="ebook-source-link disabled" disabled>Not Available</button>`;
                    }
                    
                    ebookSource.innerHTML = `
                        <div class="ebook-source-name">${source.source}</div>
                        ${viewButtonHTML}
                    `;
                    
                    ebookSources.appendChild(ebookSource);
                });
            } else {
                ebookSources.innerHTML = '<div class="no-results">No ebook options available</div>';
            }
        }
        
        // Handle free ebook sources if present
        const freeEbookSources = bookDetails.querySelector('.free-ebook-sources');
        if (freeEbookSources) {
            // Clear previous content
            freeEbookSources.innerHTML = '';
            
            // Find free ebook sources (assuming 'free: true' flag in the source)
            const freeEbookResults = book.sources ? book.sources.filter(s => s.free === true) : [];
            
            if (freeEbookResults.length > 0) {
                freeEbookResults.forEach(source => {
                    const freeEbookSource = document.createElement('div');
                    freeEbookSource.className = 'free-ebook-source';
                    
                    // Format links properly
                    let viewLink = source.link || '#';
                    if (viewLink.startsWith('//')) {
                        viewLink = 'https://' + viewLink.replace(/^\/\//, '');
                    }
                    
                    // Create view button based on link availability
                    let viewButtonHTML = '';
                    if (viewLink && viewLink !== '#') {
                        viewButtonHTML = `<a href="${viewLink}" target="_blank" class="free-ebook-source-link">View</a>`;
                    } else {
                        viewButtonHTML = `<button class="free-ebook-source-link disabled" disabled>Not Available</button>`;
                    }
                    
                    freeEbookSource.innerHTML = `
                        <div class="free-ebook-source-name">${source.source}</div>
                        ${viewButtonHTML}
                    `;
                    
                    freeEbookSources.appendChild(freeEbookSource);
                });
            } else {
                freeEbookSources.innerHTML = '<div class="no-results">No free ebook options available</div>';
            }
        }
        
        // Add details to modal
        modalBody.appendChild(bookDetails);
        
        // Show modal
        modal.style.display = 'block';
        
        // Add close functionality
        const closeBtn = modal.querySelector('.close-modal');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                modal.style.display = 'none';
            });
        }
        
        // Close modal when clicking outside
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
    
    /**
     * Hide all content sections
     */
    function hideAllSections() {
        const sections = [
            'loading-section',
            'results-section',
            'no-results-section',
            'error-section'
        ];
        
        sections.forEach(id => {
            const section = document.getElementById(id);
            if (section) {
                section.style.display = 'none';
            }
        });
    }
    
    // Handle sorting
    function handleSort() {
        if (currentResults.length > 0) {
            sortResults(currentResults, sortBySelect.value);
            displayResults({ results: currentResults });
        }
    }
    
    // Sort results
    function sortResults(results, sortBy) {
        switch (sortBy) {
            case 'price-asc':
                results.sort((a, b) => {
                    const priceA = getBestPrice(a.sources);
                    const priceB = getBestPrice(b.sources);
                    return priceA - priceB;
                });
                break;
            case 'price-desc':
                results.sort((a, b) => {
                    const priceA = getBestPrice(a.sources);
                    const priceB = getBestPrice(b.sources);
                    return priceB - priceA;
                });
                break;
            case 'title-asc':
                results.sort((a, b) => a.title.localeCompare(b.title));
                break;
            case 'title-desc':
                results.sort((a, b) => b.title.localeCompare(a.title));
                break;
        }
    }
    
    // Get best price from sources
    function getBestPrice(sources) {
        let bestPrice = Infinity;
        
        for (const source of sources) {
            if (source.price_value !== undefined && source.price_value < bestPrice) {
                bestPrice = source.price_value;
            }
        }
        
        return bestPrice === Infinity ? 999999 : bestPrice;
    }
    
    // Show error message
    function showError(message) {
        errorMessage.textContent = message;
        errorSection.style.display = 'block';
    }
    
    // Close book details modal
    function closeBookDetailsModal() {
        bookDetailsModal.style.display = 'none';
    }
});
