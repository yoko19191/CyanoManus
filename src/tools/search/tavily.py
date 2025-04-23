""" 
CyanoManus Web Search Tools

A module providing web search, weather query tools.

TOOLS_AVAILABLE:
1. prompt_with_tavily_tools_instructions: Add Tavily tools usage instructions to prompt
2. tavily_search: Real-time web search tool using Tavily API
3. tavily_extract: Web content extraction tool for specific URLs
4. prompt_with_get_weather_instructions: Add weather query tool instructions to prompt
5. get_weather: Weather information retrieval tool using OpenWeather API
"""

from agents import function_tool

from tavily import AsyncTavilyClient

import httpx
from httpx import HTTPStatusError

import requests

from typing import Literal, Optional, List, Union, Sequence, Dict

from dotenv import find_dotenv, load_dotenv
import os

############# INITIALIZE #############

_ = load_dotenv(find_dotenv())

tavily_api_key = os.getenv("TAVILY_API_KEY")

async_tavily_client = AsyncTavilyClient(
    api_key=tavily_api_key
    #proxies    
    # env TAVILY_HTTP_PROXY
    # env TAVILY_HTTPS_PROXY
)

############# End of INITIALIZE #############


def get_all_tavily_tools():
    return [tavily_search, tavily_extract]

############# Tavily RECOMMAND INSTRUCTION SUFIX PROMPT #############
TAVILY_TOOLS_PROMPT = """ 
你可以使用如下两个强大的工具获得网络信息：
`tavily_search` 使用此工具进行实时网络搜索，获取相关信息的概览。
`tavily_extract` 使用此工具从特定URL提取完整内容，进行深入分析。
最佳实践：搭配使用两个工具。比如
1. 信息收集流程：
   - 先使用 tavily_search 获取相关信息概览
   - 从搜索结果中识别最相关的URL
   - 使用 tavily_extract 获取这些URL的完整内容
   - 基于提取的内容提供深入分析
2. 适用场景：
   - 研究特定主题
   - 获取最新新闻和发展
   - 事实核查和验证
   - 多角度分析复杂问题
注意：
1. 请确保搜索查询简洁明确，并选择适当的参数以获得最相关的结果。
2. 除非用户有任何明确要求，否则使用用户提问的语言进行回答。
"""

def prompt_with_tavily_tools_instructions(instruction_prompt: str) -> str:
    """Add recommand instructions to agent for better use tavily tools
    """
    return f"{instruction_prompt}\n {TAVILY_TOOLS_PROMPT}"



############# End of Tavily RECOMMAND INSTRUCTION SUFIX PROMPT #############


############# TAVILY SEARCH #############

def format_tavily_search_result(search_result: dict) -> str:
    """Format Tavily search results into a clear, structured text format optimized for LLM consumption.
    
    Args:
        search_result (dict): Raw Tavily search result dictionary
        
    Returns:
        str: Formatted search results as a structured string
    """
    formatted_parts = []
    
    # Add query information
    #formatted_parts.append(f"Search Query: {search_result.get('query', 'N/A')}")
    
    #formatted_parts.append(f"Response Time: {search_result.get('response_time', 'N/A')} seconds")
    
    # Add main search results
    formatted_parts.append("\nSearch Results:")
    for idx, result in enumerate(search_result.get('results', []), 1):
        formatted_parts.extend([
            f"Title: \n{idx}. {result.get('title', 'No Title')}",
            f"URL: {result.get('url', 'No URL')}",
            #f"Relevance Score: {result.get('score', 'N/A')}",
            #f"Published Date: {result.get('published_date', 'N/A')}" if 'published_date' in result else "",
            f"Content: {result.get('content', 'No content available')}\n"
        ])
    
    # Add AI-generated answer if available
    if 'answer' in search_result and search_result['answer']:
        formatted_parts.extend([
            "\nAI-Generated Answer:",
            search_result['answer']
        ])
    
    # Add images if available
    if 'images' in search_result and search_result['images']:
        formatted_parts.append("\nRelated Images:")
        for img in search_result['images']:
            if isinstance(img, dict):  # Image with description
                if img.get('description'):  # 只有当描述不为空时才添加
                    formatted_parts.extend([
                        f"Description: {img.get('description')}"
                    ])
            elif img:  # 只有当URL不为空时才添加
                formatted_parts.append(f"\nImage URL: {img}")
    
    return "\n".join(part for part in formatted_parts if part)

@function_tool
async def tavily_search(
    query: str, 
    time_range: Literal["day", "d", "week", "w", "month","m", "year", "y"]=None,
    search_depth: Literal["basic", "advanced"] = "basic",
    topic: Literal["general", "news", "finance"] = "general",
    days: int = 7,
    max_result: int = 5, 
    chunks_per_source: Literal[1, 2, 3] = 1,
    include_images: bool = False,
    include_image_descriptions: bool = False, 
    include_answer: Union[bool, Literal["basic", "advanced"]] = False,
    include_raw_content: bool = False,
    include_domains: Sequence[str] = None,
    exclude_domains: Sequence[str] = None,
    timeout: int = 60
) -> str:
    """A powerful web search tool that provides comprehensive, real-time results using Tavily's AI search engine.
    
    Args:
        query (str): Search query string
        time_range (Literal["day", "d", "week", "w", "month","m", "year", "y"], optional): Time range for search results
        search_depth (Literal["basic", "advanced"], optional): Depth of search - 'basic' or 'advanced'. Defaults to "basic"
        topic (Literal["general", "news", "finance"], optional): Category of search determining which agents to use. Defaults to "general"
        days (int, optional): Number of days back to include in results (only for 'news' topic). Defaults to 7
        max_result (int, optional): Maximum number of search results to return. Defaults to 5
        chunks_per_source (Literal[1, 2, 3], optional): Number of content chunks per source. Defaults to 1
        include_images (bool, optional): Include query-related images in response. Defaults to False
        include_image_descriptions (bool, optional): Include image descriptions in response. Defaults to False
        include_answer (Union[bool, Literal["basic", "advanced"]], optional): Include AI-generated answer. Defaults to False
        include_raw_content (bool, optional): Include cleaned HTML content of results. Defaults to False
        include_domains (Sequence[str], optional): List of domains to specifically include. Defaults to None
        exclude_domains (Sequence[str], optional): List of domains to specifically exclude. Defaults to None
        timeout (int, optional): Request timeout in seconds. Defaults to 60

    Returns:
        str: Formatted search results as string, or error message if the search fails
    """
    # 处理可变默认参数（避免列表作为默认参数的陷阱）
    include_domains = include_domains or []
    exclude_domains = exclude_domains or []

    # 自动捕获所有参数（排除特殊参数如timeout）
    args = {
        k: v for k, v in locals().items() 
        if k not in ("timeout", "self", "__class__")  # 过滤不需要的参数
    }

    try:
        # 添加timeout到客户端调用
        search_result = await async_tavily_client.search(**args, timeout=timeout)
        # Convert search result to dictionary if it's not already
        result_dict = search_result if isinstance(search_result, dict) else eval(str(search_result))
        return format_tavily_search_result(result_dict)
        #return result_dict
    except HTTPStatusError as e:
        error_messages = {
            401: "Invalid API key",
            429: "Usage limit exceeded",
        }
        default_msg = f"API request failed with status {e.response.status_code}"
        return f"Error: {error_messages.get(e.response.status_code, default_msg)}"

    except httpx.RequestError as e:
        return f"Error: Network error - {str(e)}"

    except Exception as e:
        return f"Error: Unexpected error - {type(e).__name__}: {str(e)}"

############# End of TAVILY SEARCH #############


############# TAVILY EXTRACT #############

def format_tavily_extract_result(extract_result: dict) -> str:
    """Format Tavily extract results into a clear, structured text format optimized for LLM consumption.
    
    Args:
        extract_result (dict): Raw Tavily extract result dictionary
        
    Returns:
        str: Formatted extraction results as a structured string
    """
    formatted_parts = []
    
    # Add response time
    #formatted_parts.append(f"Response Time: {extract_result.get('response_time', 'N/A')} seconds\n")
    
    # Add successful extractions
    if 'results' in extract_result and extract_result['results']:
        formatted_parts.append("Successfully Extracted Content:")
        for idx, result in enumerate(extract_result['results'], 1):
            formatted_parts.extend([
                f"\n{idx}. URL: {result.get('url', 'No URL')}",
                f"Content:",
                f"{result.get('raw_content', 'No content available')}"
            ])
            
            # Add images if available
            if 'images' in result and result['images']:
                formatted_parts.append("\nExtracted Images:")
                for img_url in result['images']:
                    formatted_parts.append(f"- {img_url}")
            formatted_parts.append("")  # Add blank line between results
    
    # Add failed extractions
    if 'failed_results' in extract_result and extract_result['failed_results']:
        formatted_parts.append("\nFailed Extractions:")
        for idx, failed in enumerate(extract_result['failed_results'], 1):
            formatted_parts.extend([
                f"\n{idx}. URL: {failed.get('url', 'No URL')}",
                f"Error: {failed.get('error', 'Unknown error')}"
            ])
    
    return "\n".join(formatted_parts)

@function_tool
async def tavily_extract(
    urls: List[str],
    extract_depth: Literal["basic", "advanced"] = "basic",
    include_images: bool = False,
    timeout: int = 60
) -> str:
    """A powerful web content extraction tool that retrieves and processes raw content from specified URLs.
    
    Args:
        urls (List[str]): List of URLs to extract content from
        extract_depth (Literal["basic", "advanced"], optional): Depth of extraction - 'basic' or 'advanced'. 
            Use 'advanced' for LinkedIn URLs or when explicitly specified. Defaults to "basic"
        include_images (bool, optional): Include extracted images in response. Defaults to False
        timeout (int, optional): Request timeout in seconds. Defaults to 60

    Returns:
        str: Formatted extraction results as string, or error message if the extraction fails
    """
    try:
        extract_result = await async_tavily_client.extract(
            urls=urls,
            extract_depth=extract_depth,
            include_images=include_images,
            timeout=timeout
        )
        # Convert extract result to dictionary if it's not already
        result_dict = extract_result if isinstance(extract_result, dict) else eval(str(extract_result))
        return format_tavily_extract_result(result_dict)
        #return result_dict
    except HTTPStatusError as e:
        error_messages = {
            401: "Invalid API key",
            429: "Usage limit exceeded",
        }
        default_msg = f"API request failed with status {e.response.status_code}"
        return f"Error: {error_messages.get(e.response.status_code, default_msg)}"

    except httpx.RequestError as e:
        return f"Error: Network error - {str(e)}"

    except Exception as e:
        return f"Error: Unexpected error - {type(e).__name__}: {str(e)}"
    
############# END of TAVILY EXTRACT #############

