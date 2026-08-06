# 3 LEVELS
# 1. EXIF: if the photo has embedded GPS (metadata), I Just extract it for free (no ai)
# 2. GeoCLIP: CLIP style model (no ai), predicts coordinates based on visual content of the picture
# 3. Claude vision: multimodal model that reasons with visual cues (buildings, roads, architecture, panels)

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

import sys
import os
import base64
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from geoclip import GeoCLIP
import anthropic

#from google import genai
from google.genai import types
import google.generativeai as genai

# as default, always try EXIF

# 1 : get exif data of GPS
def get_exif(img_path):

    image = Image.open(img_path)
    exif_data = image.getexif()

    if not exif_data:
        print("gps location not in metadata :( ")
        return None

    else:

        print("gps location is in metadata, extracting all metadata...")
        
        exif = {
        }  

        for k, v in exif_data.items():
            # k is numeric code of label
            # v is asociated value of GPS coordinates
            # TAGS translates code (k) to human nouns

            human_noun = TAGS.get(k, k)
            # if can't translate, returns same code (to avoid losing it)

            # now that we have a reading noun, we save value (v) to it
            exif[human_noun] = v

            print(human_noun)
            if(human_noun == "GPSInfo"):
                print("^ this is wht I need")

        try:
            gps_ifd = exif_data.get_ifd(0x8825)
            exif["GPSInfo"] = gps_ifd
        except KeyError:
            pass  # no GPSInfo


        print("BASIC EXIF is " + str(exif) + "\n")

        print("\n \n exif end \n \n")


        lat, lon = get_exif_coordinates(exif)
        print(">>>>>" + str(lat) + " and " + str(lon))
        if(lat and lon):
            show_coords("GEOCLIP", lat, lon)
            return True
        else:
            return False

# part of step 2
def get_gps_data(exif_data):

    if (not exif_data) or ("GPSInfo" not in exif_data) :
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




# 2. get coordinates from EXTRACTED GPS
def get_exif_coordinates(exif_data):
    print("geting into the coordinates....")

    gps = get_gps_data(exif_data)

    

    if (not gps) or ("GPSLatitude" not in gps) or ("GPSLongitude" not in gps):
        return None, None # as coordinates
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
    






def geoclip(path):
    
    top_k = 5
    
    print("using geoclip...")
    
    model = GeoCLIP()
    try:
        top_pred_gps, top_pred_prob = model.predict(path, top_k=top_k)

        # in top preds gps -> saved pairs of latitude and longitude.
        # 
        
        print(f"Top {top_k} GPS predictions \n")
        
        
        for i in range(top_k):
            
            lat, lon = top_pred_gps[i]
            print(f"Prediction {i+1}: ({lat:.6f}, {lon:.6f}) | prob: {top_pred_prob[i]:.6f}")
            
            show_coords("GEOCLIP", lat, lon)

    except Exception as e:
        print(f"Error in GEOCLIP: {e}")
        
        traceback.print_exc()
        
        
        
        
def claudevision(path):
    api_key = ""
    #while not api_key:
        
     #   api_key = input("paste your anthropic API KEY: ").strip()
        
        
      #  if not api_key:
       #     print("you need a valid anthropic API KEY, try again...")
            
    # api_key is not empty
    
    with open(path, "rb") as f:
        img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
        
    ext = path.split(".")[-1].lower()
    print(ext)
    
    
    media_type = f"image/{ext}"
    
    
    client = anthropic.Anthropic(api_key = api_key)
    
    
    response = client.messages.create(
        
        model = "claude-sonnet-4-6",
        max_tokens = 600,
        
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
    
    
    print(response.content[0].text)
    
  



def main():
    # python3 geoseeker.py img_path
    if len(sys.argv) != 2:
        
        print("use python3 geoseeker.py img_path")
        sys.exit(1)
    else:
        
        path = sys.argv[1]
        print(f"geolocating place of image {path}....")

        exif = get_exif(path)

        
        #exif_lat, exif_lon = get_exif_coordinates(exif_data)

        if exif == True:
            print("COORDINATES FOUND WITH EXIF TOOL")

        else:
            print("Not enough metadata, will resort to geoclip")
            geoclip(path)
            
            print("trying with claude vision...")
            claudevision(path)
            
            

if __name__ == "__main__":
    main()