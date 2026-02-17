import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="WhatsApp Business Dashboard API")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Config ----------
FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
FB_API_VERSION = os.getenv("FB_API_VERSION", "v22.0")


# ---------- Models ----------
class AuthPayload(BaseModel):
    code: str


# ---------- Health ----------
@app.get("/")
async def health_check():
    return {"status": "active", "message": "WhatsApp Backend is running"}


# ---------- OAuth + Onboarding ----------
@app.post("/api/auth/whatsapp")
async def whatsapp_auth(payload: AuthPayload):
    """
    1. Exchange code for access token
    2. Fetch WABA + phone numbers (embedded signup assets)
    """

    if not FB_APP_ID or not FB_APP_SECRET:
        raise HTTPException(status_code=500, detail="Missing App Credentials")

    # STEP 1 — exchange code
    token_url = f"https://graph.facebook.com/{FB_API_VERSION}/oauth/access_token"
    token_params = {
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "code": payload.code
    }

    token_resp = requests.get(token_url, params=token_params)
    token_data = token_resp.json()

    if "access_token" not in token_data:
        raise HTTPException(status_code=400, detail=token_data)

    access_token = token_data["access_token"]

    # STEP 2 — fetch WABA assets
    assets_url = f"https://graph.facebook.com/{FB_API_VERSION}/me"
    assets_params = {
        "fields": "businesses{whatsapp_business_accounts{phone_numbers}}",
        "access_token": access_token
    }

    assets_resp = requests.get(assets_url, params=assets_params)
    assets_data = assets_resp.json()

    return {
        "access_token": access_token,
        "expires_in": token_data.get("expires_in"),
        "token_type": token_data.get("token_type"),
        "business_assets": assets_data
    }


# ---------- Dashboard Stats ----------
@app.get("/api/dashboard/stats")
async def get_whatsapp_stats(waba_id: str, access_token: str):
    url = f"https://graph.facebook.com/{FB_API_VERSION}/{waba_id}/analytics"
    params = {
        "access_token": access_token,
        "metrics": "messages_sent,messages_delivered,messages_read"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=data)

    return {
        "waba_id": waba_id,
        "analytics": data.get("data", [])
    }


# ---------- Phone Numbers ----------
@app.get("/api/dashboard/phone-numbers")
async def get_phone_numbers(waba_id: str, access_token: str):
    url = f"https://graph.facebook.com/{FB_API_VERSION}/{waba_id}/phone_numbers"
    params = {"access_token": access_token}

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=data)

    return data


# ---------- Run ----------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
