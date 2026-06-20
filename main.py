import io
import uuid
import requests
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "online", "message": "ZepAsset v1 Overlay Backend is running!"}

@app.post("/upload")
async def upload_asset(
    api_key: str = Form(...),
    target_type: str = Form(...),
    target_id: str = Form(...),
    mode: str = Form(...),
    image_file: UploadFile = File(...)
):
    # 1. Determine sizing dimensions
    width, height = (100, 1024) if mode == "vertical" else (1024, 100)
    
    try:
        # 2. Read and resize the provided background image
        input_bytes = await image_file.read()
        base_img = Image.open(io.BytesIO(input_bytes)).convert("RGBA")
        base_img = base_img.resize((width, height), Image.Resampling.LANCZOS)
        
        # 3. Generate the checkerboard overlay pattern
        checker_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = checker_img.load()
        for y in range(height):
            for x in range(width):
                if (x + y) % 2 == 0:
                    pixels[x, y] = (0, 0, 0, 255)
                    
        # 4. Composite the checkerboard directly ABOVE the provided image
        final_img = Image.alpha_composite(base_img, checker_img)
                    
        # 5. Save the composite image to a buffer
        img_byte_arr = io.BytesIO()
        final_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
    except Exception as img_err:
        raise HTTPException(status_code=400, detail=f"Invalid image file format: {str(img_err)}")

    # 6. Setup Roblox asset data context
    creator_config = {}
    if target_type == "group":
        creator_config["groupId"] = target_id
    else:
        creator_config["userId"] = target_id

    random_title = str(uuid.uuid4())

    asset_request = {
        "assetType": "Decal",
        "displayName": random_title,
        "description": "/ ZEPASSET /",
        "creationContext": {
            "creator": creator_config
        }
    }

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

handler = app
