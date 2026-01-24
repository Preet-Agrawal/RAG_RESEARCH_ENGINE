# Web Interface - Quick Start Guide

Beautiful Claude-style web interface for your RAG Research Engine!

## Screenshots Preview

The interface features:
- 🎨 **Dark theme** with black background (#1C1C1E)
- 🟤 **Copper accents** (#CD7F32) like Claude
- 📄 **Drag & drop** PDF upload
- 💬 **Chat interface** for questions
- ⚡ **Real-time** responses

## Quick Setup (3 Steps)

### 1. Run Setup Script

```bash
./setup_web.sh
```

This will:
- Install Python dependencies (PyPDF2)
- Install Node.js dependencies
- Create necessary directories
- Check your .env configuration

### 2. Add Groq API Key

Edit `.env` and make sure you have:

```bash
GROQ_API_KEY=gsk_your_actual_key_here
```

### 3. Start the Server

```bash
cd web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## How It Works

### Architecture

```
┌─────────────┐
│   Browser   │
│  (React/TS) │
└──────┬──────┘
       │
       │ HTTP/API
       │
┌──────▼──────┐      ┌─────────────┐
│  Next.js    │─────▶│   Python    │
│  API Routes │      │ process_pdf │
└──────┬──────┘      └──────┬──────┘
       │                    │
       │                    │
┌──────▼──────┐      ┌──────▼──────┐
│   Upload    │      │    Groq     │
│  Directory  │      │  API (FREE) │
└─────────────┘      └─────────────┘
```

### Flow

1. **Upload PDF** → Saved to `data/uploads/`
2. **Ask Question** → Sent to `/api/ask`
3. **Python Process** → Extracts text from PDF
4. **Groq LLM** → Answers question
5. **Response** → Displayed in chat

## Features

### PDF Upload
- Drag and drop interface
- Automatic validation (PDF only)
- File size display
- Remove and replace documents

### Chat Interface
- Claude-style message bubbles
- Real-time typing indicator
- Smooth scrolling
- Timestamp on messages
- Enter to send, Shift+Enter for new line

### Styling
- Professional dark theme
- Smooth animations
- Responsive design
- Custom scrollbars
- Hover effects

## API Endpoints

### POST /api/upload
Upload a PDF file

**Request:**
```javascript
const formData = new FormData();
formData.append('file', pdfFile);
fetch('/api/upload', {
  method: 'POST',
  body: formData
});
```

**Response:**
```json
{
  "success": true,
  "filename": "1234567890_document.pdf",
  "size": 12345
}
```

### POST /api/ask
Ask a question about the PDF

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
  "confidence": 0.85
}
```

## Development

### File Structure

```
web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload/route.ts   # Upload endpoint
│   │   │   └── ask/route.ts      # Question endpoint
│   │   ├── layout.tsx            # App layout
│   │   ├── page.tsx              # Main page
│   │   └── globals.css           # Global styles
│   ├── components/
│   │   ├── PDFUploader.tsx       # Upload UI
│   │   └── ChatInterface.tsx     # Chat UI
│   └── types/
│       └── index.ts              # TypeScript types
├── package.json
├── tsconfig.json
└── tailwind.config.ts
```

### Commands

```bash
# Development
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Customization

### Colors

Edit `tailwind.config.ts`:

```typescript
colors: {
  claude: {
    bg: '#1C1C1E',              // Background
    surface: '#2C2C2E',         // Cards
    border: '#3A3A3C',          // Borders
    text: '#F5F5F7',            // Text
    'text-secondary': '#A8A8AC', // Secondary text
    accent: '#CD7F32',          // Accent
    'accent-hover': '#E09A52',  // Hover
  },
}
```

### Layout

Edit `src/app/page.tsx` to modify:
- Header content
- Upload area
- Chat layout
- Footer

### Styling

Edit `src/app/globals.css` for:
- Global styles
- Scrollbar appearance
- Custom utilities

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
npm run dev -- -p 3001
```

### PDF Upload Fails

```bash
# Check directory exists
mkdir -p data/uploads

# Check permissions
chmod 755 data/uploads
```

### Python Script Errors

```bash
# Test Python script manually
python3 process_pdf.py data/uploads/test.pdf "What is this about?"

# Check dependencies
pip3 install PyPDF2
```

### Groq API Errors

```bash
# Verify API key
cat .env | grep GROQ_API_KEY

# Test API key
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GROQ_API_KEY'))"
```

## Production Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd web
vercel
```

### Environment Variables

Set these in production:
- `GROQ_API_KEY` - Your Groq API key

### Build

```bash
cd web
npm run build
npm start
```

## Tips

1. **Test with small PDFs first** - Faster processing
2. **Stay within Groq limits** - 6000 tokens/minute on free tier
3. **Clear uploads periodically** - Remove old PDFs from `data/uploads/`
4. **Check console logs** - Browser and terminal for debugging

## Next Steps

1. ✅ Upload a test PDF
2. ✅ Ask questions about it
3. ✅ See "Lost in the Middle" in action
4. ✅ Customize the design
5. ✅ Deploy to production

## Support

- **Web Issues**: Check `web/README.md`
- **RAG Issues**: Check main `README.md`
- **Groq API**: https://console.groq.com/docs

---

**Enjoy your beautiful Claude-style RAG interface! 🎨**
