# AI Orchestrator Web UI

Modern Vue 3 + Nuxt web interface for the AI Orchestrator with real-time updates and Monaco code editor.

## Features

- ✅ **Real-time Updates** - WebSocket-based live task execution updates
- ✅ **Monaco Editor** - Full-featured code editor with syntax highlighting
- ✅ **Multiple Workflows** - Choose from default, quick, thorough, review-only, and document workflows
- ✅ **File Management** - View and download generated files
- ✅ **Iteration Tracking** - See detailed progress of each AI agent step
- ✅ **Responsive Design** - Built with Tailwind CSS

## Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  Vue 3 Frontend │◄────────┤  Flask Backend   │
│  (Port 3000)    │   API   │   (Port 5000)    │
│                 │◄────────┤                  │
│ - Pinia Store   │ Socket  │  - REST API      │
│ - Monaco Editor │   IO    │  - WebSocket     │
│ - Tailwind CSS  │         │  - Orchestrator  │
└─────────────────┘         └──────────────────┘
```

## Setup Instructions

### 1. Backend Setup

```bash
# Navigate to the ui directory
cd ui

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start the backend server
python app.py
```

The backend will run on `http://localhost:5000`

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd ui/frontend

# Install Node dependencies
npm install

# Start the development server
npm run dev
```

The frontend will run on `http://localhost:3000`

### 3. Open the UI

Open your browser and navigate to:
```
http://localhost:3000
```

## Usage

### Running a Task

1. **Enter Task Description** - Describe what you want the AI to build
2. **Select Workflow**:
   - **Default**: Codex implements → Gemini reviews → Claude refines
   - **Quick**: Codex implements only (fastest)
   - **Thorough**: Multiple review cycles
   - **Review Only**: For existing code
   - **Document**: Generate documentation
3. **Set Max Iterations** - How many refinement cycles (1-10)
4. **Click Execute** - Watch real-time progress

### Viewing Generated Code

1. Generated files appear in the **"Generated Files"** section
2. Click any file to open it in the **Monaco Editor**
3. **Download** files directly from the editor
4. View full output in the **"Output"** tab
5. Track agent progress in the **"Iterations"** tab

## Tech Stack

### Frontend
- **Vue 3** - Progressive JavaScript framework
- **Pinia** - State management
- **Monaco Editor** - VS Code editor component
- **Socket.IO Client** - Real-time WebSocket communication
- **Axios** - HTTP client
- **Tailwind CSS** - Utility-first CSS framework
- **Vite** - Build tool and dev server

### Backend
- **Flask** - Python web framework
- **Flask-SocketIO** - WebSocket support
- **Flask-CORS** - Cross-origin resource sharing
- **Eventlet** - Async networking library

## Development

### Frontend Development

```bash
cd ui/frontend

# Run dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

The backend automatically reloads when you make changes (Flask debug mode).

## API Endpoints

### REST API

- `GET /api/agents` - List available AI agents
- `GET /api/workflows` - List available workflows
- `POST /api/execute` - Execute a task
- `GET /api/status` - Get current session status
- `GET /api/files/<filename>` - Get file content

### WebSocket Events

**Client → Server:**
- `connect` - Client connection

**Server → Client:**
- `connected` - Connection established
- `task_started` - Task execution started
- `task_completed` - Task execution completed
- `task_error` - Task execution error

## Project Structure

```
ui/
├── app.py                 # Flask backend server
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── frontend/
    ├── src/
    │   ├── App.vue           # Main application component
    │   ├── main.js           # Application entry point
    │   ├── style.css         # Global styles
    │   ├── components/       # Vue components
    │   │   ├── Sidebar.vue
    │   │   ├── MainContent.vue
    │   │   ├── MonacoEditor.vue
    │   │   └── StatusBadge.vue
    │   └── stores/
    │       └── orchestrator.js  # Pinia store
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── tailwind.config.js
```

## Troubleshooting

### Backend won't start
- Ensure Python virtual environment is activated
- Check if port 5000 is available
- Verify all dependencies are installed: `pip install -r requirements.txt`

### Frontend won't start
- Check if port 3000 is available
- Ensure Node.js v18+ is installed
- Delete `node_modules` and run `npm install` again

### WebSocket connection fails
- Ensure backend is running on port 5000
- Check browser console for CORS errors
- Verify firewall settings

### Monaco Editor not loading
- Check browser console for errors
- Clear browser cache
- Ensure internet connection (CDN required)

## Tips

1. **Quick Testing**: Use the "Quick" workflow for fast iterations
2. **Full Review**: Use "Default" or "Thorough" for production code
3. **File Downloads**: Download files before clearing the session
4. **Multiple Tasks**: Clear previous results before starting a new task

## Contributing

Contributions are welcome! Please ensure:
- Code follows Vue 3 Composition API patterns
- Components are properly typed
- Tailwind CSS classes are used for styling
- Backend API changes are documented

## License

Same as the main AI Orchestrator project.
