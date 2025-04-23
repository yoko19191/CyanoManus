from agents import function_tool

from dotenv import find_dotenv, load_dotenv
import os
from typing import Dict, Any, List, Optional, Union
import json # Added for formatting results

_ = load_dotenv(find_dotenv())

from firecrawl import FirecrawlApp

# Ensure API key is loaded
api_key = os.getenv("FIRECRAWL_API_KEY")
if not api_key:
    raise ValueError("FIRECRAWL_API_KEY not found in environment variables.")

app = FirecrawlApp(api_key=api_key)


# --- Helper Functions ---

def _format_mcp_response(result: Any, is_error: bool = False) -> Dict[str, Any]:
    """Formats the result into the MCP response structure."""
    if is_error:
        text_content = f"Error: {str(result)}"
    elif isinstance(result, (dict, list)):
        # Pretty print JSON for readability
        try:
            text_content = json.dumps(result, indent=2, ensure_ascii=False)
        except TypeError: # Handle potential non-serializable data
            text_content = str(result)
    else:
        text_content = str(result)

    return {
        'content': [{'type': 'text', 'text': text_content}],
        'isError': is_error
    }

def _create_params_dict(**kwargs) -> Dict[str, Any]:
    """
    Creates a dictionary of parameters for the FirecrawlApp methods,
    excluding None values and _meta, and handling nested option structures.
    """
    params = {k: v for k, v in kwargs.items() if v is not None and k != '_meta'}

    # --- Handle pageOptions for scrape ---
    page_options_keys = {
        'formats', 'onlyMainContent', 'includeTags', 'excludeTags',
        'waitFor', 'timeout', 'actions', 'extract', 'mobile',
        'skipTlsVerification', 'removeBase64Images', 'location'
    }
    page_options = {k: params.pop(k) for k in page_options_keys if k in params}
    if page_options:
        # For scrape, pageOptions is passed directly
        # For crawl/search, it's nested within scrapeOptions or passed separately
        # We'll handle nesting later based on the calling function context if needed
        pass # Keep page_options separate for now

    # --- Handle scrapeOptions for crawl and search ---
    # If scrapeOptions dict is explicitly passed, use it
    if 'scrapeOptions' in params and isinstance(params['scrapeOptions'], dict):
        # User provided the full dict, prioritize it
        # Remove individual scrape-related keys if they were also passed,
        # as they are now superseded by the scrapeOptions dict.
        individual_scrape_keys = page_options_keys # Same keys apply
        for key in individual_scrape_keys:
            params.pop(key, None) # Remove if present
        # Also remove the page_options we extracted earlier if scrapeOptions is given
        page_options = {}
    else:
        # Construct scrapeOptions from individual args if scrapeOptions dict is not provided
        # Use the page_options we potentially extracted earlier
        if page_options:
            params['scrapeOptions'] = page_options
        # Remove the now-redundant top-level scrapeOptions key if it was None
        params.pop('scrapeOptions', None)


    # --- Handle crawlerOptions for crawl ---
    crawler_options_keys = {
        'excludePaths', 'includePaths', 'maxDepth', 'ignoreSitemap', 'limit',
        'allowBackwardLinks', 'allowExternalLinks', 'webhook',
        'deduplicateSimilarURLs', 'ignoreQueryParameters'
    }
    crawler_options = {k: params.pop(k) for k in crawler_options_keys if k in params}
    if crawler_options:
        params['crawlerOptions'] = crawler_options

    # --- Handle pageOptions for search (merging specific search params) ---
    search_page_options_keys = {
        'limit', 'lang', 'country', 'tbs', 'filter', 'location' # location is also a pageOption key
    }
    search_page_options = {k: params.pop(k) for k in search_page_options_keys if k in params}
    if search_page_options:
        # Search uses pageOptions for these. Merge with existing page_options if any.
        # If scrapeOptions was built, these search params go into pageOptions *within* scrapeOptions
        if 'scrapeOptions' in params and isinstance(params['scrapeOptions'], dict):
            params['scrapeOptions']['pageOptions'] = params['scrapeOptions'].get('pageOptions', {})
            params['scrapeOptions']['pageOptions'].update(search_page_options)
        else:
            # If no scrapeOptions, merge into the top-level page_options dict
            page_options.update(search_page_options)
            if page_options: # Ensure page_options exists if we added to it
                params['pageOptions'] = page_options


    # --- Handle extractionOptions for extract ---
    extract_options_keys = {
        'prompt', 'systemPrompt', 'schema', 'allowExternalLinks',
        'enableWebSearch', 'includeSubdomains'
    }
    extraction_options = {k: params.pop(k) for k in extract_options_keys if k in params}
    if extraction_options:
        params['extractionOptions'] = extraction_options

    # --- Handle llmsOptions for generate_llmstxt ---
    llmstxt_options_keys = {'maxUrls', 'showFullText'}
    llmstxt_options = {k: params.pop(k) for k in llmstxt_options_keys if k in params}
    if llmstxt_options:
        # Assuming the library uses 'llmsOptions' based on common patterns
        params['llmsOptions'] = llmstxt_options

    # Return the main params dict and the separated page_options (for scrape)
    # The calling function will decide how to use page_options
    return params, page_options


# --- Tool Functions ---

@function_tool
async def firecrawl_scrape(
    url: str,
    formats: Optional[List[str]] = ['markdown'], # Default as per original doc
    onlyMainContent: Optional[bool] = None,
    includeTags: Optional[List[str]] = None,
    excludeTags: Optional[List[str]] = None,
    waitFor: Optional[int] = None,
    timeout: Optional[int] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    extract: Optional[Dict[str, Any]] = None,
    mobile: Optional[bool] = None,
    skipTlsVerification: Optional[bool] = None,
    removeBase64Images: Optional[bool] = None,
    location: Optional[Dict[str, Any]] = None,
    _meta: Optional[Dict[str, Any]] = None # Metadata is captured but not passed to firecrawl
) -> Dict[str, Any]:
    """
    Scrapes a single webpage with advanced options for content extraction.

    Supports various formats including markdown, HTML, and screenshots.
    Can execute custom actions like clicking or scrolling before scraping.

    Args:
        url (str): The URL to scrape (required).
        formats (Optional[List[str]]): Content formats to extract
            (e.g., ['markdown', 'html']). Defaults to ['markdown'].
        onlyMainContent (Optional[bool]): Extract only main content.
        includeTags (Optional[List[str]]): HTML tags to specifically include.
        excludeTags (Optional[List[str]]): HTML tags to exclude.
        waitFor (Optional[int]): Milliseconds to wait for dynamic content.
        timeout (Optional[int]): Max milliseconds for page load.
        actions (Optional[List[Dict[str, Any]]]): Actions to perform before scraping.
        extract (Optional[Dict[str, Any]]): Configuration for structured data extraction.
        mobile (Optional[bool]): Use mobile viewport.
        skipTlsVerification (Optional[bool]): Skip TLS verification.
        removeBase64Images (Optional[bool]): Remove base64 images.
        location (Optional[Dict[str, Any]]): Location settings.
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains the scraped data as a JSON string.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not url:
        return _format_mcp_response("Error: 'url' parameter is required.", is_error=True)

    try:
        # Pass all relevant args to _create_params_dict
        params, page_options = _create_params_dict(
            formats=formats, onlyMainContent=onlyMainContent, includeTags=includeTags,
            excludeTags=excludeTags, waitFor=waitFor, timeout=timeout, actions=actions,
            extract=extract, mobile=mobile, skipTlsVerification=skipTlsVerification,
            removeBase64Images=removeBase64Images, location=location
        )
        # The ascrape_url method expects page_options as a separate argument
        result = await app.ascrape_url(url, params=params, page_options=page_options)
        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)


@function_tool
async def firecrawl_map(
    url: str,
    search: Optional[str] = None,
    _meta: Optional[Dict[str, Any]] = None # Metadata is captured but not passed to firecrawl
) -> Dict[str, Any]:
    """
    Maps a website to retrieve all accessible URLs, optionally filtering by a search query.

    Useful for getting a sitemap or finding specific pages before scraping/crawling.

    Args:
        url (str): The base URL of the website to map (required).
        search (Optional[str]): A query to filter URLs. Returns URLs most relevant to the query.
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains a list of URLs as a JSON string.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not url:
        return _format_mcp_response("Error: 'url' parameter is required.", is_error=True)

    try:
        params, _ = _create_params_dict(search=search) # Only search is relevant here
        result = await app.amap_url(url, params=params)
        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)


@function_tool
async def firecrawl_crawl(
    url: str,
    # --- Crawler Options ---
    excludePaths: Optional[List[str]] = None,
    includePaths: Optional[List[str]] = None,
    maxDepth: Optional[int] = None,
    ignoreSitemap: Optional[bool] = None,
    limit: Optional[int] = None, # Also a pageOption for search
    allowBackwardLinks: Optional[bool] = None,
    allowExternalLinks: Optional[bool] = None,
    webhook: Optional[Dict[str, Any]] = None,
    deduplicateSimilarURLs: Optional[bool] = None,
    ignoreQueryParameters: Optional[bool] = None,
    # --- Scrape Options (passed within crawl) ---
    formats: Optional[List[str]] = ['markdown'], # Default as per original doc
    onlyMainContent: Optional[bool] = None,
    includeTags: Optional[List[str]] = None,
    excludeTags: Optional[List[str]] = None,
    waitFor: Optional[int] = None,
    timeout: Optional[int] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    extract: Optional[Dict[str, Any]] = None,
    mobile: Optional[bool] = None,
    skipTlsVerification: Optional[bool] = None,
    removeBase64Images: Optional[bool] = None,
    location: Optional[Dict[str, Any]] = None, # Also a pageOption key
    # --- Explicit ScrapeOptions Dict (overrides individual args) ---
    scrapeOptions: Optional[Dict[str, Any]] = None,
    # --- Metadata ---
    _meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Crawls a website starting from a URL, scraping content from discovered pages.

    Recursively follows links (configurable depth and scope) and extracts data
    in specified formats. Supports advanced scraping options for each page.

    Args:
        url (str): The starting URL for the crawl (required).
        excludePaths (Optional[List[str]]): URL paths to exclude from crawling.
        includePaths (Optional[List[str]]): Specific URL paths to include.
        maxDepth (Optional[int]): Maximum crawl depth relative to the start URL.
        ignoreSitemap (Optional[bool]): Ignore the website's sitemap.xml.
        limit (Optional[int]): Maximum number of pages to crawl.
        allowBackwardLinks (Optional[bool]): Allow crawling links outside the initial path scope.
        allowExternalLinks (Optional[bool]): Allow crawling links to external domains.
        webhook (Optional[Dict[str, Any]]): Webhook configuration for crawl completion.
        deduplicateSimilarURLs (Optional[bool]): Deduplicate URLs with minor variations.
        ignoreQueryParameters (Optional[bool]): Ignore URL query parameters during crawl.
        formats (Optional[List[str]]): Content formats for scraped pages (e.g., ['markdown']).
        onlyMainContent (Optional[bool]): Extract only main content from scraped pages.
        includeTags (Optional[List[str]]): HTML tags to include in scraped content.
        excludeTags (Optional[List[str]]): HTML tags to exclude from scraped content.
        waitFor (Optional[int]): Milliseconds to wait for dynamic content on scraped pages.
        timeout (Optional[int]): Max milliseconds for page load during scraping.
        actions (Optional[List[Dict[str, Any]]]): Actions to perform before scraping each page.
        extract (Optional[Dict[str, Any]]): Structured data extraction config for scraped pages.
        mobile (Optional[bool]): Use mobile viewport for scraping.
        skipTlsVerification (Optional[bool]): Skip TLS verification during scraping.
        removeBase64Images (Optional[bool]): Remove base64 images from scraped content.
        location (Optional[Dict[str, Any]]): Location settings for scraping.
        scrapeOptions (Optional[Dict[str, Any]]): A dictionary containing scrape options,
            overriding individual scrape-related arguments if provided.
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains the crawl job ID or results as a JSON string.
                        Note: Crawl is often asynchronous; this might return a job ID.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not url:
        return _format_mcp_response("Error: 'url' parameter is required.", is_error=True)

    try:
        # Pass all relevant args to _create_params_dict
        params, _ = _create_params_dict(
            # Crawler Options
            excludePaths=excludePaths, includePaths=includePaths, maxDepth=maxDepth,
            ignoreSitemap=ignoreSitemap, limit=limit, allowBackwardLinks=allowBackwardLinks,
            allowExternalLinks=allowExternalLinks, webhook=webhook,
            deduplicateSimilarURLs=deduplicateSimilarURLs,
            ignoreQueryParameters=ignoreQueryParameters,
            # Scrape Options (will be nested under 'scrapeOptions' by the helper)
            formats=formats, onlyMainContent=onlyMainContent, includeTags=includeTags,
            excludeTags=excludeTags, waitFor=waitFor, timeout=timeout, actions=actions,
            extract=extract, mobile=mobile, skipTlsVerification=skipTlsVerification,
            removeBase64Images=removeBase64Images, location=location,
            # Explicit scrapeOptions dict (if provided)
            scrapeOptions=scrapeOptions
        )
        # The acrawl_url method expects crawlerOptions and scrapeOptions within the params dict
        result = await app.acrawl_url(url, params=params, wait_until_done=True) # Wait for completion
        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)


@function_tool
async def firecrawl_search(
    query: str,
    # --- Search Page Options ---
    limit: Optional[int] = None, # Max search results
    lang: Optional[str] = None,
    country: Optional[str] = None,
    tbs: Optional[str] = None, # Time Based Search (e.g., 'qdr:d' for past day)
    filter: Optional[str] = None, # Additional search filters
    location: Optional[Dict[str, Any]] = None, # Location for search results (also a scrape pageOption)
    # --- Scrape Options (for scraping results) ---
    formats: Optional[List[str]] = None, # ['markdown', 'html', 'links', etc.]
    onlyMainContent: Optional[bool] = None,
    includeTags: Optional[List[str]] = None,
    excludeTags: Optional[List[str]] = None,
    waitFor: Optional[int] = None,
    timeout: Optional[int] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    extract: Optional[Dict[str, Any]] = None,
    mobile: Optional[bool] = None,
    skipTlsVerification: Optional[bool] = None,
    removeBase64Images: Optional[bool] = None,
    # --- Explicit ScrapeOptions Dict (overrides individual args) ---
    scrapeOptions: Optional[Dict[str, Any]] = None,
    # --- Metadata ---
    _meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Performs a web search and optionally scrapes the content of the search results.

    Args:
        query (str): The search query (required).
        limit (Optional[int]): Maximum number of search results to return.
        lang (Optional[str]): Language code for the search (e.g., 'en').
        country (Optional[str]): Country code for the search (e.g., 'US').
        tbs (Optional[str]): Time-based search filter (e.g., 'qdr:d' for past day).
        filter (Optional[str]): Additional search filters.
        location (Optional[Dict[str, Any]]): Location settings for search results.
        formats (Optional[List[str]]): Content formats if scraping results (e.g., ['markdown']).
        onlyMainContent (Optional[bool]): Extract only main content when scraping results.
        includeTags (Optional[List[str]]): HTML tags to include when scraping results.
        excludeTags (Optional[List[str]]): HTML tags to exclude when scraping results.
        waitFor (Optional[int]): Milliseconds to wait for dynamic content when scraping results.
        timeout (Optional[int]): Max milliseconds for page load during result scraping.
        actions (Optional[List[Dict[str, Any]]]): Actions to perform before scraping results.
        extract (Optional[Dict[str, Any]]): Structured data extraction config for scraped results.
        mobile (Optional[bool]): Use mobile viewport for scraping results.
        skipTlsVerification (Optional[bool]): Skip TLS verification during result scraping.
        removeBase64Images (Optional[bool]): Remove base64 images when scraping results.
        scrapeOptions (Optional[Dict[str, Any]]): A dictionary containing scrape options,
            overriding individual scrape-related arguments if provided. Used if scraping results.
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains search results (and potentially scraped content)
                        as a JSON string.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not query:
        return _format_mcp_response("Error: 'query' parameter is required.", is_error=True)

    try:
        # Pass all relevant args to _create_params_dict
        params, _ = _create_params_dict(
            # Search Page Options (will be nested under 'pageOptions' by the helper)
            limit=limit, lang=lang, country=country, tbs=tbs, filter=filter, location=location,
            # Scrape Options (will be nested under 'scrapeOptions' by the helper)
            formats=formats, onlyMainContent=onlyMainContent, includeTags=includeTags,
            excludeTags=excludeTags, waitFor=waitFor, timeout=timeout, actions=actions,
            extract=extract, mobile=mobile, skipTlsVerification=skipTlsVerification,
            removeBase64Images=removeBase64Images,
             # Explicit scrapeOptions dict (if provided)
            scrapeOptions=scrapeOptions
        )
        # The asearch method expects pageOptions and scrapeOptions within the params dict
        result = await app.asearch(query, params=params)
        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)


@function_tool
async def firecrawl_extract(
    urls: List[str],
    prompt: Optional[str] = None,
    schema: Optional[Dict[str, Any]] = None, # JSON Schema
    # --- Extraction Options ---
    systemPrompt: Optional[str] = None,
    allowExternalLinks: Optional[bool] = None,
    enableWebSearch: Optional[bool] = None,
    includeSubdomains: Optional[bool] = None,
    # --- Metadata ---
    _meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extracts structured data from one or multiple URLs using LLMs based on a prompt or schema.

    Supports wildcards in URLs (e.g., 'example.com/*').

    Args:
        urls (List[str]): A list of URLs or URL patterns to extract data from (required).
        prompt (Optional[str]): Natural language prompt describing the data to extract.
            Required if 'schema' is not provided.
        schema (Optional[Dict[str, Any]]): JSON schema defining the structure of the data to extract.
            Required if 'prompt' is not provided.
        systemPrompt (Optional[str]): System prompt to guide the LLM extraction process.
        allowExternalLinks (Optional[bool]): Allow extraction to follow links outside the specified domain.
        enableWebSearch (Optional[bool]): Enable web search during extraction if needed.
        includeSubdomains (Optional[bool]): Include subdomains when using wildcard URLs.
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains the extracted structured data as a JSON string.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not urls:
        return _format_mcp_response("Error: 'urls' parameter is required.", is_error=True)
    if not prompt and not schema:
         return _format_mcp_response("Error: Either 'prompt' or 'schema' parameter is required.", is_error=True)

    try:
        # Pass all relevant args to _create_params_dict
        params, _ = _create_params_dict(
            prompt=prompt, schema=schema,
            # Extraction Options (will be nested under 'extractionOptions' by the helper)
            systemPrompt=systemPrompt, allowExternalLinks=allowExternalLinks,
            enableWebSearch=enableWebSearch, includeSubdomains=includeSubdomains
        )
        # The aextract method expects extractionOptions within the params dict
        result = await app.aextract(urls=urls, params=params, wait_until_done=True) # Wait for completion
        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)


@function_tool
async def firecrawl_llmstxt(
    url: str,
    maxUrls: Optional[int] = None,
    showFullText: Optional[bool] = None,
    _meta: Optional[Dict[str, Any]] = None # Metadata is captured but not passed to firecrawl
) -> Dict[str, Any]:
    """
    Generates an llms.txt summary for a given URL or domain.

    llms.txt provides instructions for LLMs on how to interact with a website.

    Args:
        url (str): The URL or domain to generate llms.txt for (required).
        maxUrls (Optional[int]): Maximum number of URLs to consider when generating the summary.
        showFullText (Optional[bool]): Include full text content in the summary (can be large).
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': llms_txt_content}], 'isError': False}
                        where 'llms_txt_content' is the generated llms.txt as a string.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not url:
        return _format_mcp_response("Error: 'url' parameter is required.", is_error=True)

    try:
        # Pass all relevant args to _create_params_dict
        params, _ = _create_params_dict(
            # LLMs.txt Options (will be nested under 'llmsOptions' by the helper)
            maxUrls=maxUrls, showFullText=showFullText
        )
        # The allmstxt method expects llmsOptions within the params dict
        result = await app.allmstxt(url, params=params)
        # llms.txt usually returns plain text, format it directly
        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)

# Note: Deep Research and Generate LLMs.txt are less common/potentially enterprise features.
# Assuming methods exist based on documentation/common patterns. Adjust if needed.

@function_tool
async def firecrawl_deep_research(
    query: str,
    maxDepth: Optional[int] = None, # e.g., 1-10
    timeLimit: Optional[int] = None, # e.g., 30-300 seconds
    maxUrls: Optional[int] = None, # e.g., 1-1000
    _meta: Optional[Dict[str, Any]] = None # Metadata captured but not passed
) -> Dict[str, Any]:
    """
    Conducts deep research on a query using web crawling, search, and AI analysis.
    (Note: This might be a higher-tier feature of Firecrawl)

    Args:
        query (str): The query to research (required).
        maxDepth (Optional[int]): Max depth of research iterations (e.g., 1-10).
        timeLimit (Optional[int]): Time limit in seconds (e.g., 30-300).
        maxUrls (Optional[int]): Max number of URLs to analyze (e.g., 1-1000).
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains the final analysis from the research.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not query:
        return _format_mcp_response("Error: 'query' parameter is required.", is_error=True)

    try:
        # Assuming these are passed as direct kwargs or within an options dict.
        params, _ = _create_params_dict(
            maxDepth=maxDepth, timeLimit=timeLimit, maxUrls=maxUrls
        )

        # Assuming an async method like 'adeep_research' exists.
        if hasattr(app, 'adeep_research'):
            result = await app.adeep_research(query, **params)
        elif hasattr(app, 'deep_research'): # Fallback sync
            result = app.deep_research(query, **params)
        else:
            return _format_mcp_response("Error: FirecrawlApp does not have 'adeep_research' or 'deep_research' method.", is_error=True)

        return _format_mcp_response(result)
    except Exception as e:
        return _format_mcp_response(e, is_error=True)


@function_tool
async def firecrawl_generate_llmstxt(
    url: str,
    maxUrls: Optional[int] = 10, # Default from original doc
    showFullText: Optional[bool] = False, # Default from original doc
    _meta: Optional[Dict[str, Any]] = None # Metadata captured but not passed
) -> Dict[str, Any]:
    """
    Generates a standardized LLMs.txt file for a given URL.

    Provides context about how LLMs should interact with the website.
    (Note: This might be a newer or specific feature of Firecrawl)

    Args:
        url (str): The URL to generate LLMs.txt from (required).
        maxUrls (Optional[int]): Max URLs to process (1-100, default: 10).
        showFullText (Optional[bool]): Show LLMs-full.txt in response (default: False).
        _meta (Optional[Dict[str, Any]]): Metadata (ignored by the function).

    Returns:
        Dict[str, Any]: A dictionary representing the MCP response format.
            On success: {'content': [{'type': 'text', 'text': json_string}], 'isError': False}
                        where 'json_string' contains the generated LLMs.txt content
                        (and optionally LLMs-full.txt content) as a JSON string.
            On failure: {'content': [{'type': 'text', 'text': error_message}], 'isError': True}
    """
    if not url:
        return _format_mcp_response("Error: 'url' parameter is required.", is_error=True)

    
    
    
    
    
    