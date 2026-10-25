import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from database import init_db, create_user, authenticate_user, save_chat, get_chats
from services import get_weather, recommend_crop, recommend_irrigation, recommend_fertilizer, forecast_mandi, answer_farmer
from disease_predictor import predict_disease

st.set_page_config(page_title="KrishiMitra AI", page_icon="🌾", layout="wide")
init_db()

st.markdown("""
<style>
.stApp {background:linear-gradient(135deg,#f4fbf3 0%,#f8fbff 100%);}
[data-testid="stSidebar"] {background:#123d2b;}
[data-testid="stSidebar"] * {color:#fff !important;}
.hero {padding:1.5rem 1.8rem;border-radius:20px;background:linear-gradient(110deg,#124b32,#23844e);color:white;margin-bottom:1rem}
.hero h1 {font-size:2.3rem;margin:0}.hero p {font-size:1.05rem;margin:.4rem 0 0}
.metric-card {padding:1rem;border-radius:14px;background:white;border:1px solid #dceadd}
</style>
""", unsafe_allow_html=True)

def hero():
    st.markdown('<div class="hero"><h1>🌾 KrishiMitra AI Smart Farming</h1><p>Your intelligent farming companion — weather-aware advice for healthier crops and better decisions.</p></div>',unsafe_allow_html=True)

if "farmer" not in st.session_state: st.session_state.farmer = None
if "messages" not in st.session_state: st.session_state.messages = []

if not st.session_state.farmer:
    hero()
    login_tab, signup_tab = st.tabs(["🔐 Login", "🌱 Create farmer account"])
    with login_tab:
        with st.form("login_form"):
            email=st.text_input("Email address", key="login_email")
            password=st.text_input("Password", type="password", key="login_password")
            submitted=st.form_submit_button("Login", use_container_width=True)
        if submitted:
            farmer=authenticate_user(email,password)
            if farmer:
                st.session_state.farmer=farmer
                st.rerun()
            else: st.error("Login failed. Check your email and password.")

    with signup_tab:
        with st.form("signup_form"):
            name=st.text_input("Farmer name")
            email=st.text_input("Email address",key="signup_email")
            location=st.text_input("Village / city",placeholder="e.g. Coimbatore, Tamil Nadu")
            language=st.selectbox("Preferred language",["English","தமிழ்","हिन्दी","తెలుగు","ಕನ್ನಡ","मराठी"])
            password=st.text_input("Create password",type="password",key="signup_password")
            confirm=st.text_input("Confirm password",type="password")
            submitted=st.form_submit_button("Create account",use_container_width=True)
        if submitted:
            if not all([name.strip(),email.strip(),location.strip(),password]): st.error("Please complete every field.")
            elif password != confirm: st.error("Passwords do not match.")
            elif len(password)<8: st.error("Use a password with at least 8 characters.")
            else:
                ok,msg=create_user(name,email,location,language,password)
                if ok: st.success("Account created. Open Login to continue.")
                else: st.error(msg)
    st.stop()

farmer=st.session_state.farmer
with st.sidebar:
    st.markdown("## 🌾 KrishiMitra AI Smart Farming")
    st.caption(f"Welcome, {farmer['name']}")
    page=st.radio("Navigate",["🏡 Dashboard","🌦️ Weather","🌱 Crop recommendation","💧 Irrigation advice","🧪 Fertilizer advice","📈 Mandi price forecast","🩺 Plant disease detection","🤖 Farmer assistant","👨‍🌾 Farm profile"])
    st.divider()
    if st.button("Log out",use_container_width=True):
        st.session_state.farmer=None; st.session_state.messages=[]; st.rerun()

hero()
if page=="🏡 Dashboard":
    st.subheader("Your farm at a glance")
    c1,c2,c3=st.columns(3)
    c1.metric("Your location",farmer["location"])
    c2.metric("Weather", "Check live conditions →")
    c3.metric("Tools available","7 modules")
    st.info("Start with **Weather** to load current conditions, then use crop, irrigation and fertilizer advice. Recommendations are decision support; confirm critical actions with a local agricultural officer.")
    st.subheader("Explore modules")
    cols=st.columns(3)
    for col,(emoji,title,desc) in zip(cols,[("🌦️","Weather","Current conditions"),("🌱","Crop recommendation","Soil + weather"),("📈","Mandi forecast","Indicative price trend")]):
        with col:
            st.markdown(f'<div class="metric-card"><h3>{emoji} {title}</h3><p>{desc}</p></div>',unsafe_allow_html=True)


elif page=="🌦️ Weather":
    st.subheader("Live weather")
    location=st.text_input("Location for weather",value=farmer["location"])
    if st.button("Get current weather",type="primary"):
        with st.spinner("Fetching current weather…"):
            weather=get_weather(location)
        if weather.get("ok"):
            a,b,c,d=st.columns(4)
            a.metric("Temperature",f"{weather['temp_c']} °C")
            b.metric("Humidity",f"{weather['humidity']}%")
            c.metric("Rainfall",f"{weather['rain_mm']} mm")
            d.metric("Wind",f"{weather['wind_kph']} km/h")
            st.write(f"**Condition:** {weather['condition']} · **Location:** {weather['location']}")
            st.session_state.weather=weather
        else: st.error(weather["error"])
    if st.session_state.get("weather"):
        st.caption("Weather data can be used in the recommendation modules during this session.")


elif page=="🌱 Crop recommendation":
    st.subheader("Weather-aware crop recommendation")
    w=st.session_state.get("weather",{})
    if w: st.success(f"Loaded weather: {w['temp_c']}°C, humidity {w['humidity']}%, rainfall {w['rain_mm']} mm.")
    with st.form("crop_form"):
        a,b,c=st.columns(3)
        n=a.number_input("Soil Nitrogen (N)",0,200,70)
        p=b.number_input("Soil Phosphorus (P)",0,200,40)
        k=c.number_input("Soil Potassium (K)",0,200,40)
        a,b,c=st.columns(3)
        ph=a.slider("Soil pH",3.0,10.0,6.5,.1)
        temp=b.number_input("Temperature °C", -5.0,55.0,float(w.get("temp_c",28.0)))
        humidity=c.slider("Humidity %",0,100,int(w.get("humidity",65)))
        rainfall=st.number_input("Expected seasonal rainfall (mm)",0.0,3000.0,float(max(0,w.get("rain_mm",0)*30)))
        submitted=st.form_submit_button("Recommend crops",type="primary")

    
    if submitted:
        recs=recommend_crop(n,p,k,ph,temp,humidity,rainfall)
        st.session_state.crop_recommendation=recs
        for i,r in enumerate(recs,1): st.markdown(f"**{i}. {r['crop']}** — {r['reason']}")
        st.caption("These are rule-based preliminary matches, not a laboratory soil analysis.")
    if st.session_state.get("crop_recommendation"):
        options=[r["crop"] for r in st.session_state.crop_recommendation]
        selected=st.selectbox("Choose a crop for mandi forecasting",options)
        if st.button("Use selected crop for mandi forecast"):
            st.session_state.selected_crop=selected
            st.success(f"{selected} selected. Open Mandi price forecast.")


elif page=="💧 Irrigation advice":
    st.subheader("Irrigation recommendation")
    w=st.session_state.get("weather",{})
    crop=st.selectbox("Crop",["Rice","Wheat","Maize","Tomato","Cotton","Sugarcane","Groundnut","Millet"])
    soil=st.selectbox("Soil type",["Loamy","Sandy","Clay","Black","Red"])
    stage=st.selectbox("Growth stage",["Sowing / establishment","Vegetative","Flowering","Fruiting / grain filling","Maturity"])
    moisture=st.slider("Estimated soil moisture (%)",0,100,35)
    if st.button("Get irrigation advice",type="primary"):
        st.info(recommend_irrigation(crop,soil,stage,moisture,w))
elif page=="🧪 Fertilizer advice":
    st.subheader("Fertilizer advice")
    w=st.session_state.get("weather",{})
    crop=st.selectbox("Crop",["Rice","Wheat","Maize","Tomato","Cotton","Sugarcane","Groundnut","Millet"])
    stage=st.selectbox("Crop stage",["Before sowing","Early growth","Vegetative","Flowering","Fruit / grain development"])
    soil=st.selectbox("Soil test status",["Not tested","Low nitrogen","Low phosphorus","Low potassium","Balanced"])
    if st.button("Prepare fertilizer guidance",type="primary"):
        st.info(recommend_fertilizer(crop,stage,soil,w))
        st.caption("Use a soil-test report and local agricultural recommendations before applying exact quantities.")


elif page=="📈 Mandi price forecast":
    st.subheader("Indicative mandi price forecast")
    crop_default=st.session_state.get("selected_crop","Tomato")
    crop=st.selectbox("Selected crop",["Rice","Wheat","Maize","Tomato","Cotton","Sugarcane","Groundnut","Millet"],index=["Rice","Wheat","Maize","Tomato","Cotton","Sugarcane","Groundnut","Millet"].index(crop_default) if crop_default in ["Rice","Wheat","Maize","Tomato","Cotton","Sugarcane","Groundnut","Millet"] else 3)
    market=st.text_input("Mandi / market",value=farmer["location"])
    if st.button("Forecast next 7 days",type="primary"):
        df=forecast_mandi(crop,market)
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.line_chart(df.set_index("Date")["Predicted price (₹/quintal)"])
        st.warning("Demonstration forecast based on seeded sample history, not live official mandi transactions. Replace with verified AGMARKNET/eNAM historical data before real-world decisions.")



elif page == "🩺 Plant disease detection":

    st.subheader("🩺 Plant Disease Detection")

    st.write(
        "Upload a clear photo of a potato leaf. "
        "AI will analyze the image and predict the possible disease."
    )

    uploaded = st.file_uploader(
        "Upload potato leaf image",
        type=["jpg", "jpeg", "png", "webp"],
        key="plant_disease_image",
    )

    if uploaded is not None:

        st.image(
            uploaded.getvalue(),
            caption="Uploaded potato leaf",
            width=320,
        )

        if st.button(
            "🔍 Analyze Leaf Image",
            type="primary",
            key="analyze_plant_disease",
        ):

            with st.spinner("Analyzing potato leaf..."):

                # Call the inference function
                result = predict_disease(uploaded)

            if result.get("ok", False):

                label = result["label"]
                confidence = float(result["confidence"])
                confidence = max(0.0, min(1.0, confidence))

                st.success("Analysis completed!")

                st.subheader("🌱 Prediction")

                if label == "Potato healthy":
                    st.success("🌱 Healthy Potato Leaf")

                elif label == "Potato Late blight":
                    st.error("🦠 Potato Late Blight")

                elif label == "Potato Early blight":
                    st.warning("🦠 Potato Early Blight")

                else:
                    st.warning(f"Predicted class: {label}")

                st.write(f"**Model confidence: {confidence:.2%}**")
                st.progress(confidence)

                st.subheader("📊 Prediction Probabilities")

                probabilities = result.get("probabilities", {})

                for disease, probability in probabilities.items():

                    probability = float(probability)
                    probability = max(0.0, min(1.0, probability))

                    st.write(f"**{disease}: {probability:.2%}**")
                    st.progress(probability)

                st.warning(
                    "This is an AI prediction, not a confirmed diagnosis. "
                    "Consult an agricultural expert before treating crops."
                )

            else:
                st.error(
                    result.get(
                        "error",
                        "Unable to analyze this image.",
                    )
                )

                    

elif page=="🤖 Farmer assistant":
    st.subheader("AI Farmer Assistant")
    st.caption("Powered by Groq. Ask about crop care, irrigation, fertilizer, weather interpretation or common farming practices.")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    prompt=st.chat_input("Ask your farming question…")
    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Preparing farming guidance…"):
                answer=answer_farmer(prompt,farmer,st.session_state.get("weather"))
            st.markdown(answer)
        st.session_state.messages.append({"role":"assistant","content":answer})
        save_chat(farmer["id"],prompt,answer)


elif page=="👨‍🌾 Farm profile":
    st.subheader("Farmer profile")
    st.write(f"**Name:** {farmer['name']}")
    st.write(f"**Email:** {farmer['email']}")
    st.write(f"**Location:** {farmer['location']}")
    st.write(f"**Preferred language:** {farmer['language']}")
    st.caption("Weather is fetched on demand and is not automatically refreshed. Sign out when using a shared computer.")
