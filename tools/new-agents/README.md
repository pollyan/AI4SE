<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/c97c85d2-02c7-4b2b-8f75-10e132d588f4

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Copy `.env.example` to `.env.local` and configure your LLM provider:
   - `LLM_API_KEY`: Your API key
   - `LLM_BASE_URL`: API endpoint (e.g. `https://api.deepseek.com/v1`)
   - `LLM_MODEL`: Model name (e.g. `deepseek-chat`, `gpt-4o`)
3. Run the app:
   `npm run dev`
