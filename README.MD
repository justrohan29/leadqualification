# Lead Qualification AI Agent

This is a simple Streamlit app that helps you qualify leads from a CSV file using an AI model. It reads each lead's message, decides if it's worth following up, and suggests a short reply if needed.

---

## Features

- Upload a CSV file with Name, Email, and Message
- For each lead, the AI:
  - Labels it as High, Medium, or Low quality
  - Suggests what to do: Send reply, Ignore, or Escalate
  - Writes a short reply (only if needed)
- Filter leads by quality
- Download the processed results
- No database needed — works entirely in memory

---

## Tech Stack

- Python  
- Streamlit  
- OpenRouter (Mistral-7B model)  
- Pandas  
- Requests
