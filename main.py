{\rtf1\ansi\ansicpg1252\cocoartf2709
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 from fastapi import FastAPI, HTTPException\
from pydantic import BaseModel\
from geopy.distance import geodesic\
import requests\
import os\
\
app = FastAPI()\
\
# Replace with your actual API keys\
EASYPOST_API_KEY = os.getenv("EASYPOST_API_KEY")  # or hardcode for now\
GEOCODING_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")\
\
class Address(BaseModel):\
    city: str\
    zip: str\
\
class ReturnRequest(BaseModel):\
    order_id: str\
    shipping_address: Address\
    tracking_number: str\
    carrier: str\
\
@app.post("/check-return")\
def check_return(data: ReturnRequest):\
    # 1. Get return drop-off address from EasyPost\
    easypost_url = f"https://api.easypost.com/v2/trackers/\{data.carrier\}/\{data.tracking_number\}"\
    headers = \{"Authorization": f"Bearer \{EASYPOST_API_KEY\}"\}\
    response = requests.get(easypost_url, headers=headers)\
    if response.status_code != 200:\
        raise HTTPException(status_code=500, detail="Error fetching tracking info from EasyPost")\
\
    tracker = response.json().get("tracker")\
    if not tracker or not tracker.get("tracking_details"):\
        raise HTTPException(status_code=404, detail="Tracking details not found")\
\
    # Extract last known location (assume latest scan is drop-off location)\
    last_detail = tracker["tracking_details"][-1]\
    drop_off_city = last_detail.get("city")\
    drop_off_zip = last_detail.get("zip")\
\
    if not drop_off_city or not drop_off_zip:\
        raise HTTPException(status_code=400, detail="Incomplete drop-off location info")\
\
    # 2. Geocode both addresses\
    def geocode(city, zip):\
        g_url = f"https://maps.googleapis.com/maps/api/geocode/json?address=\{city\},\{zip\}&key=\{GEOCODING_API_KEY\}"\
        geo_res = requests.get(g_url)\
        geo_data = geo_res.json()\
        if geo_data['status'] != 'OK':\
            raise HTTPException(status_code=400, detail="Geocoding failed")\
        location = geo_data['results'][0]['geometry']['location']\
        return (location['lat'], location['lng'])\
\
    ship_coords = geocode(data.shipping_address.city, data.shipping_address.zip)\
    drop_coords = geocode(drop_off_city, drop_off_zip)\
\
    # 3. Compute distance\
    distance = geodesic(ship_coords, drop_coords).miles\
    is_fraud = distance > 15\
\
    return \{\
        "is_fraud": is_fraud,\
        "distance_miles": round(distance, 2),\
        "drop_off_city": drop_off_city,\
        "shipping_city": data.shipping_address.city\
    \}}