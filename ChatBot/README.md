# [modern dope] AI Chatbot - Deployment Guide

This guide explains how to package the [modern dope] "Floyd" Chatbot and deploy it to a live production server so it can be embedded into your WordPress website.

## Architecture Overview
The chatbot relies on two separate backend services running simultaneously:
1. **Node.js Server (Port 3000):** Handles chat logic, securely stores your `GEMINI_API_KEY`, manages the system prompt (from `knowledge.md`), and communicates with the Google Gemini API.
2. **Python TTS Server (Port 5001):** Runs the Kokoro ONNX Text-to-Speech AI model to instantly generate high-quality voice streams.

To deploy this securely and reliably, you should host these backends on a Virtual Private Server (VPS) like DigitalOcean, AWS EC2, or Hetzner, and use **Docker** to run them side-by-side.

---

## Step 1: Prepare for Production
Before deploying, you must update the `API_URL` endpoints in the frontend so they point to your future live server instead of `localhost`.

1. Open `public/widget.js`.
2. Locate the `API_URL` variable at the top and change it to your live Node.js domain (e.g., `https://api.moderndope.com/chat`).
3. Locate the `speakText` function and change the `fetch` URL from `http://localhost:5001/synthesize` to your live TTS domain (e.g., `https://tts.moderndope.com/synthesize`).

---

## Step 2: Deploy the Backends (Docker)
1. **Provision a Server:** Spin up an Ubuntu VPS with at least 2GB of RAM (Kokoro model requires some memory).
2. **Install Docker:** SSH into your server and install Docker and Docker Compose.
3. **Upload Files:** Clone or upload this repository to your server. 
4. **Create `.env`:** Ensure your `.env` file is present on the server with your `GEMINI_API_KEY`.
5. **Run Docker Compose:** (Assuming you create a `docker-compose.yml` that builds both the Node and Python environments).
   ```bash
   docker-compose up -d
   ```
6. **Set up a Reverse Proxy:** Use Nginx or Caddy to route internet traffic (HTTPS) to Port 3000 (Node) and Port 5001 (Python) on your server.

---

## Step 3: Embed in WordPress
Once your backend servers are actively running on the internet, you can easily embed the frontend interface into your WordPress site.

1. **Upload Static Files:**
   Upload the following files to your WordPress Media Library, or into your active child theme's directory via FTP:
   - `public/floyd_avatar.png`
   - `public/styles.css`
   - `public/widget.js`

2. **Inject the HTML:**
   You need to drop the chatbot HTML container immediately before the closing `</body>` tag of your WordPress site. You can do this by editing `footer.php` in your child theme, or by using a free plugin like "WPCode" (Insert Headers and Footers).

   Paste the following block, making sure to update the `href` and `src` paths to wherever you uploaded them in Step 1:

   ```html
   <!-- [modern dope] Styles -->
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
   <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
   <link rel="stylesheet" href="URL_TO_YOUR_UPLOADED/styles.css">

   <!-- Chat Widget Container -->
   <div id="md-chat-widget" class="md-chat-widget-closed">
       <button id="md-chat-toggle-btn" class="md-btn-pulse" aria-label="Toggle Chat">
           <img src="URL_TO_YOUR_UPLOADED/floyd_avatar.png" alt="Chat with Floyd" class="md-chat-toggle-avatar">
           <i class="fa-solid fa-times md-hidden"></i>
       </button>

       <!-- Chat Window -->
       <div id="md-chat-window" class="md-hidden">
           <div class="md-chat-header">
               <div class="md-chat-header-info">
                   <img src="URL_TO_YOUR_UPLOADED/floyd_avatar.png" alt="Floyd Avatar" class="md-chat-logo" onerror="this.style.display='none'">
                   <div>
                       <h3>Floyd</h3>
                       <p>Ask me anything about our services!</p>
                   </div>
               </div>
               <button id="md-chat-close-btn" class="md-header-btn"><i class="fa-solid fa-chevron-down"></i></button>
           </div>
           
           <!-- Messages Area -->
           <div id="md-chat-messages" class="md-chat-body">
               <div class="md-message md-message-bot">
                   <div class="md-message-content">
                       Hey there! 👋 I'm the [modern dope] AI assistant. How can I help you today?
                   </div>
               </div>
           </div>

           <!-- Input Area -->
           <div class="md-chat-footer">
               <form id="md-chat-form">
                   <button type="button" id="md-mic-btn" aria-label="Toggle Voice Control" title="Voice Chat">
                       <i class="fa-solid fa-microphone"></i>
                   </button>
                   <input type="text" id="md-chat-input" placeholder="Type your question..." autocomplete="off" required>
                   <button type="submit" id="md-chat-send-btn">
                       <i class="fa-solid fa-paper-plane"></i>
                   </button>
               </form>
           </div>
       </div>
   </div>

   <!-- FLOYD VOICE OVERLAY MODAL -->
   <div id="floyd-voice-overlay" class="md-hidden">
       <button id="floyd-close-btn" aria-label="Close Voice Chat">
           <i class="fa-solid fa-times"></i>
       </button>

       <div class="floyd-content">
           <h2 class="floyd-title">Floyd</h2>
           <p class="floyd-subtitle" id="floyd-status-text">Listening...</p>
           
           <div class="floyd-orb-container" id="floyd-orb-btn">
               <div class="floyd-orb" id="floyd-main-orb"></div>
               <div class="floyd-ring floyd-ring-1"></div>
               <div class="floyd-ring floyd-ring-2"></div>
               <i class="fa-solid fa-microphone floyd-mic-icon"></i>
           </div>
           
           <div class="floyd-transcript-container">
               <p id="floyd-transcript-text" class="floyd-transcript-text"></p>
           </div>
       </div>
   </div>

   <!-- Initialize Chat Logic -->
   <script src="URL_TO_YOUR_UPLOADED/widget.js"></script>
   ```
