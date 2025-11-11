from flask import Flask, render_template, request
from kimi_api import ask_kimi
from kimi_api import generate_map_iframe
from markupsafe import Markup
from kimi_api import extract_locations
from kimi_api import generate_all_iframes_with_links
import re
import redis

# aecfb2f4a9b06fb006aad013871c7ce5   我的高德key api
AMAP_KEY = "aecfb2f4a9b06fb006aad013871c7ce5"  # 替换为你的高德
# 简历redis数据库配置
# redis_client = redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)

app = Flask(__name__)

# 将kimi_api中的generate_map_iframe和get_location函数集成到Flask应用中
@app.route("/", methods=["GET", "POST"])
def index():
    reply = ""
    map_iframe = ""
    
    if request.method == "POST":
        user_input = request.form["user_input"]
        raw_reply = ask_kimi(user_input)
        reply =Markup(linkify_locations(raw_reply))

        locations = extract_locations(raw_reply)
        try:
            reply =ask_kimi(user_input)
        except Exception as e:
            reply = f"<p class='text-danger'>❌ 生成行程失败，请稍后再试。错误信息：{str(e)}</p>"
        print("提取到的景点：", locations)
        if len(locations) >=2:
            map_iframe=Markup(generate_all_iframes_with_links(locations,AMAP_KEY))
        else:
            map_iframe = "<p>请提供至少两个地点以生成地图。</p>"
    
 
    return render_template("index.html", reply=reply,map_iframe=map_iframe)


# 生成高德地图的链接
def linkify_locations(text):
     # 匹配（地点名）格式，比如：象鼻山（象鼻山）
    pattern = r"（(.*?)）"
    def replacer(match):
        location = match.group(1)
        amap_url = f"https://www.amap.com/search?query={location}"
        return f'（<a href="{amap_url}" target="_blank">{location}</a>）'
    return re.sub(pattern, replacer, text)




if __name__ == "__main__":
    app.run(debug=True)
