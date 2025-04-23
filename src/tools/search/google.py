"""
CyanoManus Google Search Tools

此模块提供了使用 googlesearch-python 库进行 Google 搜索的函数，
作为 CyanoManus 项目中 Function Calling 的一部分。
它允许执行基本的 Google 搜索并获取结果列表或详细信息。
"""
from googlesearch import search as google_search_api, SearchResult
from typing import List, Optional, Union

from agents import function_tool

# Google Search 工具使用说明
GOOGLE_SEARCH_TOOLS_PROMPT = """
你可以使用以下 Google 搜索工具来获取网络信息, 尤其是非中文内容。
`google_search`: 使用 Google 搜索引擎执行网络搜索。

使用方法：
1.  **基本搜索**: 提供搜索查询词 (`query`)，可以指定结果数量 (`num_results`)、语言 (`lang`) 和地区 (`region`)。默认返回 URL 列表。
2.  **高级搜索**: 设置 `advanced=True` 来获取每个结果的标题、URL 和描述。
3.  **语言和地区**: 使用 `lang` (如 'en', 'zh-CN') 和 `region` (如 'us', 'cn') 参数来定制搜索范围。
4.  **错误处理**: 如果搜索过程中出现问题，函数会返回包含 "Error:" 的字符串。

注意：此工具依赖于抓取 Google 搜索结果页，请避免过于频繁的请求，以免被暂时阻止。
"""

def prompt_with_google_search_instructions(instruction_prompt: str) -> str:
    """将 Google 搜索工具的使用说明添加到提示中"""
    return f"{instruction_prompt}\n{GOOGLE_SEARCH_TOOLS_PROMPT}"

def format_search_results(results: Union[List[str], List[SearchResult]], advanced: bool) -> str:
    """将搜索结果格式化为适合 LLM 的字符串。"""
    if not results:
        return "No search results found."

    formatted_parts = ["Search Results:"]
    if advanced:
        # 处理 SearchResult 对象列表
        for idx, result in enumerate(results, 1):
            if isinstance(result, SearchResult): # 确保是 SearchResult 对象
                 formatted_parts.append(f"\n{idx}. Title: {result.title}")
                 formatted_parts.append(f"   URL: {result.url}")
                 formatted_parts.append(f"   Description: {result.description}")
            else:
                 # 如果不是预期的类型，则记录下来
                 formatted_parts.append(f"\n{idx}. Unexpected result format: {result}")

    else:
        # 处理 URL 字符串列表
        for idx, url in enumerate(results, 1):
             if isinstance(url, str):
                 formatted_parts.append(f"{idx}. {url}")
             else:
                 formatted_parts.append(f"{idx}. Unexpected result format: {url}")


    return "\n".join(formatted_parts)

@function_tool
def google_search(
    query: str,
    num_results: int = 10,
    lang: str = "en",
    region: Optional[str] = None,
    advanced: bool = False,
    sleep_interval: int = 0,
    timeout: int = 5
) -> str:
    """
    使用 Google 搜索引擎执行网络搜索。

    设计用于 LLM Function Calling。成功时返回格式化的搜索结果字符串，失败时返回错误信息字符串。

    Args:
        query (str): 要搜索的关键词。
        num_results (int): 希望返回的结果数量。默认为 10。
        lang (str): 搜索结果的语言代码 (例如, "en", "zh-CN")。默认为 "en"。
        region (Optional[str]): 搜索结果的地区代码 (例如, "us", "cn")。默认为 None (全球)。
        advanced (bool): 是否返回高级结果 (包含标题、URL和描述)。默认为 False (只返回 URL)。
        sleep_interval (int): 当请求大量结果时，每次请求之间的休眠秒数，以避免被阻止。默认为 0。
        timeout (int): 单次 HTTP 请求的超时时间（秒）。默认为 5。

    Returns:
        str: 如果成功，返回格式化的搜索结果字符串 (URL 列表或包含标题/描述的列表)。
             如果发生错误 (例如网络问题、请求被阻止等)，返回一个描述错误的字符串，以 "Error:" 开头。
    """
    try:
        print(f"Performing Google search for: '{query}' (lang={lang}, region={region}, num={num_results}, advanced={advanced})")
        search_results_iterator = google_search_api(
            query=query,
            num_results=num_results,
            lang=lang,
            region=region,
            advanced=advanced,
            sleep_interval=sleep_interval,
            timeout=timeout
        )
        # 将迭代器转换为列表以处理结果
        results_list = list(search_results_iterator)

        return format_search_results(results_list, advanced)

    except Exception as e:
        # 捕获所有可能的异常，包括网络错误、解析错误等
        error_message = f"Error performing Google search for '{query}'. Details: {type(e).__name__}: {str(e)}"
        print(error_message)
        return error_message

# == 示例用法 ==
# if __name__ == '__main__':
#     # 基本搜索示例 (中文)
#     print("\n--- Basic Search (Chinese) ---")
#     basic_results_zh = google_search(query="大型语言模型", num_results=5, lang="zh-CN", region="cn")
#     print(basic_results_zh)

#     # 高级搜索示例 (英文)
#     print("\n--- Advanced Search (English) ---")
#     advanced_results_en = google_search(query="Large Language Models applications", num_results=3, lang="en", advanced=True)
#     print(advanced_results_en)

#     # 搜索可能失败的示例 (例如，网络问题或被阻止时)
#     # print("\n--- Potential Error Scenario ---")
#     # try:
#     #     # 模拟一个可能导致问题的场景，例如非常高的 num_results 或无效代理
#     #     error_result = google_search(query="test", num_results=1000, sleep_interval=0.1, timeout=1)
#     #     print(error_result)
#     # except Exception as e:
#     #      print(f"Caught exception outside function (should not happen ideally): {e}")

#     # 测试带说明的提示
#     print("\n--- Prompt with Instructions ---")
#     initial_prompt = "请帮我研究一下最新的 AI 技术。"
#     prompt_with_instructions = prompt_with_google_search_instructions(initial_prompt)
#     print(prompt_with_instructions)