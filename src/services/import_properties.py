"""Script to scrape and import properties from PropertyGuru"""

import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.scrape_property import PropertyScraper
from services.property_service import PropertyService
from core.supabase_client import SupabaseClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_and_import(url: str, skip_duplicates: bool = True):
    """Scrape properties from URL and import to database"""
    logger.info(f"Starting scrape from: {url}")
    
    #Scrape properties
    scraper = PropertyScraper()
    try:
        properties = scraper.scrape_properties(url)
        logger.info(f"✅ Scraped {len(properties)} properties")
    except Exception as e:
        logger.error(f"❌ Scraping failed: {str(e)}")
        return
    
    if not properties:
        logger.warning("No properties found to import")
        return
    
    # Filter duplicates if needed
    if skip_duplicates:
        property_service = PropertyService()
        filtered_properties = []
        
        for prop in properties:
            listing_id = prop.get('listing_id')
            if listing_id and property_service.check_duplicate_listing(listing_id):
                logger.info(f"Skipping duplicate: {listing_id}")
            else:
                filtered_properties.append(prop)
        
        logger.info(f"Filtered to {len(filtered_properties)} new properties")
        properties = filtered_properties
    
    if not properties:
        logger.info("No new properties to import")
        return
       
    #Import to database
    property_service = PropertyService()
    try:
        result = property_service.bulk_insert_properties(properties)
        logger.info(f"✅ Import complete!")
        logger.info(f"   Inserted: {result['inserted']}/{result['total']}")
        
        if result['errors']:
            logger.warning(f"   Errors: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Show first 5 errors
                logger.warning(f"   - {error}")
    except Exception as e:
        logger.error(f"❌ Import failed: {str(e)}")

if __name__ == "__main__":
    # can change the url here
    url = "https://www.propertyguru.com.sg/property-for-rent"
    
    # can also accept URL from command line
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    scrape_and_import(url, skip_duplicates=True)