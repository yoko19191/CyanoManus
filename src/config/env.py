from dotenv import find_dotenv, load_dotenv
import os

# load enviroment variables from .env file
_ = load_dotenv(find_dotenv())


BASIC_LLM_API_KEY = os.getenv("BASIC_LLM_API_KEY")
BASIC_LLM_BASE_URL = os.getenv("BASIC_LLM_BASE_URL")
BASIC_LLM_MODEL = os.getenv("BASIC_LLM_MODEL")

REASONING_LLM_API_KEY = os.getenv("REASONING_LLM_API_KEY")
REASONING_LLM_BASE_URL = os.getenv("REASONING_LLM_BASE_URL")
REASONING_LLM_MODEL = os.getenv("REASONING_LLM_MODEL")

VLM_API_KEY = os.getenv("VLM_API_KEY")
VLM_BASE_URL = os.getenv("VLM_BASE_URL")
VLM_MODEL = os.getenv("VLM_MODEL")

CODING_LLM_API_KEY = os.getenv("CODING_LLM_API_KEY")
CODING_LLM_BASE_URL = os.getenv("CODING_LLM_BASE_URL")
CODING_LLM_MODEL = os.getenv("CODING_LLM_MODEL")

