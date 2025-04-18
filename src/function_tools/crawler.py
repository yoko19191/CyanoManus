""" 
CyanoManus 



TOOLS_AVAILABLE: 


""" 



from agents import function_tool


from firecrawl import FirecrawlApp


from dotenv import find_dotenv, load_dotenv
import os 


############# INITIALIZE #############
_ = load_dotenv(find_dotenv())

firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

firecrawl_client = FirecrawlApp(
    api_key=firecrawl_api_key
)

############# End of INITIALIZE #############



############# FIRECRAWL_SCRAPE_URL #############


def firecrawl_scrape_url():
    """Turn any url into clean data
    To scrape a single URL, use the scrape_url method. It takes the URL as a parameter and returns the scraped data as a dictionary.
    
    """
    # Scrape a website:
    scrape_result = firecrawl_client.scrape_url(
        'firecrawl.dev', 
        params={'formats': ['markdown', 'html']}
    )
    print(scrape_result)
    
    
    
    
############# End of FIRECRAWL_SCRAPE_URL #############



############# FIRECRAWL_BATCH_SCRAPE #############

def firecrawl_batch_scrape():
    
    

############# End of FIRECRAWL_BATCH_SCRAPE #############


############# FIRECRAWL_BATCH_SCRAPE #############


