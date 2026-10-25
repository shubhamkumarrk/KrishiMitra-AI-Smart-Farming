import os, requests, pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv
load_dotenv()

print(os.getenv("OPENWEATHER_API_KEY"))

# def get_weather(location):
#     key=os.getenv("WEATHER_API_KEY")
#     #if not key: return {"ok":False,"error":"WEATHER_API_KEY is missing. Add it to your .env file and restart the app."}
#     try:
#         r=requests.get("https://api.openweathermap.org/data/2.5/weather",params={"key":key,"q":location,"aqi":"no"},timeout=12)
#         if r.status_code != 200:
#             try: detail=r.json().get("error",{}).get("message","Weather provider request failed.")
#             except Exception: detail="Weather provider request failed."
#             return {"ok":False,"error":f"Weather API error: {detail}"}
#         d=r.json(); cur=d["current"]
#         return {"ok":True,"location":d["location"]["name"]+", "+d["location"]["country"],"temp_c":cur["temp_c"],"humidity":cur["humidity"],"rain_mm":cur["precip_mm"],"wind_kph":cur["wind_kph"],"condition":cur["condition"]["text"]}
#     except requests.RequestException: return {"ok":False,"error":"Could not reach the weather service. Check your internet connection and API key."}


def get_weather(location):
    key = os.getenv("OPENWEATHER_API_KEY")

    if not key:
        return {
            "ok": False,
            "error": "OPENWEATHER_API_KEY is missing from .env"
        }

    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "appid": key,
                "q": location,
                "units": "metric"
            },
            timeout=12
        )

        d = r.json()

        if r.status_code != 200:
            detail = d.get("message", "Weather request failed")
            return {
                "ok": False,
                "error": f"Weather API error ({r.status_code}): {detail}"
            }

        cur = d["main"]
        weather = d["weather"][0]

        return {
            "ok": True,
            "location": d["name"] + ", " + d["sys"]["country"],
            "temp_c": cur["temp"],
            "humidity": cur["humidity"],
            "rain_mm": d.get("rain", {}).get("1h", 0),
            "wind_kph": round(d.get("wind", {}).get("speed", 0) * 3.6, 2),
            "condition": weather["description"].title()
        }

    except requests.RequestException as e:
        return {
            "ok": False,
            "error": f"Weather connection failed: {e}"
        }



def recommend_crop(n,p,k,ph,temp,humidity,rainfall):
    crops=[
      ("Rice",abs(temp-27)/8+abs(humidity-82)/25+abs(rainfall-1200)/900+abs(ph-6.2)/2,"Warm, humid conditions and reliable water availability generally suit rice."),
      ("Wheat",abs(temp-20)/8+abs(humidity-50)/30+abs(rainfall-500)/700+abs(ph-6.8)/2,"Cooler growing conditions and moderate seasonal rainfall generally suit wheat."),
      ("Maize",abs(temp-25)/10+abs(humidity-60)/35+abs(rainfall-650)/800+abs(ph-6.3)/2,"Maize can suit warm conditions with well-drained soil and adequate moisture."),
      ("Cotton",abs(temp-29)/10+abs(humidity-55)/35+abs(rainfall-700)/900+abs(ph-7)/2,"Cotton generally prefers warm conditions and a long frost-free season."),
      ("Tomato",abs(temp-23)/8+abs(humidity-60)/35+abs(rainfall-600)/800+abs(ph-6.2)/2,"Tomato often performs best in moderate temperatures and well-drained soil."),
      ("Groundnut",abs(temp-27)/10+abs(humidity-60)/35+abs(rainfall-600)/800+abs(ph-6.3)/2,"Groundnut can suit warm conditions and light, well-drained soils."),
      ("Millet",abs(temp-29)/12+abs(humidity-45)/40+abs(rainfall-400)/700+abs(ph-6.5)/2,"Millets can be options in warm areas with comparatively lower rainfall.")
    ]
    # Soil nutrient values are surfaced as context, but crop suitability is not a substitute for a validated local model.
    return [{"crop":x[0],"reason":x[2]+f" Soil readings N={n}, P={p}, K={k}, pH={ph:.1f} should be checked against local crop requirements."} for x in sorted(crops,key=lambda z:z[1])[:3]]

def recommend_irrigation(crop,soil,stage,moisture,weather=None):
    weather=weather or {}
    if moisture<25: msg="Soil moisture is low. Check root-zone moisture and consider irrigating soon if the crop is not waterlogged."
    elif moisture<45: msg="Moisture is moderate. Recheck the root zone and crop condition before deciding whether to irrigate."
    else: msg="Moisture reading is relatively high. Avoid automatic irrigation; check drainage and root-zone conditions first."
    if weather.get("rain_mm",0)>=2: msg+=" Recent measured rainfall is present; reassess soil moisture before adding water."
    if soil=="Sandy": msg+=" Sandy soils drain quickly; smaller, more frequent irrigation may be appropriate."
    elif soil=="Clay": msg+=" Clay soils retain water longer; avoid prolonged saturation."
    if stage=="Flowering / fruiting / grain filling": msg+=" Monitor closely during flowering or grain/fruit filling, when water stress may reduce yield."
    return f"**{crop} — {stage}:** {msg} Use local crop guidance and actual soil measurements; weather API current rainfall is not a forecast."

def recommend_fertilizer(crop,stage,soil_status,weather=None):
    advice={"Low nitrogen":"Consider nitrogen management based on a soil test and the crop's growth stage; avoid over-application.",
    "Low phosphorus":"A soil-test-confirmed phosphorus deficiency may need correction, with placement and dose based on local recommendations.",
    "Low potassium":"If a soil test confirms low potassium, use a locally recommended potassium source and rate.",
    "Balanced":"Avoid adding nutrients without evidence of need; follow the crop-specific nutrient schedule.",
    "Not tested":"Get a soil test before choosing a fertilizer dose. Consider organic matter, previous crop and local extension recommendations."}
    rain=(weather or {}).get("rain_mm",0)
    extra=" Current observed rainfall is notable; avoid applying fertilizer immediately before heavy rain if runoff/leaching risk is high." if rain>=5 else ""
    return f"**{crop}, stage: {stage}.** {advice[soil_status]}{extra} Exact fertilizer quantity depends on soil-test values, cultivar, yield target and local agricultural guidance."

def forecast_mandi(crop,market):
    # Stable illustrative baseline series. Replace with verified market-wise AGMARKNET/eNAM data for real forecasting.
    base={"Rice":2400,"Wheat":2600,"Maize":2200,"Tomato":2850,"Cotton":7200,"Sugarcane":350,"Groundnut":5800,"Millet":2700}.get(crop,2500)
    dates=[date.today()+timedelta(days=i) for i in range(1,8)]
    values=[]
    for i,d in enumerate(dates):
        price=round(base*(1+0.012*i+0.018*((i%3)-1)),2)
        values.append({"Date":d.isoformat(),"Crop":crop,"Market":market,"Predicted price (₹/quintal)":price})
    return pd.DataFrame(values)

def answer_farmer(prompt,farmer,weather=None):
    key=os.getenv("GROQ_API_KEY")
    if not key: return "The AI assistant is not configured yet. Add GROQ_API_KEY to your .env file and restart the app."
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage,HumanMessage
        llm=ChatGroq(model=os.getenv("GROQ_MODEL","openai/gpt-oss-120b"),api_key=key,temperature=0.2)
        context="No live weather has been loaded in this session."
        if weather and weather.get("ok"): context=f"Current observed weather in {weather['location']}: {weather['temp_c']} C, humidity {weather['humidity']}%, rainfall {weather['rain_mm']} mm, condition {weather['condition']}."
        system=f"""You are KrishiMitra AI, a careful agriculture assistant. Give concise, practical farming guidance in {farmer['language']}. Farmer location: {farmer['location']}. {context} Never invent live weather, market prices, or guaranteed yields. Ask for missing crop/soil details when necessary. Do not give exact pesticide or fertilizer doses without sufficient verified context. Encourage local agricultural extension advice for high-impact decisions."""
        result=llm.invoke([SystemMessage(content=system),HumanMessage(content=prompt)])
        return result.content if isinstance(result.content,str) else str(result.content)
    except Exception as e:
        return f"Could not reach Groq. Check GROQ_API_KEY, model access and internet connection. Details: {str(e)[:240]}"
