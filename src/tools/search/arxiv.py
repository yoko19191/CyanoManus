import logging

import arxiv 
from arxiv import ArxivError, UnexpectedEmptyPageError, HTTPError


from dotenv import load_dotenv, find_dotenv
import os

from agents import function_tool


logging.basicConfig(level=logging.DEBUG)


_ = load_dotenv(find_dotenv())

working_dir = os.getenv("WORKING_DIR")

client = arxiv.Client()

ARXIV_TOOLS_PROMPT = """

"""


# For advanced query syntax documentation, see the arXiv API User Manual:
# https://arxiv.org/help/api/user-manual#query_details
ADVANCED_QUERY_SYNTAX_PROMPT = """

"""


def get_all_arxiv_tools():
    return 





def categories_map()：




async def arxiv_query() -> str:
    """在 arxiv 上搜索
    """
    return None 


async def arxiv_extract() -> str:
    """获取一个具体的的论文的详细信息
    """
    return None


async def arxiv_download() -> str:
    """下载一个具体的论文的 PDF 保存到 working_dir 目录下
    
    """
    return None