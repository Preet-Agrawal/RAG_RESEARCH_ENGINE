#!/bin/bash
cd "$(dirname "$0")"
uvicorn src.api:app --reload --port 8000 &
cd server && node index.js &
cd client && npm run dev
