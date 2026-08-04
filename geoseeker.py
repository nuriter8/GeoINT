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


import sys
import os
import base64
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# as default, always try EXIF

# 1 : get exif data of GPS
def get_exif(img_path):

    image = Image.open(img_path)
    exif_data = image.getexif()

    if not exif_data:
        print("gps location not in metadata :( )")
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

    return float(d) + float(m) / 60.0 + float(s) / 3600.0




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

def coords_with_exif(lat, lon):

    print("COORDINATES WITH EXIF " + str(lat) + ", " + str(lon))

    print(f"https://www.google.com/maps?q={lat},{lon}")

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


if __name__ == "__main__":
    main()