from functools import lru_cache

from langchain.agents import create_agent

from app.llm_config import build_chat_model


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    weather_map = {
        "beijing": "Beijing is sunny, 24C.",
        "北京": "北京晴，24C。",
        "shanghai": "Shanghai is cloudy, 22C.",
        "上海": "上海多云，22C。",
        "shenzhen": "Shenzhen is rainy, 27C.",
        "深圳": "深圳有雨，27C。",
    }
    return weather_map.get(city.strip().lower(), f"{city} weather is unavailable, but it is likely mild.")


def sanitize_text(value) -> str:
    text = str(value)
    return text.encode("utf-8", errors="replace").decode("utf-8")


@lru_cache(maxsize=1)
def get_agent():
    return create_agent(
        model=build_chat_model(),
        tools=[get_weather],
        system_prompt="You are a helpful assistant. Be concise and use tools when needed.",
    )


def chat_once(user_input: str) -> str:
    result = get_agent().invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_input,
                }
            ]
        }
    )
    return sanitize_text(result["messages"][-1].content)
