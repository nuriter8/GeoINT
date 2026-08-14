# LEVELS
# 0. photo adaptation : CLAHE, Unsharp mask
# 1. EXIF: if the photo has embedded GPS (metadata), I Just extract it for free (no ai)
# 2. GeoCLIP: CLIP style model (no ai), predicts coordinates based on visual content of the picture
# 3. Claude vision: multimodal model that reasons with visual cues (buildings, roads, architecture, panels)
# 4. Tesseract: OCR, program to extract names, licence plates, traffic signs...
# 5. Using plantNet (to-do)

#reliability
# EXIF: exact if metadata was provided
# geoclip: statistical, like a pretrained neural network. gives a result based on seen sites, but can't reason on its own
# claude vision: bad accuracy unless known places

# you'll need :
# pip install Pillow requests geoclip anthropic
# pip install geoclip
# pip install torch==2.2.0 torchvision==0.17.0 --index-url https://download.pytorch.org/whl/cpu
# pip install torch==2.2.0 torchvision==0.17.0
# python3 -c "import numpy; print(numpy.__version__)"
# pip install "numpy<2.0" --force-reinstall
# import traceback
# pip install anthropic
# pip install flask
# pip install flask_cors

# sudo apt-get install tesseract-ocr
# sudo apt-get install tesseract-ocr-spa tesseract-ocr-eng
# pip install pytesseract requests
# pip install opencv-python
# pip install "transformers==4.36.2" --force-reinstall
# pip install easyocr
# pip install "transformers==4.36.2" --force-reinstall
# python3 -c "import numpy; print(numpy.__version__)"
# pip install "numpy<2.0" --force-reinstall



import sys
import os
import base64
import traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geoclip import GeoCLIP
import anthropic
import google.generativeai as genai
import json
import pytesseract
import cv2
import numpy as np
import os

import easyocr

print("loading EasyOCR model...")
ocr_reader = easyocr.Reader(['en', 'es'], gpu=False)
print("easyocr loaded")




app = Flask(__name__, static_folder='webpage', static_url_path='')
CORS(app)

def save_preprocessed(cv2_image, path):
    rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    pil_img.save(path, "JPEG", quality=95)
    
    
def save_step(img, step_number, instruction, folder="preprocess"):
    
    os.makedirs(folder, exist_ok=True)

    output = img.copy()

    if len(output.shape) == 2:
        output = cv2.cvtColor(
            output,
            cv2.COLOR_GRAY2BGR
        )

    font = cv2.FONT_HERSHEY_SIMPLEX
   

    cv2.putText(
        
        output,
        f"STEP {step_number}",
        (20, 110),
        font,
        3.0,
        (0, 0, 255),
        2,
        cv2.LINE_AA
    )

    cv2.putText(
        output,
        instruction,
        (20, 70),
        font,
        0.6,
        (0, 0, 255),
        2,
        cv2.LINE_AA
    )

    filename = os.path.abspath(
        os.path.join(
            folder,
            f"step{step_number}.jpg"
        )
    )

    print("-"*30)
    print("STEP:", step_number)
    print("FILENAME:", repr(filename))
    print("EXTENSION:", os.path.splitext(filename)[1])
    print("SHAPE:", output.shape)
    print("WRITER JPG:", cv2.haveImageWriter(".jpg"))
    print("-"*30)

    success = cv2.imwrite(filename, output)

    print("IMWRITE RESULT:", success)

    if not success:
        raise RuntimeError(
            f"Could not save image: {filename}"
        )
 
    
    
def preprocess_image(img_path):
    
    img = cv2.imread(img_path)
    save_step(img, 1, "cv2.cvtColor(img, cv2.COLOR_BGR2LAB)")
     
    # clahe: separates L (LIGHT) and A, B (COLOR INFO)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
   
    
    l, a, b = cv2.split(lab)
    save_step(l, 2, "l: cv2.cvtColor(img, cv2.COLOR_BGR2LAB)")
    save_step(a, 3, "a: cv2.cvtColor(img, cv2.COLOR_BGR2LAB)")
    save_step(b, 4, "b: cv2.cvtColor(img, cv2.COLOR_BGR2LAB)")
    
    # clipLimit: contrast
    # tileGridSize: divides img in blocks of 8x8, equalizes each one separately
    
    clahe = cv2.createCLAHE(clipLimit= 3.0, tileGridSize= (8,8))
    l_corrected = clahe.apply(l)
    balanzed = cv2.merge((l_corrected, a, b))
    balanzed = cv2.cvtColor(balanzed, cv2.COLOR_LAB2BGR)
    
    # SHARPNESS
    no_focus = cv2.GaussianBlur(balanzed, (0, 0), sigmaX=3)
    sharp = cv2.addWeighted(balanzed, 1.5, no_focus, -0.5, 0)
    
    return sharp


def get_exif(img_path):
    image = Image.open(img_path)
    exif_data = image.getexif()

    if not exif_data:
        print("gps location not in metadata :( ")
        return None
    else:
        print("gps location is in metadata, extracting all metadata...")
        exif = {}
        for k, v in exif_data.items():
            human_noun = TAGS.get(k, k)
            exif[human_noun] = v
            print(human_noun)
            if(human_noun == "GPSInfo"):
                print("^ this is wht I need")

        try:
            gps_ifd = exif_data.get_ifd(0x8825)
            exif["GPSInfo"] = gps_ifd
        except KeyError:
            pass

        print("BASIC EXIF is " + str(exif) + "\n")
        print("\n \n exif end \n \n")

        lat, lon = get_exif_coordinates(exif)
        print(">>>>>" + str(lat) + " and " + str(lon))
        if(lat and lon):
            show_coords("GEOCLIP", lat, lon)
            return {"lat": lat, "lon": lon}
        else:
            return None

def get_gps_data(exif_data):
    if (not exif_data) or ("GPSInfo" not in exif_data):
        return None

    gps_info = exif_data['GPSInfo']
    print("\n all that have gpsinfo " + str(gps_info))
    exif_gps = {}

    for tag, value in gps_info.items():
        human_noun = GPSTAGS.get(tag, tag)
        exif_gps[human_noun] = value
        print("converting " + str(tag) + " to : " + str(human_noun))

    print("EXIF GPS: " + str(exif_gps))
    return exif_gps

def to_degrees(value):
    d, m, s = value
    degrees = float(d) + float(m) / 60.0 + float(s) / 3600.0
    print(f"{value} to degrees: {degrees}")
    return degrees

def get_exif_coordinates(exif_data):
    print("geting into the coordinates....")
    gps = get_gps_data(exif_data)

    if (not gps) or ("GPSLatitude" not in gps) or ("GPSLongitude" not in gps):
        return None, None
    else:
        print("coordinates captured!!!")
        
        
        lat = to_degrees(gps["GPSLatitude"])
        
        if gps.get("GPSLatitudeRef") == "S":
            lat = -lat
            
        lon = to_degrees(gps["GPSLongitude"])
        
        if gps.get("GPSLongitudeRef") == "W":
            lon = -lon
            
            
        print("lat and lon " + str(lat) + ", " + str(lon))
        return lat, lon

def show_coords(method, lat, lon):
    print(f"COORDINATES WITH {method}, {lat} , {lon}")
    print(f"https://www.google.com/maps?q={lat},{lon} \n")

print("loading GEOCLIP model, can take some time...")
geoclip_model = GeoCLIP()
print("geoclip loaded")

def geoclip(path):
    top_k = 5
    try:
        top_pred_gps, top_pred_prob = geoclip_model.predict(path, top_k=top_k)
        results = []
        for i in range(top_k):
            lat, lon = top_pred_gps[i]
            prob = top_pred_prob[i]
            results.append({
                "lat": float(lat),
                "lon": float(lon),
                "prob": float(prob)
            })
        
            show_coords("geoclip", lat, lon)
            
        return results
    except Exception as e:
        print(f"Error in GEOCLIP: {e}")
        traceback.print_exc()
        return None

def claudevision(path, api_key):
    with open(path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")

   
    fmt_map = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "GIF": "image/gif",
        "WEBP": "image/webp",
    }
    with Image.open(path) as img:
        real_format = img.format  # ej "PNG", "JPEG"
    media_type = fmt_map.get(real_format)
    if not media_type:
        raise ValueError(f"Image format not supported with anthropic API: {real_format}")

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                {"type": "text", "text": (
                    "use plain text, no markdown"
                    "Act as an expert in visual geolocation (GeoGuessr style). "
                    "Analyze visible clues: language on signs, license plate type, "
                    "analyze visible cues about the main characters of the picture if there are any, if not, common attributes among the people in the picture"
                    "which side of the road traffic drives on, vegetation, climate, architecture, traffic signs, stores, people, culture, etc"
                    "Give your best estimate of country and region/city, and explain which clues you're basing it on. "
                    "Be honest about your level of uncertainty"
                    "give possible coordinates"
                )}
            ]
        }]
    )
    return response.content[0].text

def extract_text_tesseract(img_path):
    image = Image.open(img_path)
    text = pytesseract.image_to_string(image, lang="spa+eng+fra+deu+ita")
    
    #text = "test"

    
    return text.strip()
    
    
def extract_text_easyocr(img_path):
    
    
    results = ocr_reader.readtext(img_path)

    texts = [text for (_, text, trust) in results if trust > 0.35]

    if not texts:
        return ""

    final_text = " | ".join(texts)
    print("TEXT IN IMAGE (EasyOCR):" + final_text)

    return final_text

# FLASK
@app.route('/')
def index():
    return send_from_directory('webpage', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('webpage', path)

    
    
@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        temp_path = 'temp_image.jpg'
        file.save(temp_path)

        preprocess_path = 'temp_img_preprocessed.jpg'

        try:
        
            exif_result = get_exif(temp_path)
            if exif_result:
                response_data = {
                    'source': 'exif',
                    'exif': {
                        'lat': exif_result['lat'],
                        'lon': exif_result['lon']
                    }
                }
                return jsonify(response_data)

      
            sharp = preprocess_image(temp_path)
            save_preprocessed(sharp, preprocess_path)
            geoclip_results = geoclip(preprocess_path)

            if geoclip_results:
                ocr_text = extract_text_easyocr(preprocess_path)
                print(ocr_text)
                response_data = {
                    'source': 'geoclip',
                    'geoclip': geoclip_results,
                    'ocr': ocr_text
                }
                return jsonify(response_data)

            return jsonify({'error': 'Could not determine location'}), 500

        finally:
            for p in (temp_path, preprocess_path):
                if os.path.exists(p):
                    os.remove(p)

    except Exception as e:
        print(f"ERROR in analyze: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
    

@app.route('/api/vision', methods=['POST'])
def vision():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        api_key = request.form.get('api_key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 400
        
        file = request.files['image']
        temp_path = 'temp_image.jpg'
        file.save(temp_path)
        
        try:
            result = claudevision(temp_path, api_key)
            return jsonify({'text': result})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"ERROR in vision: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"geolocating place of image {path}....")
        exif = get_exif(path)
        if exif:
            print("COORDINATES FOUND WITH EXIF TOOL")
        else:
            print("Not enough metadata, will resort to geoclip")
            geoclip(path)
            print("trying with claude vision...")
            api_key = input("paste your anthropic API KEY: ").strip()
            claudevision(path, api_key)
    else:
        app.run(debug=True, host='0.0.0.0', port=5518, use_reloader=False)