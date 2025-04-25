from dotenv import load_dotenv, find_dotenv
import os 

_ = load_dotenv(find_dotenv())

api_key = os.getenv("SERP_API_KEY")


