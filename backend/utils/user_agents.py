from user_agents import parse

def parse_user_agent(user_agent: str):
    """
    Парсит User-Agent и возвращает информацию о браузере, OS и устройстве.
    """
    if not user_agent:
        return {"browser": "Unknown", "os": "Unknown", "device": "Unknown"}

    ua = parse(user_agent)
    return {
        "browser": f"{ua.browser.family} {ua.browser.version_string}",
        "os": f"{ua.os.family} {ua.os.version_string}",
        "device": ua.device.family,
        "is_mobile": ua.is_mobile,
        "is_tablet": ua.is_tablet,
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot,
    }