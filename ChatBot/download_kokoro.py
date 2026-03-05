import os
from huggingface_hub import hf_hub_download

# Download Kokoro ONNX model and voices map
print("Downloading Kokoro ONNX models (this might take a minute)...")
model_path = hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename="kokoro-v0_19.onnx")
voices_path = hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename="voices.json")

print(f"Model downloaded to: {model_path}")
print(f"Voices downloaded to: {voices_path}")
