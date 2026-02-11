import os
import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="WhatsApp Business Dashboard API")

# --- CORS Configuration ---
# This allows your frontend (React, Vue, etc.) to make requests to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
FB_API_VERSION = os.getenv("FB_API_VERSION", "v21.0")

# --- Models ---
class AuthPayload(BaseModel):
    code: str

# --- Endpoints ---

@app.get("/")
async def health_check():
    return {"status": "active", "message": "WhatsApp Backend is running"}

@app.post("/api/auth/whatsapp")
async def whatsapp_auth(payload: AuthPayload):
    """
    Exchanges the 'code' from the Meta Embedded Signup for an Access Token.
    """
    if not FB_APP_ID or not FB_APP_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured: Missing App Credentials")

    url = f"https://graph.facebook.com/{FB_API_VERSION}/oauth/access_token"
    params = {
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "code": payload.code
    }
    
    response = requests.get(url, params=params)
    res_data = response.json()
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, 
            detail=res_data.get("error", "Failed to exchange token")
        )
    
    # This token is what you use for future requests
    # In a real app, save this to your database!
    return {
        "access_token": res_data.get("access_token"),
        "expires_in": res_data.get("expires_in"),
        "token_type": res_data.get("token_type")
    }

@app.get("/api/dashboard/stats")
async def get_whatsapp_stats(waba_id: str, access_token: str):
    """
    Fetches messaging statistics (sent, delivered, read) for a specific WABA ID.
    """
    url = f"https://graph.facebook.com/{FB_API_VERSION}/{waba_id}/analytics"
    params = {
        "access_token": access_token,
        "metrics": "messages_sent,messages_delivered,messages_read"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, 
            detail=data.get("error", "Failed to fetch stats")
        )
        
    return {
        "waba_id": waba_id,
        "analytics": data.get("data", [])
    }

@app.get("/api/dashboard/phone-numbers")
async def get_phone_numbers(waba_id: str, access_token: str):
    """
    Fetches the list of phone numbers and their quality status.
    """
    url = f"https://graph.facebook.com/{FB_API_VERSION}/{waba_id}/phone_numbers"
    params = {"access_token": access_token}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch numbers")
        
    return data

if __name__ == "__main__":
    import uvicorn
    # Read port from .env or default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)