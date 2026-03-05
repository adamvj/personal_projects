# Local Setup Guide: [modern dope] AI Chatbot

This guide explains how to run the [modern dope] "Floyd" Chatbot locally on your machine for development and testing.

## Prerequisites
1. **Node.js** (v18 or higher)
2. **Python** (v3.12 recommended)
3. **Gemini API Key** (Get one from Google AI Studio)

---

## 1. Environment Setup

First, ensure you have an environment variables file. Create a file named `.env` in the root of the project folder:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
PORT=3000
```

---

## 2. Start the Node.js Chat Backend
This server manages the chat logic, securely holds your API key, and processes responses using `knowledge.md`.

1. Open a terminal and navigate to the project folder.
2. Install the Node dependencies:
   ```bash
   npm install
   ```
3. Start the server:
   ```bash
   node server.js
   ```
   *You should see: `Chatbot server running at http://localhost:3000`*

---

## 3. Start the Python TTS (Voice) Backend
This server runs the local Kokoro ONNX model to generate the dynamic male AI voice.

1. Open a **second** terminal window and navigate to the project folder.
2. Create a Python virtual environment (only needed the first time):
   ```bash
   python3 -m venv venv
   ```
3. Activate the virtual environment:
   - **Mac/Linux:** `source venv/bin/activate`
   - **Windows:** `venv\Scripts\activate`
4. Install the Python dependencies (only needed the first time):
   ```bash
   pip install kokoro-onnx soundfile fastapi uvicorn numpy httpx
   ```
5. Ensure the model files are present in the root directory:
   - `kokoro-v0_19.onnx`
   - `voices.bin`
   *(If not, download them from the kokoro-onnx github releases).*
6. Start the voice server:
   ```bash
   python3 tts_server.py
   ```
   *You should see: `Starting Kokoro TTS Server on port 5001...`*

---

## 4. Test the App
With both servers running, test the application locally:

1. Open your web browser.
2. Navigate to: `http://localhost:3000`
3. The chatbot toggle button should appear in the bottom right corner.
4. Click the microphone icon or the main astronaut orb to test the full-screen voice UI and TTS streaming!
