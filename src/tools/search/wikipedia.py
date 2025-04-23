"""
CyanoManus Wikipedia Search Tools

此模块提供了用于与维基百科 API 交互的函数，
作为 CyanoManus 项目中 Function Calling 的一部分。
它允许搜索页面、获取摘要、内容和元数据。
"""

import wikipedia
from wikipedia.exceptions import PageError, DisambiguationError, WikipediaException
import json # 用于元数据函数返回 JSON 字符串

from agents import function_tool


def get_all_wikipedia_tools(): 
    return [search_wiki_pages, get_wiki_page_summary, get_wiki_page_content, get_wiki_page_metadata, get_random_wiki_page_title]


# 新增：维基百科工具使用说明
WIKIPEDIA_TOOLS_PROMPT = """
你可以使用以下维基百科工具来获取信息：
`search_wiki_pages`: 根据关键词搜索维基百科页面标题。
`get_wiki_page_summary`: 获取指定维基百科页面的摘要。
`get_wiki_page_content`: 获取指定维基百科页面的完整内容。
`get_wiki_page_metadata`: 获取指定维基百科页面的元数据（如URL、分类、坐标等），以JSON格式返回。
`get_random_wiki_page_title`: 获取一个或多个随机维基百科文章的标题。

最佳实践：
1.  **信息查找流程**:
    *   首先使用 `search_wiki_pages` 查找相关的页面标题。
    *   根据搜索结果，选择最相关的标题。
    *   使用 `get_wiki_page_summary` 获取页面的简要概述。
    *   如果需要更详细的信息，使用 `get_wiki_page_content` 获取完整内容。
    *   如果需要特定信息（如页面ID、URL、分类等），使用 `get_wiki_page_metadata`。
2.  **语言参数**: 所有函数都接受 `lang` 参数来指定维基百科的语言版本（例如 'en' 代表英语，'zh' 代表中文）。请根据用户提问的语言或上下文选择合适的语言。
3.  **错误处理**: 函数在遇到问题时（如页面未找到、歧义页面）会返回包含 "Error:" 的字符串。请注意检查并根据错误信息调整你的请求。
4.  **随机页面**: 使用 `get_random_wiki_page_title` 来探索随机主题或获取示例页面。
"""

# 新增：用于添加说明的函数
def prompt_with_wikipedia_tools_instructions(instruction_prompt: str) -> str:
    """将维基百科工具的使用说明添加到提示中"""
    return f"{instruction_prompt}\n{WIKIPEDIA_TOOLS_PROMPT}"

@function_tool
def search_wiki_pages(query: str, results: int = 5, lang: str = "en") -> list[str] | str:
    """
    根据查询词搜索维基百科页面标题。

    设计用于 LLM Function Calling。成功时返回标题列表，失败时返回错误信息字符串。

    Args:
        query (str): 搜索的关键词。
        results (int): 返回的最大结果数量。默认为 5。
        lang (str): 维基百科语言代码 (例如, "en" 代表英语, "zh" 代表中文)。默认为 "en"。

    Returns:
        list[str] | str: 如果成功，返回匹配的维基百科页面标题列表。
                         如果发生错误（例如 API 问题），返回一个描述错误的字符串。
    """
    try:
        wikipedia.set_lang(lang)
        search_results = wikipedia.search(query, results=results)
        return search_results
    except Exception as e:
        # 返回错误信息字符串而不是抛出异常
        return f"Wikipedia API Error: Failed to search for '{query}' in language '{lang}'. Details: {e}"

@function_tool
def get_wiki_page_summary(title: str, sentences: int = 0, auto_suggest: bool = True, redirect: bool = True, lang: str = "en") -> str:
    """
    获取指定维基百科页面的摘要。

    设计用于 LLM Function Calling。成功时返回页面摘要，失败时返回错误信息字符串。

    Args:
        title (str): 维基百科页面的确切标题或搜索词。
        sentences (int): 返回摘要的句子数量。0 表示返回第一段。默认为 0。
        auto_suggest (bool): 如果找不到精确匹配，是否自动建议页面。默认为 True。
        redirect (bool): 是否自动处理重定向。默认为 True。
        lang (str): 维基百科语言代码 (例如, "en" 代表英语, "zh" 代表中文)。默认为 "en"。

    Returns:
        str: 如果成功，返回页面的纯文本摘要。
             如果页面未找到 (PageError)，返回 "Error: Page not found for title '{title}'."。
             如果标题导致消歧义 (DisambiguationError)，返回 "Error: Disambiguation - '{title}' may refer to: [options list]."。
             如果发生其他 API 错误，返回 "Error: Could not retrieve summary for '{title}'. Details: [error details]."。
    """
    try:
        wikipedia.set_lang(lang)
        # 尝试直接获取摘要，如果失败则捕获异常
        summary_text = wikipedia.summary(title, sentences=sentences, auto_suggest=auto_suggest, redirect=redirect)
        return summary_text
    except PageError:
        return f"Error: Page not found for title '{title}' in language '{lang}'."
    except DisambiguationError as e:
        options = ", ".join(e.options[:5]) # 最多显示5个选项
        return f"Error: Disambiguation - '{title}' in language '{lang}' may refer to: {options}..."
    except Exception as e:
        return f"Error: Could not retrieve summary for '{title}' in language '{lang}'. Details: {e}"


@function_tool
def get_wiki_page_content(title: str, auto_suggest: bool = True, redirect: bool = True, lang: str = "en") -> str:
    """
    获取指定维基百科页面的完整纯文本内容。

    设计用于 LLM Function Calling。成功时返回页面内容，失败时返回错误信息字符串。

    Args:
        title (str): 维基百科页面的确切标题或搜索词。
        auto_suggest (bool): 如果找不到精确匹配，是否自动建议页面。默认为 True。
        redirect (bool): 是否自动处理重定向。默认为 True。
        lang (str): 维基百科语言代码 (例如, "en" 代表英语, "zh" 代表中文)。默认为 "en"。

    Returns:
        str: 如果成功，返回页面的完整纯文本内容。
             如果页面未找到 (PageError)，返回 "Error: Page not found for title '{title}'."。
             如果标题导致消歧义 (DisambiguationError)，返回 "Error: Disambiguation - '{title}' may refer to: [options list]."。
             如果发生其他 API 错误，返回 "Error: Could not retrieve content for '{title}'. Details: [error details]."。
    """
    try:
        wikipedia.set_lang(lang)
        page_obj = wikipedia.page(title, auto_suggest=auto_suggest, redirect=redirect)
        return page_obj.content
    except PageError:
        return f"Error: Page not found for title '{title}' in language '{lang}'."
    except DisambiguationError as e:
        options = ", ".join(e.options[:5])
        return f"Error: Disambiguation - '{title}' in language '{lang}' may refer to: {options}..."
    except Exception as e:
        return f"Error: Could not retrieve content for '{title}' in language '{lang}'. Details: {e}"

@function_tool
def get_wiki_page_metadata(title: str, metadata_keys: list[str] | None = None, auto_suggest: bool = True, redirect: bool = True, lang: str = "en") -> str:
    """
    获取指定维基百科页面的元数据，并以 JSON 字符串形式返回。

    设计用于 LLM Function Calling。成功时返回包含元数据的 JSON 字符串，失败时返回错误信息字符串。

    Args:
        title (str): 维基百科页面的确切标题或搜索词。
        metadata_keys (list[str] | None): 需要获取的元数据键列表。
            可能的键包括: 'title', 'pageid', 'url', 'content', 'summary',
            'images', 'references', 'links', 'sections', 'parent_id',
            'revision_id', 'categories', 'coordinates', 'html'.
            如果为 None，则尝试获取常用元数据 ('title', 'pageid', 'url', 'categories', 'summary')。默认为 None。
        auto_suggest (bool): 如果找不到精确匹配，是否自动建议页面。默认为 True。
        redirect (bool): 是否自动处理重定向。默认为 True。
        lang (str): 维基百科语言代码 (例如, "en" 代表英语, "zh" 代表中文)。默认为 "en"。

    Returns:
        str: 如果成功，返回一个包含所请求元数据的 JSON 格式字符串。
             如果页面未找到 (PageError)，返回 "Error: Page not found for title '{title}'."。
             如果标题导致消歧义 (DisambiguationError)，返回 "Error: Disambiguation - '{title}' may refer to: [options list]."。
             如果请求了无效的元数据键 (AttributeError)，返回 "Error: Invalid metadata key requested: [key name]."。
             如果发生其他 API 错误，返回 "Error: Could not retrieve metadata for '{title}'. Details: [error details]."。
    """
    try:
        wikipedia.set_lang(lang)
        page_obj = wikipedia.page(title, auto_suggest=auto_suggest, redirect=redirect)
        metadata = {}

        default_keys = ['title', 'pageid', 'url', 'categories', 'summary']
        keys_to_fetch = metadata_keys if metadata_keys is not None else default_keys

        for key in keys_to_fetch:
            try:
                if hasattr(page_obj, key):
                    # 特殊处理可能返回非 JSON 兼容类型的属性 (虽然此列表中的大部分是安全的)
                    value = getattr(page_obj, key)
                    # 确保值是 JSON 可序列化的 (简单类型通常没问题)
                    metadata[key] = value
                elif key == 'html': # 特殊处理 html() 方法
                     metadata[key] = page_obj.html() # HTML 字符串是安全的
                else:
                    # 记录无法直接获取的键，但不视为错误
                    metadata[key] = f"Warning: Key '{key}' not directly available or failed to retrieve."
            except Exception as e:
                # 捕获获取单个属性时可能发生的错误
                metadata[key] = f"Warning: Could not retrieve metadata key '{key}'. Details: {e}"

        # 将字典转换为 JSON 字符串
        return json.dumps(metadata, ensure_ascii=False, indent=2) # indent 用于可读性，LLM 可能不需要

    except PageError:
        return f"Error: Page not found for title '{title}' in language '{lang}'."
    except DisambiguationError as e:
        options = ", ".join(e.options[:5])
        return f"Error: Disambiguation - '{title}' in language '{lang}' may refer to: {options}..."
    except AttributeError as e: # 虽然内部尝试捕获，但 page() 本身可能失败
        return f"Error: Invalid metadata key requested or attribute access issue for '{title}'. Details: {e}"
    except Exception as e:
        return f"Error: Could not retrieve metadata for '{title}' in language '{lang}'. Details: {e}"

@function_tool
def get_random_wiki_page_title(pages: int = 1, lang: str = "en") -> str | list[str]:
    """
    获取一个或多个随机维基百科文章的标题。

    设计用于 LLM Function Calling。成功时返回标题或标题列表，失败时返回错误信息字符串。

    Args:
        pages (int): 要获取的随机页面数量。默认为 1。
        lang (str): 维基百科语言代码 (例如, "en" 代表英语, "zh" 代表中文)。默认为 "en"。

    Returns:
        str | list[str]: 如果 pages=1 且成功，返回单个标题字符串。
                         如果 pages > 1 且成功，返回标题字符串列表。
                         如果发生错误，返回一个描述错误的字符串。
    """
    try:
        wikipedia.set_lang(lang)
        random_titles = wikipedia.random(pages=pages)
        return random_titles
    except Exception as e:
        return f"Error: Could not retrieve random Wikipedia page(s) in language '{lang}'. Details: {e}"

# == 示例用法 ==
# if __name__ == '__main__':
#     # 搜索页面 (中文)
#     query = "人工智能"
#     print(f"\nSearching for '{query}' in Chinese...")
#     search_results = search_wiki_pages(query, results=3, lang="zh")
#     print(f"Search Results: {search_results}") # 可能是列表或错误字符串

#     # 获取摘要 (英文) - 假设搜索结果是列表且第一个是 'Artificial intelligence'
#     page_title_en = "Artificial intelligence"
#     print(f"\nGetting summary for '{page_title_en}' in English...")
#     summary = get_wiki_page_summary(page_title_en, sentences=2, lang="en")
#     print(f"Summary:\n{summary}") # 可能是摘要或错误字符串

#     # 获取内容 (中文) - 假设搜索结果是列表且第一个是 '人工智能'
#     if isinstance(search_results, list) and search_results:
#         page_title_zh = search_results[0]
#         print(f"\nGetting content for '{page_title_zh}' in Chinese...")
#         content = get_wiki_page_content(page_title_zh, lang="zh")
#         if not content.startswith("Error:"):
#             print(f"Content (first 200 chars):\n{content[:200]}...")
#         else:
#             print(content) # 打印错误信息
#     else:
#         print("\nSkipping content retrieval due to search error or no results.")


#     # 获取元数据 (中文) - '北京'
#     print(f"\nGetting metadata for '北京' in Chinese...")
#     metadata_json = get_wiki_page_metadata("北京", metadata_keys=['pageid', 'url', 'categories', 'coordinates', 'invalid_key'], lang="zh")
#     print(f"Metadata (JSON):\n{metadata_json}") # 可能是 JSON 字符串或错误字符串

#     # 处理歧义页面示例 (英文)
#     print("\nTesting Disambiguation (English):")
#     summary_dis = get_wiki_page_summary("Apple", auto_suggest=False, lang="en")
#     print(f"Result for 'Apple': {summary_dis}") # 应该返回 Disambiguation 错误字符串

#     # 处理页面不存在示例 (英文)
#     print("\nTesting Page Not Found (English):")
#     summary_404 = get_wiki_page_summary("A non existent wikipedia page title 12345xyz", auto_suggest=False, lang="en")
#     print(f"Result for non-existent page: {summary_404}") # 应该返回 Page not found 错误字符串

#     # 获取随机页面 (英文)
#     print("\nGetting random page title (English):")
#     random_title = get_random_wiki_page_title(lang="en")
#     print(f"Random title: {random_title}") # 可能是标题或错误字符串