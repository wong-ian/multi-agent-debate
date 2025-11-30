import { GoogleGenerativeAI } from "@google/genai";
import type { Message } from '../types.js';
import { env } from '$env/dynamic/public';

const apiKey = env.VITE_GEMINI_API_KEY;

if (!apiKey) {
  throw new Error("VITE_GEMINI_API_KEY is not set in the environment.");
}

const genAI = new GoogleGenerativeAI(apiKey);

export const generateResponse = async (
  systemInstruction: string,
  history: Message[],
  prompt: string
): Promise<string> => {
  try {
    const model = genAI.getGenerativeModel({
      model: "gemini-1.5-flash",
      systemInstruction: systemInstruction,
    });

    const chat = model.startChat({
        history: history.map(msg => ({
            role: msg.agent === 'Judge' || msg.agent.startsWith('Debater_') ? 'model' : 'user',
            parts: [{ text: msg.content }]
        }))
    });

    const result = await chat.sendMessage(prompt);
    const response = await result.response;
    const text = response.text();
    return text;

  } catch (error) {
    console.error("Error generating response from Gemini API:", error);
    if (error instanceof Error) {
        return `An error occurred: ${error.message}. Please check your API key and network connection.`;
    }
    return "An unknown error occurred while contacting the AI."
  }
};