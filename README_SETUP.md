# Knowledge Graph Chatbot - Setup Guide

## Prerequisites

- Python 3.12+
- Node.js 18+
- API Keys:
  - Gemini API key (Google AI Studio)
  - Pinecone API key
  - Tavily API key

## Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
# or if using uv
uv pip install -r requirements.txt
```

2. Create `.env` file in project root:
```
GEMINI_API_KEY=your_gemini_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
PINECONE_INDEX=knowledge-graph
TAVILY_API_KEY=your_tavily_api_key
```

3. Create Pinecone index:
   - Go to Pinecone console
   - Create index named `knowledge-graph`
   - Dimension: 768 (for Gemini embeddings)
   - Metric: cosine

4. Start Motia backend:
```bash
npm run dev
# or
motia dev
```

Backend will run on `http://localhost:3000`

## Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:3000
```

4. Start Next.js dev server:
```bash
npm run dev
```

Frontend will run on `http://localhost:3001` (or next available port)

## Usage

1. Open the frontend in your browser
2. Type a question in the chat interface
3. The system will:
   - Generate an answer using Gemini
   - Extract key concepts
   - Search for related articles using Tavily
   - Cluster concepts by similarity
   - Visualize as an interactive graph
4. Click on any node to see:
   - Detailed description
   - Source references with links
   - Related concepts
   - Option to expand and find more

## Project Structure

```
hack/
├── src/                    # Motia backend
│   ├── api/               # API endpoints
│   ├── services/          # Business logic
│   └── utils/             # Utilities
├── frontend/              # Next.js frontend
│   └── src/
│       ├── app/           # Next.js app router
│       ├── components/    # React components
│       ├── contexts/      # React contexts
│       └── services/      # API client
└── motia.config.ts        # Motia configuration
```

## Troubleshooting

- **Import errors**: Make sure all Python packages are installed
- **API errors**: Check that all API keys are set in `.env`
- **Graph not rendering**: Check browser console for errors
- **CORS errors**: Ensure backend is running and accessible

