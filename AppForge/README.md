# AppForge

Build apps with AI — no code required. Desktop (Windows EXE) and mobile (Android APK) ready.

## Features

- **AI-powered app creation**: Describe your idea in plain language; AI designs and generates a web app.
- **Wizard flow**: Input → Proposal → Building → Complete with preview, code editor, and AI chat.
- **Responsive UI**: Works on desktop and phone (DM Sans + Outfit, brand/accent colors).
- **Publishable**: Build as Windows EXE (Electron) or Android APK (Capacitor).

## Quick start (web)

1. Install dependencies:
   ```bash
   cd AppForge
   npm install
   cd server && npm install && cd ..
   ```

2. Start backend and frontend:
   ```bash
   npm run dev:all
   ```
   Backend: http://localhost:3001  
   Frontend: http://localhost:5173

3. Open http://localhost:5173, click "New App", describe your app, and build.

## Build Windows EXE

1. Install dependencies (including Electron):
   ```bash
   npm install
   cd server && npm install && cd ..
   ```

2. Build frontend and pack with Electron:
   ```bash
   set VITE_API_URL=http://localhost:3001/api
   npm run electron:build
   ```
   Output: `dist-electron/` — installer and portable EXE. Run the server (e.g. `node server/index.js`) on the same machine so the app can call the API at localhost:3001.

3. Run in dev mode (no pack):
   ```bash
   npm run build
   npm run server
   npm run electron:dev
   ```
   (Or run backend separately and point Electron to localhost:5173 in dev.)

## Build Android APK

1. Install Capacitor:
   ```bash
   npm install @capacitor/core @capacitor/cli
   npx cap init
   npx cap add android
   ```

2. Build web app and sync:
   ```bash
   npm run build
   npx cap sync android
   npx cap open android
   ```

3. In Android Studio: Build → Build Bundle(s) / APK(s) → Build APK(s).  
   Or use CLI: `cd android && ./gradlew assembleDebug`

4. **Backend for APK**: The app talks to your API. Options:
   - Deploy the `server/` to a host (e.g. Railway, Render) and set the API URL in app Settings.
   - Use the same machine on the same network and set API URL to `http://YOUR_IP:3001`.

## Environment (server)

Create `server/.env`:

- `OPENAI_API_KEY` or `CEREBRAS_API_KEY` — for AI chat and future code generation.
- `OPENAI_BASE_URL` — optional (e.g. `https://api.cerebras.ai/v1`).
- `PORT` — default 3001.

## Tech stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Zustand, React Router.
- **Backend**: Node.js, Express, fs-extra, OpenAI-compatible API (optional).
- **Desktop**: Electron.
- **Mobile**: Capacitor (same web app).

## License

MIT.
