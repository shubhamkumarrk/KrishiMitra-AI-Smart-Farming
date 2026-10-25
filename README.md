# KrishiMitra AI — Smart Farming MVP

## Features
- Farmer signup/login with SQLite and PBKDF2 password hashing
- Current weather via WeatherAPI.com (`WEATHER_API_KEY`)
- Weather-aware rule-based crop matching
- Irrigation and fertilizer decision-support guidance
- 7-day illustrative mandi price trend
- Groq-powered farmer assistant (`GROQ_API_KEY`, model defaults to `openai/gpt-oss-120b`)
- Plant leaf image classification using a public Hugging Face Transformers model

## Setup (Windows PowerShell)
```powershell
cd path\to\KrishiMitra_AI
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
streamlit run app.py
```

Put your real keys in `.env`. Never commit `.env` to GitHub. `.env.example` is safe to commit.

## Important accuracy notes
- The mandi forecast is deliberately marked illustrative and is **not** a trained forecasting model or live official mandi data. Before relying on it, connect verified market-wise historical prices (for example, AGMARKNET/eNAM data), then train and evaluate a time-series model per crop and market.
- Crop recommendations are transparent rule-based matches, not a validated agronomic ML model. Soil laboratory results and local season/cultivar guidance matter.
- Irrigation advice is decision support; current rainfall from the weather endpoint is not a rainfall forecast.
- Plant disease classification downloads a public model on first use. Model availability, supported labels and prediction accuracy depend on the model repository. Validate predictions with an agricultural expert.
- Use HTTPS in production, rate-limit login/API calls, protect secrets, add session expiry/CSRF protections, and review security before deploying publicly.

## Files
- `app.py`: Streamlit UI/navigation
- `database.py`: account and chat persistence
- `services.py`: weather, recommendations, mandi demo forecast, Groq assistant
- `disease.py`: plant-image classifier
- `.env.example`: environment variable template
