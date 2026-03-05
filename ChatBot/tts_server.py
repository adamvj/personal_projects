from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from kokoro_onnx import Kokoro
import io
import soundfile as sf
import uvicorn
import re
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading Kokoro ONNX model...")
kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
print("Model loaded successfully!")

def split_text_into_chunks(text: str):
    # Split text into chunks ending in punctuation so speech has natural pauses
    chunks = re.split(r'([.?!])\s*', text)
    result = []
    
    for i in range(0, len(chunks)-1, 2):
        sentence = chunks[i] + (chunks[i+1] if i+1 < len(chunks) else '')
        if sentence.strip():
            result.append(sentence.strip())
            
    if len(chunks) % 2 != 0 and chunks[-1].strip():
        result.append(chunks[-1].strip())
        
    return result if result else [text]

@app.post("/synthesize")
async def synthesize(request: Request):
    data = await request.json()
    text = data.get("text", "")
    voice = data.get("voice", "am_adam") # Use male voice by default
    speed = data.get("speed", 1.05)
    
    if not text:
        return {"error": "Text is required"}
        
    chunks = split_text_into_chunks(text)
    
    async def audio_generator():
        for chunk in chunks:
            if not chunk: continue
            
            # Generate audio for sentence
            samples, sample_rate = kokoro.create(
                chunk, voice=voice, speed=speed, lang="en-us"
            )
            
            # Convert float32 [-1, 1] to raw 16-bit PCM for streaming
            samples_int16 = (samples * 32767).astype(np.int16)
            
            # Yield raw PCM bytes directly
            yield samples_int16.tobytes()

    return StreamingResponse(audio_generator(), media_type="audio/l16")

if __name__ == "__main__":
    print("Starting Kokoro TTS Server on port 5001...")
    uvicorn.run(app, host="0.0.0.0", port=5001)
