import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import { GoogleGenAI } from '@google/genai';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public')); // Serve the widget from public folder

// Initialize Gemini API
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

app.post('/chat', async (req, res) => {
    try {
        const { message, history } = req.body;

        if (!message) {
            return res.status(400).json({ error: 'Message is required' });
        }

        // Read the knowledge base on every request so edits are reflected immediately
        // without needing to restart the server
        const knowledgeBasePath = path.join(__dirname, 'knowledge.md');
        const systemInstructionContent = fs.readFileSync(knowledgeBasePath, 'utf8');

        // Format history for Gemini API
        // Gemini multi-turn format: { role: 'user' | 'model', parts: [{ text: '...' }] }
        const formattedHistory = [];
        if (history && Array.isArray(history)) {
            for (const msg of history) {
                formattedHistory.push({
                    role: msg.role === 'user' ? 'user' : 'model',
                    parts: [{ text: msg.content }]
                });
            }
        }

        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: [
                ...formattedHistory,
                { role: 'user', parts: [{ text: message }] }
            ],
            config: {
                systemInstruction: systemInstructionContent,
                temperature: 0.2, // Keep interpretations grounded
            }
        });

        res.json({ reply: response.text });
    } catch (error) {
        console.error('Error generating chat response:', error);
        res.status(500).json({ error: 'Failed to generate response', details: error.message });
    }
});

app.listen(port, () => {
    console.log(`Chatbot server running at http://localhost:${port}`);
});
