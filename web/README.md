# RAG Research Engine - Web Interface

A beautiful, Claude-inspired web interface for testing the "Lost in the Middle" phenomenon in RAG systems.

## Features

- 🎨 **Claude-Style Dark Theme** - Beautiful black background with copper accents
- 📄 **PDF Upload** - Drag and drop PDF documents
- 💬 **Chat Interface** - Ask questions about your PDF
- 🔬 **RAG Analysis** - Tests "Lost in the Middle" phenomenon
- ⚡ **Powered by Groq** - Fast, free API

## Tech Stack

- **Frontend**: Next.js 14, React, TypeScript
- **Styling**: Tailwind CSS
- **Backend**: Next.js API Routes
- **Processing**: Python + Groq API
- **PDF Parsing**: PyPDF2

## Setup

### 1. Install Python Dependencies

From the root directory:

```bash
pip install PyPDF2>=3.0.0
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

### 2. Install Node Dependencies

```bash
cd web
npm install
```

### 3. Configure Environment

Make sure your `.env` file in the root directory has your Groq API key:

```bash
GROQ_API_KEY=gsk_your_actual_key_here
```

### 4. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## How to Use

1. **Upload PDF**: Drag and drop a PDF file or click to select
2. **Ask Questions**: Type questions about your PDF in the chat
3. **Get Answers**: The system will analyze the PDF and answer using Groq's LLM
4. **Test RAG**: See how the "Lost in the Middle" phenomenon affects retrieval

## Project Structure

```
web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload/      # PDF upload endpoint
│   │   │   └── ask/         # Question answering endpoint
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Main page
│   ├── components/
│   │   ├── PDFUploader.tsx  # PDF upload component
│   │   └── ChatInterface.tsx # Chat UI component
│   ├── types/
│   │   └── index.ts         # TypeScript types
│   └── lib/                 # Utility functions
├── public/                  # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.js
```

## API Endpoints

### POST /api/upload

Upload a PDF file.

**Request:**
- `FormData` with `file` field (PDF file)

**Response:**
```json
{
  "success": true,
  "filename": "1234567890_document.pdf",
  "filepath": "/path/to/file",
  "size": 12345,
  "name": "document.pdf"
}
```

### POST /api/ask

Ask a question about the uploaded PDF.

**Request:**
```json
{
  "question": "What is this document about?",
  "filename": "1234567890_document.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "answer": "This document discusses...",
  "sources": ["PDF Document"],
  "confidence": 0.85,
  "positions": []
}
```

## Design Philosophy

The interface is inspired by Claude's clean, professional design:

- **Dark Theme**: Black background (#1C1C1E) with subtle grays
- **Copper Accents**: Warm copper (#CD7F32) for highlights
- **Smooth Interactions**: Subtle animations and transitions
- **Minimalist**: Focus on content, not chrome
- **Accessible**: High contrast, clear typography

## Color Palette

```typescript
claude: {
  bg: '#1C1C1E',              // Main background
  surface: '#2C2C2E',         // Cards, surfaces
  border: '#3A3A3C',          // Borders
  text: '#F5F5F7',            // Primary text
  'text-secondary': '#A8A8AC', // Secondary text
  accent: '#CD7F32',          // Copper accent
  'accent-hover': '#E09A52',  // Hover state
}
```

## Troubleshooting

### PDF Upload Fails
- Check that the file is a valid PDF
- Ensure the `data/uploads/` directory exists
- Check file permissions

### Questions Don't Get Answered
- Verify Groq API key is set in `.env`
- Check that `process_pdf.py` has execute permissions
- Look at browser console and terminal for errors

### Styling Issues
- Clear `.next` cache: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`
- Check Tailwind CSS is properly configured

## Production Deployment

### Build for Production

```bash
npm run build
npm start
```

### Environment Variables

Make sure these are set in production:
- `GROQ_API_KEY` - Your Groq API key

### Deployment Platforms

This Next.js app can be deployed to:
- **Vercel** (recommended)
- **Netlify**
- **AWS Amplify**
- **Docker**

## Contributing

This is part of the RAG Research Engine project. See the main [README.md](../README.md) for more information.

## License

Part of the RAG Research Engine project.

---

**Built with ❤️ using Next.js, TypeScript, and Groq**
