"""Scrape property listings from PropertyGuru Singapore"""

# src/services/scraper.py
# src/services/scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import logging
import re

logger = logging.getLogger(__name__)

class PropertyScraper:
    """Scrapes property listings from PropertyGuru Singapore"""
    
    def __init__(self):
        self.driver = None
    
    def _setup_driver(self):
        """Setup Selenium driver with Chrome"""
        if self.driver is None:
            chrome_options = Options()
            
            # Browser options
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # That's it! No binary_location needed
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium driver initialized with Chrome")
        
    def scrape_properties(self, url: str) -> List[Dict]:
        """Scrape property listings from PropertyGuru"""
        try:
            self._setup_driver()
            
            logger.info(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for listings to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[da-listing-id]')))
            
            # Scroll to load more listings
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Get page source and parse
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            properties = self._parse_listings(soup)
            
            logger.info(f"Successfully scraped {len(properties)} properties")
            return properties
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
            
    def _parse_listings(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse PropertyGuru listings"""
        properties = []
        
        # Find all property cards
        listings = soup.select('div[da-listing-id]')
        
        for listing in listings:
            try:
                property_data = {
                    'listing_id': self._get_listing_id(listing),
                    'title': self._get_title(listing),
                    'address': self._get_address(listing),
                    'price': self._get_price(listing),
                    'price_psf': self._get_price_psf(listing),
                    'bedrooms': self._get_bedrooms(listing),
                    'bathrooms': self._get_bathrooms(listing),
                    'area_sqft': self._get_area(listing),
                    'unit_type': self._get_unit_type(listing),
                    'availability': self._get_availability(listing),
                    'mrt_info': self._get_mrt_info(listing),
                    'agent_name': self._get_agent_name(listing),
                    'agency_name': self._get_agency_name(listing),
                    'url': self._get_url(listing),
                }
                
                properties.append(property_data)
                
            except Exception as e:
                logger.warning(f"Failed to parse listing: {str(e)}")
                continue
        
        return properties
    
    def _get_listing_id(self, listing) -> str:
        """Get listing ID"""
        return listing.get('da-listing-id', '')
    
    def _get_title(self, listing) -> str:
        """Get property title/estate name"""
        title_elem = listing.select_one('h3.listing-type-text')
        return title_elem.text.strip() if title_elem else ''
    
    def _get_address(self, listing) -> str:
        """Get property address"""
        address_elem = listing.select_one('p.listing-address')
        return address_elem.text.strip() if address_elem else ''
    
    def _get_price(self, listing) -> float:
        """Get property price"""
        price_div = listing.select_one('div.listing-price')
        price_text = price_div.text.strip() if price_div else ''
        return self._parse_price(price_text)
    
    def _get_price_psf(self, listing) -> float:
        """Get price per square foot"""
        price_psf_elem = listing.select_one('p.listing-ppa')
        price_psf_text = price_psf_elem.text.strip() if price_psf_elem else ''
        return self._parse_price(price_psf_text)
    
    def _get_bedrooms(self, listing) -> Optional[int]:
        """Get number of bedrooms"""
        bedrooms_elem = listing.select_one('div[da-id="listing-card-v2-bedrooms"] p')
        return self._parse_number(bedrooms_elem.text) if bedrooms_elem else None
    
    def _get_bathrooms(self, listing) -> Optional[int]:
        """Get number of bathrooms"""
        bathrooms_elem = listing.select_one('div[da-id="listing-card-v2-bathrooms"] p')
        return self._parse_number(bathrooms_elem.text) if bathrooms_elem else None
    
    def _get_area(self, listing) -> Optional[int]:
        """Get property area in sqft"""
        area_elem = listing.select_one('div[da-id="listing-card-v2-area"] p')
        if area_elem:
            # Extract number from "2,000 sqft"
            return self._parse_number(area_elem.text)
        return None
    
    def _get_unit_type(self, listing) -> str:
        """Get unit type (e.g., Corner Terrace)"""
        unit_type_elem = listing.select_one('div[da-id="listing-card-v2-unit-type"] p')
        return unit_type_elem.text.strip() if unit_type_elem else ''
    
    def _get_availability(self, listing) -> str:
        """Get availability status"""
        avail_elem = listing.select_one('div[da-id="listing-card-v2-availability"] p')
        return avail_elem.text.strip() if avail_elem else ''
    
    def _get_mrt_info(self, listing) -> str:
        """Get MRT proximity information"""
        mrt_elem = listing.select_one('div[da-id="listing-card-v2-mrt"] span.listing-location-value')
        return mrt_elem.text.strip() if mrt_elem else ''
    
    def _get_agent_name(self, listing) -> str:
        """Get agent name"""
        agent_elem = listing.select_one('span[da-id="listing-card-v2-agent-name"]')
        return agent_elem.text.strip() if agent_elem else ''
    
    def _get_agency_name(self, listing) -> str:
        """Get agency name"""
        agency_elem = listing.select_one('span[da-id="listing-card-v2-agency-name"]')
        return agency_elem.text.strip() if agency_elem else ''
    
    def _get_url(self, listing) -> str:
        """Get property listing URL"""
        link = listing.select_one('a.card-footer')
        url = link.get('href', '') if link else ''
        if url and not url.startswith('http'):
            url = f"https://www.propertyguru.com.sg{url}"
        return url
    
    def _parse_price(self, price_str: str) -> float:
        """Extract numeric price from string"""
        try:
            numbers = re.findall(r'[\d,]+\.?\d*', price_str)
            if numbers:
                return float(numbers[0].replace(',', ''))
            return 0.0
        except:
            return 0.0
    
    def _parse_number(self, text: str) -> Optional[int]:
        """Extract integer from text"""
        try:
            numbers = re.findall(r'\d+', text.replace(',', ''))
            return int(numbers[0]) if numbers else None
        except:
            return None