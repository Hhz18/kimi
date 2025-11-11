import requests
import re
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import redis


KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_API_KEY = "sk-q9WiNYtIFGhcJQRLTM8ZplHzGdJGPq0hhWHR7NnopYTjkAtF"

# redis 连接
redis_client = redis.Redis(host='localhost', port=6379, db=0)


HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KIMI_API_KEY}"
}

@retry(stop=stop_after_attempt(3),wait=wait_fixed(2))# 最多重试3次，每次间隔2秒
def ask_kimi(user_input):
    # 更结构化的prompt
    messages = [
        {
        "role": "system",
        "content": (
            "你是一个专业的旅行规划助手，你的任务是根据用户的出发城市、目的地城市和旅游时间，生成一个详细的行程安排。"
            "你的输出格式需要非常规范，确保地图导航不会出错："
            "\n\n"
            "1. 每一个地点（无论是否在标题中），都必须标明【城市 + 地点名称】的组合，例如：\n"
            "   - 回民街 → 西安回民街\n"
            "   - 大雁塔 → 西安大雁塔\n"
            "   - 华清池 → 西安华清池\n"
            "   - 而不是只写“回民街”或“华清池”\n\n"
            "2. 格式要求如下：\n"
            # "   - 正文中写：游览西安大雁塔（西安大雁塔）\n"
            "   - 每个标题都需要给这个标题地点添加括号 如：### 第1天：成都（成都）\n"
            "   - 标题中写：### 第2天：西安古城墙（西安古城墙）- 回民街（西安回民街）\n\n"
            "3. 出发地和目的地必须明确。\n"
            "   - 如“成都出发 → 西安”必须写作 成都（成都） → 西安（西安）\n\n"
            "4. 如果你不确定景点所属城市，请自动参考出发地或当天主要城市作为默认归属地。\n\n"
            "请严格遵守以上规则。"
        )
        },
        {"role": "user", "content": user_input}
    ]
    
    #调用kimi API 
    payload = {
        "model": "moonshot-v1-8k",  # 也可以用更大模型
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(KIMI_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        logging.error(f"调用kimi出错：{e}")
        return f"调用失败：{e}"



# location_cache = {}
# def get_location(keyword, amap_key="你的高德地图API Key"):
#      # 先从 Redis 查询缓存
#     cache_key = f"amap:loc:{keyword}"
#     cached_value = redis_client.get(cache_key)
#     if cached_value:
#         return cached_value
    
#     url = f"https://restapi.amap.com/v3/geocode/geo"
#     params = {
#         "address": keyword,
#         "key": amap_key
#     }
#     try:  # ✅ 正确缩进：与函数体保持一致
#         res = requests.get(url, params=params, timeout=5).json()
#         if res.get("geocodes"):
#             location = res["geocodes"][0]["location"]  # 格式：'经度,纬度'
#             location_cache[keyword] = location
#             return location
#     except requests.RequestException as e:
#         logging.error(f"高德API查询失败：{e}")
#     return None
location_cache = {}
def get_location(keyword,amap_key="你的高德地图API Key"):
    if keyword in location_cache:
        return location_cache[keyword]
    
    url =f"https://restapi.amap.com/v3/geocode/geo"
    params = {
        "address": keyword,
        "key":  amap_key
    }
    try:
        res =requests.get(url, params=params,timeout=5).json()
        if res.get("geocodes"):
            location = res["geocodes"][0]["location"] #格式：'经度'，'纬度'
            location_cache[keyword] =location
            return location
    except requests.RequestException as e:
        logging.error(f"高德API查询失败：{e}")
    return None

def generate_map_iframe(start_name,end_name,amap_key,mode ="car"):
    start_loc =get_location(start_name,amap_key)
    end_loc = get_location(end_name,amap_key)
    if start_loc and end_loc:
        return (
            f'<iframe class="amap-iframe" '
            f'data-start="{start_loc}" data-end="{end_loc}" '
            f'src="https://uri.amap.com/navigation?from={start_loc},{start_name}&to={end_loc},{end_name}&mode={mode}&policy=1&src=travel-planner" '
            f'width="100%" height="300" frameborder="0"></iframe>'
        )
    return "<p>地图生成失败</p>"


# 从生成文本中提取地点名和名称列表
def extract_locations(text):
    # 提取所有地点（在括号里的）
    pattern = r"（(.*?)）"
    locations =re.findall(pattern, text)
    # 去重 +保留顺序
    seen = set()
    ordered_locations = []
    for loc in locations:
        if loc not in seen:
            seen.add(loc)
            ordered_locations.append(loc)
    return ordered_locations

# w为每一个地点生成地图路线
def generate_all_iframes_with_links(location_list,amap_key):
    if len(location_list)<2:
        return "<p>地点列表长度必须大于等于2 </p>"
    
    iframe_blocks=[]
    for i in range(len(location_list)-1):
        start =location_list[i]
        end =location_list[i+1]

        iframe =generate_map_iframe(start, end, amap_key)
        div_class ="visible-map" if i<3 else "hidden-map"
        block =(
            f'<div class="map-frame {div_class}">'
            f"<p><b>{start} → {end}</b></p>{iframe}</div>"
        )
        iframe_blocks.append(block)
        # 生成高德地图链接
        toggle_button =(
            '<div class="text-center mt-3">'
            '<button class="btn btn-outline-primary" onclick="showMoreMaps()">展开更多路线</button>'
            '</div>'
        )
        
    return "\n".join(iframe_blocks) + toggle_button

def validate_city_prefix(location_name,city_hint):
    """确保地名前带城市，如'华清池'->'西安华清池'"""
    if city_hint not in location_name:
        return city_hint + location_name
    return location_name
def generate_amap_url(start,end,amap_key):
    start_loc =get_location(start,amap_key)
    end_loc =get_location(end,amap_key)
    if start_loc and end_loc:
        return(
             f"https://uri.amap.com/navigation?"
            f"from={start_loc},{start}&to={end_loc},{end}"
            f"&mode=car&policy=1&src=travel-planner"
        )
    return "javascript:void(0);"