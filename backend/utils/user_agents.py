from user_agents import parse
import re

def parse_user_agent(user_agent: str):
    """
    Улучшенный парсер User-Agent с дополнительной логикой для точного определения устройств.
    Возвращает детальную информацию о браузере, ОС и устройстве.
    """
    if not user_agent:
        return {
            "browser": "Unknown",
            "os": "Unknown",
            "device": "Unknown",
            "device_type": "Unknown",
            "brand": "Unknown",
            "model": "Unknown",
            "is_mobile": False,
            "is_tablet": False,
            "is_pc": False,
            "is_bot": False,
            "is_touch_capable": False
        }

    ua = parse(user_agent)
    
    # Дополнительная обработка для устройств
    device_info = extract_device_info(ua)
    
    return {
        "browser": get_browser_info(ua),
        "os": get_os_info(ua),
        "device": device_info["device"],
        "device_type": device_info["type"],
        "brand": device_info["brand"],
        "model": device_info["model"],
        "is_mobile": ua.is_mobile,
        "is_tablet": ua.is_tablet,
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot,
        "is_touch_capable": ua.is_touch_capable,
        "raw_ua": user_agent  # Для отладки
    }

def get_browser_info(ua):
    """Детальная информация о браузере"""
    browser = ua.browser
    version = browser.version_string
    if not version and browser.family == "Mobile Safari":
        version = extract_version(ua.ua_string, "Version/")
    
    return f"{browser.family} {version}" if version else browser.family

def get_os_info(ua):
    """Детальная информация об ОС"""
    os = ua.os
    version = os.version_string
    if not version and os.family == "iOS":
        version = extract_version(ua.ua_string, "OS ")
    
    return f"{os.family} {version}" if version else os.family

def extract_device_info(ua):
    """Расширенное определение устройства"""
    device = {
        "device": ua.device.family,
        "type": "Unknown",
        "brand": "Unknown",
        "model": "Unknown"
    }
    
    # Определение типа устройства
    if ua.is_mobile:
        device["type"] = "Mobile"
    elif ua.is_tablet:
        device["type"] = "Tablet"
    elif ua.is_pc:
        device["type"] = "PC"
    elif ua.is_bot:
        device["type"] = "Bot"
    
    # Дополнительный парсинг для конкретных устройств
    if ua.device.family != "Other":
        device["device"] = ua.device.family
    
    # Парсинг бренда и модели из строки User-Agent
    brand_model = detect_brand_and_model(ua.ua_string)
    if brand_model:
        device.update(brand_model)
    
    # Специальные случаи
    if "iPhone" in ua.ua_string:
        device.update({
            "brand": "Apple",
            "model": "iPhone",
            "type": "Mobile"
        })
    elif "iPad" in ua.ua_string:
        device.update({
            "brand": "Apple",
            "model": "iPad",
            "type": "Tablet"
        })
    elif "Macintosh" in ua.ua_string:
        device.update({
            "brand": "Apple",
            "model": "Mac",
            "type": "PC"
        })
    
    return device

def detect_brand_and_model(ua_string):
    """Определение бренда и модели устройства"""
    # Регулярные выражения для популярных устройств
    patterns = {
        "Samsung": r"Samsung[-\s]([^\s;)]+)",
        "Huawei": r"Huawei[-\s]([^\s;)]+)",
        "Xiaomi": r"Mi[-\s]([^\s;)]+)|Redmi[-\s]([^\s;)]+)",
        "Google": r"Pixel[-\s]([^\s;)]+)",
        "OnePlus": r"ONE[-\s]([^\s;)]+)",
        "Windows": r"Windows[-\s]([^\s;)]+)",
    }
    
    for brand, pattern in patterns.items():
        match = re.search(pattern, ua_string, re.I)
        if match:
            model = next((m for m in match.groups() if m), "Unknown")
            return {
                "brand": brand,
                "model": model
            }
    
    return None

def extract_version(ua_string, prefix):
    """Извлечение версии из строки User-Agent"""
    start = ua_string.find(prefix)
    if start == -1:
        return None
    
    start += len(prefix)
    end = ua_string.find(" ", start)
    version = ua_string[start:end].replace("_", ".")
    return version.split(";")[0].strip()