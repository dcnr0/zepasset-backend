import os
import io
import uuid
import requests
from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

app = FastAPI()

# Enable CORS so your Chrome extension frontend can securely communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_asset(
    api_key: str = Form(...),
    target_type: str = Form(...),
    target_id: str = Form(...),
    mode: str = Form(...)
):
    # 1. Determine sizing dimensions based on user mode selection
    width, height = (100, 1024) if mode == "vertical" else (1024, 100)
    
    # 2. Generate the transparent and black checkerboard matrix using Pillow
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            if (x + y) % 2 == 0:
                pixels[x, y] = (0, 0, 0, 255)
                
    # 3. Save the image bytes to a buffer stream
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    # 4. Check target context configuration (User ID vs Group ID mapping)
    creator_config = {}
    if target_type == "group":
        creator_config["groupId"] = target_id
    else:
        creator_config["userId"] = target_id

    # Generate a completely random UUID version 4 string for the asset title
    random_title = str(uuid.uuid4())

    asset_request = {
        "assetType": "Decal",
        "displayName": random_title,
        "description": "/ ZEPASSET /",
        "creationContext": {
            "creator": creator_config
        }
    }

    # 5. Dispatch multipart/form-data transaction payloads directly to Roblox Assets API
    files = {
        'request': (None, requests.utils.quote(str(asset_request)), 'application/json'),
        'fileContent': (f'checkerboard_{width}x{height}.png', img_byte_arr, 'image/png')
    }
    
    headers = {
        'x-api-key': api_key
    }

    try:
        response = requests.post(
            'https://apis.roblox.com/assets/v1/assets', 
            headers=headers, 
            files=files
        )
        if response.status_code in [200, 201]:
            return {"status": "success", "message": "Image uploaded successfully!"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
