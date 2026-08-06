# GeoSeeker
<img width="1208" height="942" alt="Image" src="https://github.com/user-attachments/assets/57a58c34-b274-40f9-bf2e-91f60eab854e" />

**GeoSeeker** is a Python tool that geolocates a photo using three fallback layers of increasing complexity — starting with exact metadata, and falling back to AI-based visual reasoning when no metadata is available.

## How to run it
1. python3 geoseeker.py
2. open http://127.0.0.1:5500 on your browser
3. upload you picture and click 'Analyze'
4. if you want detailed data, obtain an anthropic api key and paste it on the Claude vision section

None of the data you provide is stored

## How it works

1. **EXIF extraction** (exact, free)
   If the photo has embedded GPS metadata (common with smartphone photos), GeoSeeker reads the exact coordinates directly from the file — no AI involved.

2. **GeoCLIP** (statistical, free, runs locally)
   When no GPS metadata is present, a pretrained CLIP-style neural network predicts likely coordinates purely from the visual content of the image, based on patterns learned from millions of geotagged photos worldwide. It returns a ranked list of candidate coordinates with confidence scores.

3. **Multimodal vision reasoning** (qualitative, requires an API key)
   As a complementary layer, a vision-capable LLM analyzes the image the way a human would play GeoGuessr: reading language on signs, license plate style, which side of the road traffic drives on, vegetation, climate, architecture, and cultural cues — then explains its reasoning and is explicit about its uncertainty.

| Layer | Method | Precision | Cost |
|---|---|---|---|
| 1 | EXIF metadata | Exact (meters) | Free |
| 2 | GeoCLIP | Approximate (country/region) | Free, runs locally |
| 3 | Vision LLM reasoning | Qualitative, varies | Requires your own API key |
