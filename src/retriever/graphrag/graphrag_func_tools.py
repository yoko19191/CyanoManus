""" 
Using GraphRAG resposne from given query.

1. graphrag init --root ./ragtest
2. mkdir ./ragtest/input
3. graphrag index --root ./ragtest
4. setup setttings.yaml and .env
5. graphrag query --root ./ragtest --method local --query "your-query"
6. graphrag query --root ./ragtest --method global --query "your-query"
"""

from pathlib import Path 

import pandas as pd

import graphrag.api as api 
from graphrag.config.load_config import load_config
from graphrag.index.typing.pipeline_run_result import PipelineRunResult

from typing import Literal

from dotenv import load_dotenv, find_dotenv
import os
_ = load_dotenv(find_dotenv())  # read local .env file


from agents import function_tool


# directories where graphrag project has already init and indexing
PROJECT_DIR = os.getenv("GRAPHRAG_PROJECT")


# 
graphrag_config = load_config(Path(PROJECT_DIR))


# BOTH LOCAL SEARCH AND GLOBAL SEARCH NEED THIS
entities = pd.read_parquet(f"{PROJECT_DIR}/output/entities.parquet")
communities = pd.read_parquet(f"{PROJECT_DIR}/output/communities.parquet")
community_reports = pd.read_parquet(f"{PROJECT_DIR}/output/community_reports.parquet")

# LOCAL SEARCH NEED THIS 
text_units = pd.read_parquet(f"{PROJECT_DIR}/output/text_units.parquet")
relationships = pd.read_parquet(f"{PROJECT_DIR}/output/relationships.parquet")



@function_tool
async def check_graphrag_project_status() -> str:
    """
    Check if the openai agents sdk documentation grphrag project is ready for query.
    Returns:
        str: the status detail of given graphrag project
    """
    index_result: list [PipelineRunResult] = await api.build_index(config=graphrag_config)
    lines = []
    error_count = 0 
    for workflow_result in index_result:
        if workflow_result.errors:
            error_count += 1
            lines.append(f"Workflow {workflow_result.workflow}\tStatus: error\n {workflow_result.errors}")
        else:
            lines.append(f"Workflow {workflow_result.workflow}\tStatus: success")
        lines.append("\n")    
    return_str = "".join(lines)
    if error_count > 0:
        return_str += f"\n⚠️ Found {error_count} errors. Please check the status of graphrag project"
    else: 
        return_str += "\n✅ Graphrag project {PROJECT_DIR} is ready for query."        

    return return_str


@function_tool
async def graphrag_query(query: str, method: Literal["local", "global"]="local") -> str:
    """
    
    这是一个使用 GraphRAG 查询 OpenAI Agents SDK 文档的函数。
    
    Args:
        query (str): 用户有关 OpenAI Agents SDK 文档的查询。
        method (Literal[&quot;local&quot;, &quot;global&quot;], optional): 进行 GraphRAG 查询的方式 local 使用实体进行查询，速度快，适合绝大多数情况的查询。global 联合使用社区进行查询，适用于对全局问题的查询。. Defaults to "local".

    Returns:
        str: 查询的结果或错误。
    """
    
    try: 
        match method:
            case "local":
                try: 
                    response, context = await api.local_search(
                        config=graphrag_config,
                        entities=entities,
                        communities=communities,
                        community_reports=community_reports,
                        community_level=2,
                        covariates=None,
                        text_units=text_units,
                        relationships=relationships,
                        response_type="Multiple Paragraphs",
                        query=query
                    )
                    return f"Local Search Response: {response}\nContext: {context}"
                except Exception as e:
                    return f"Local Search failed. Error: {e}"
                
            case "global":
                try:     
                    response, context = await api.global_search(
                        config=graphrag_config,
                        entities=entities,
                        communities=communities,
                        community_reports=community_reports,
                        community_level=2,
                        dynamic_community_selection=False,
                        response_type="Multiple Paragraphs",
                        query=query,
                    )
                    return f"Global Search Response: {response}\n"
                except Exception as e:
                    return f"Global Search failed. Error: {e}"
                
    except Exception as e:
        return f"GraphRAG query {str} failed. Error: {e}"
    
    # can not use finally here, because it will be a coroutine
    
    