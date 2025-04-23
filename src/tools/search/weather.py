""" 
CyanoManus Weather Tools

A module providing weather tools.

TOOLS_AVAILABLE:
1. prompt_with_get_weather_instructions: Add weather query tool instructions to prompt
2. get_weather: Weather information retrieval tool using OpenWeather API
"""

from agents import function_tool

import httpx
from httpx import HTTPStatusError

import requests

from typing import Dict

from dotenv import find_dotenv, load_dotenv
import os

############# INITIALIZE #############

_ = load_dotenv(find_dotenv())

openweather_api_key = os.getenv("OPENWEATHER_API_KEY")


############# End of INITIALIZE #############


############# GET WEATHER #############

GET_WEATHER_TOOLS_PROMPT = """ 
你可以使用如下工具获得天气信息：
`get_weather` 输入英文城市名称，获得该城市的天气信息。
注意：
1. 请确保搜索查询简洁明确，并选择适当的参数以获得最相关的结果。
2. 根据用户的提问的语言，推测用户的使用的温度单位。比如中文用户，使用摄氏度。
3. 当用户提问只包含粗略的天气信息请求时，只返回温度、天气等基础信息。
4. 在分析到天气状况非常极端时，比如极端高温、极端低温、极端天气等，提醒用户注意。
5. 除非用户有任何明确要求，否则使用用户提问的语言进行回答。
""" 


def prompt_with_get_weather_instructions(instruction_prompt: str) -> str:
    """Add recommand instructions to agent for better use tavily tools
    """
    return f"{instruction_prompt}\n {GET_WEATHER_TOOLS_PROMPT}"

def format_weather_data(weather_data: Dict) -> str:
    """    
    Format raw openweather api return into txt format for better LLM consumption.
    
    Args:
        weather_data (dict): raw json dict from openweather api return or error string
    
    Returns:
        str: formatted weather information string
    """
    # handle weather_data is string (error report)
    if isinstance(weather_data, str):
        return f"Error: {weather_data}"

    # handle invalid weather data
    if not weather_data or 'cod' not in weather_data or weather_data['cod'] != 200:
        return "Unable to retrieve weather data"
    
    try:
        # extract weather information
        city = weather_data['name']
        country = weather_data['sys']['country']
        weather_desc = weather_data['weather'][0]['description'].capitalize()
        
        # extract temperature information
        temp = weather_data['main']['temp']
        feels_like = weather_data['main']['feels_like']
        temp_min = weather_data['main']['temp_min']
        temp_max = weather_data['main']['temp_max']
        humidity = weather_data['main']['humidity']
        
        # extract wind information
        wind_speed = weather_data['wind']['speed']
        wind_deg = weather_data['wind'].get('deg', 'N/A')
        
        # extract additional information
        pressure = weather_data['main']['pressure']
        visibility = weather_data.get('visibility', 'N/A')
        if visibility != 'N/A':
            visibility = f"{visibility/1000} km"  # 转换为千米
        
        # formatting
        formatted_output = (
            f"📍 Location: {city}, {country}\n"
            f"🌤️ Weather: {weather_desc}\n"
            f"🌡️ Temperature: {temp}°C (feels like {feels_like}°C)\n"
            f"📈 Temperature Range: {temp_min}°C ~ {temp_max}°C\n"
            f"💧 Humidity: {humidity}%\n"
            f"🌬️ Wind Speed: {wind_speed} m/s, Direction: {wind_deg}°\n"
            f"📊 Pressure: {pressure} hPa\n"
            f"👀 Visibility: {visibility}"
        )
        
        return formatted_output
    
    except KeyError as e:
        return f"Data parsing error: Missing key field {e}"

@function_tool
async def get_weather(loc: str, unit="metric", lang="en") -> str: 
    """Get Weather information from given location via OpenWeather API
    Args:
        loc: str, the location of the weather
        unit: str, the unit of the weather, default is metric
        lang: str, the language of the weather, default is en
    Returns:
        str, the weather of the location
    """
    api_key = openweather_api_key
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    try:
        params = {
            "q": loc,
            "appid": api_key,
            "units": unit,
            "lang": lang
        }
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        return format_weather_data(weather_data)
    
    except requests.exceptions.RequestException as e:
        return format_weather_data(f"Get weather data of {loc} failed: {e}")

############# End of GET WEATHER #############