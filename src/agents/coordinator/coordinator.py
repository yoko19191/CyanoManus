# from openai import AsyncOpenAI
# from agents import OpenAIChatCompletionsModel, set_default_openai_client

# from agents import Agent, Runner


# # from dotenv import find_dotenv, load_dotenv
# # import os

# # _ = load_dotenv(find_dotenv())


# # coordinator_agent_client = AsyncOpenAI(
# #     api_key=os.getenv("BASIC_LLM_API_KEY"),
# #     base_url=os.getenv("BASIC_LLM_BASE_URL")
# # )

# # set_default_openai_client(coordinator_agent_client)

# # coordinator_agent_model = OpenAIChatCompletionsModel(
# #     model=os.getenv("BASIC_LLM_MODEL"),
# #     openai_client=coordinator_agent_client
# # )


# coordinator_agent = Agent(
#     name="coordinator_agent",
#     instructions="you are a helpful assistant and always reply user in poetry way",
#     model=OpenAIChatCompletionsModel(
#         model="gpt-4o",
#         openai_client=AsyncOpenAI(
#             api_key="sk-5CRwq3LizQGtJUaLyCsAc1qdtW99Hmj5R1rZ4sUF2T4FbwXI",
#             base_url="https://www.DMXapi.com/v1"
#         )
#     )
# )



# async def main():
#     result = await Runner.run(coordinator_agent, input="告诉我天空为什么是蓝色的？")
#     print(result)

# import asyncio

# asyncio.run(main())



import asyncio
from httpx import Client
from openai import AsyncOpenAI
from agents import (
    Agent, 
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
    set_trace_processors
)

from dotenv import find_dotenv, load_dotenv
import os 
_ = load_dotenv(find_dotenv())


from langsmith.wrappers import OpenAIAgentsTracingProcessor
set_trace_processors([OpenAIAgentsTracingProcessor()])


COORDINATOR_LLM_API_KEY = os.getenv("BASIC_LLM_API_KEY")
COORDINATOR_LLM_BASE_URL = os.getenv("BASIC_LLM_BASE_URL")
COORDINATOR_LLM_MODEL = os.getenv("BASIC_LLM_MODEL")

if not COORDINATOR_LLM_BASE_URL or not COORDINATOR_LLM_API_KEY or not COORDINATOR_LLM_MODEL:
    raise ValueError(
        "Please set Coordinator backing LLM properly"
    )


coordinator_client = AsyncOpenAI(
    api_key=COORDINATOR_LLM_API_KEY,
    base_url=COORDINATOR_LLM_BASE_URL
)

set_default_openai_client(client=coordinator_client, use_for_tracing=True)
set_default_openai_api("chat_completions")
#set_tracing_disabled(disabled=True)




async def main():
    coordinator_agent = Agent(
        name="coordinator_agent",
        instructions="you are a helpful assistant and always reply user in poetry way",
        model=COORDINATOR_LLM_MODEL
    )
    
    result = await Runner.run(coordinator_agent, input="天空为什么是蓝色的？")
    print(result)
    
    

asyncio.run(main())