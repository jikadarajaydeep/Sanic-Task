import requests
from sanic import Sanic
from sanic.response import HTTPResponse
import aiohttp
import cv2
import numpy as np
import json

app = Sanic(__name__)

async def fetch_and_decode_image(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                return cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
            else:
                return None  # Handle errors by substituting with a black image
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None  # Handle errors by substituting with a black image

async def generate_composite_image(limit,offset):
    url = f"https://api.slingacademy.com/v1/sample-data/photos?limit={limit}&offset={offset}"
    image_width, image_height = 32, 32
    num_images = 132
     # Adjust the limit based on your desired concurrency

    async with aiohttp.ClientSession() as session:
        tasks = []
        # for offset in range(0, num_images, limit):
        api_url = url

        # Fetch and decode images
        image_urls = []  # Store image URLs from the API response
        try:
            async with session.get(api_url) as response:
                if response.status == 200:
                    response_data = await response.read()
                    data = json.loads(response_data)
                    image_urls = [entry['url'] for entry in data['photos']]
        except Exception as e:
            print(f"Error fetching image URLs: {e}")

        for image_url in image_urls:
            image = await fetch_and_decode_image(session, image_url)
            if image is not None:
                image = cv2.resize(image, (image_width, image_height))
                tasks.append(image)
            else:
                # Substitute with a blue image tile
                blue_tile = np.zeros((image_height, image_width, 3), dtype=np.uint8)
                blue_tile[:, :, 2] = 255  # Set blue channel to 255
                tasks.append(blue_tile)
    
    num_images = len(tasks)
    rows = (num_images + 4 - 1) // 4
    composite_image = np.zeros((rows * image_height, 4 * image_width, 3), dtype=np.uint8)

    for i, image in enumerate(tasks):
        row = i // 4
        col = i % 4
        y1 = row * image_height
        y2 = y1 + image_height
        x1 = col * image_width
        x2 = x1 + image_width
        composite_image[y1:y2, x1:x2] = image

    return composite_image
   

@app.route("/")
async def serve_composite_image(request):
    try:
        limit = int(request.args.get('limit',10))
        offset = int(request.args.get('offset',0))
        composite_image = await generate_composite_image(limit,offset)
        _, image_data = cv2.imencode('.png', composite_image)
        return HTTPResponse(body=image_data.tobytes(), content_type="image/png")
    except Exception as e:
        print(f"Error generating composite image: {e}")
        return HTTPResponse(body=b"", status=500)