import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';
import { spawn } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, '.env') });
const app = express();

process.on('unhandledRejection', (err) => {
  console.error('Unhandled Promise Rejection:', err);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
});
const PORT = process.env.PORT || 3001;
const PROJECTS_DIR = path.resolve(__dirname, '../projects');
const LIVING_ENTITY_PATH = path.resolve(__dirname, '../../');  // D:\Code\PCControllerHuman
let openaiClient = null;

const runtimeAiConfig = () => {
  const apiKey = process.env.OPENAI_API_KEY || process.env.CEREBRAS_API_KEY || '';
  let baseURL = process.env.OPENAI_BASE_URL || '';
  if (!baseURL && process.env.CEREBRAS_API_KEY) {
    baseURL = 'https://api.cerebras.ai/v1';
  }
  if (!baseURL) {
    baseURL = 'https://api.openai.com/v1';
  }
  return { apiKey, baseURL };
};

const resolvePythonExe = () => {
  const venvPython = path.join(process.cwd(), '.venv', 'Scripts', 'python.exe');
  if (process.env.PYTHON && fs.pathExistsSync(process.env.PYTHON)) {
    return process.env.PYTHON;
  }
  if (fs.pathExistsSync(venvPython)) {
    return venvPython;
  }
  return 'python';
};

const detectProvider = (baseURL, apiKey) => {
  if (!apiKey) return 'None';
  if ((baseURL || '').includes('cerebras')) return 'Cerebras';
  return 'OpenAI';
};

const extractJson = (raw) => {
  if (!raw) return null;
  const cleaned = raw.replace(/```json|```/g, '').trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    return null;
  }
};

app.use(cors());
app.use(bodyParser.json());
fs.ensureDirSync(PROJECTS_DIR);

// Projects CRUD
app.get('/api/projects', async (req, res) => {
  try {
    await fs.ensureDir(PROJECTS_DIR);
    const items = await fs.readdir(PROJECTS_DIR, { withFileTypes: true });
    const projects = await Promise.all(
      items.filter((d) => d.isDirectory()).map(async (dir) => {
        const pkgPath = path.join(PROJECTS_DIR, dir.name, 'package.json');
        let meta = { description: 'Generated project', type: 'web' };
        if (await fs.pathExists(pkgPath)) {
          try {
            const pkg = await fs.readJson(pkgPath);
            meta = { ...meta, ...(pkg.appforgeMetadata || {}) };
          } catch (_) {}
        }
        return {
          id: dir.name,
          name: dir.name,
          description: meta.description || 'No description',
          type: meta.type || 'web',
          status: 'Ready',
          lastEdited: 'Just now',
          deliverables: meta.deliverables || [],
        };
      })
    );
    res.json(projects);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/projects', async (req, res) => {
  const { name, description, type, userRequest, useAgent } = req.body;
  const projectPath = path.join(PROJECTS_DIR, name);
  try {
    if (await fs.pathExists(projectPath)) return res.status(400).json({ error: 'Project already exists' });
    await fs.ensureDir(projectPath);
    
    // Try to use LivingEntity AI Agent first (if enabled)
    if (useAgent !== false) {
      try {
        console.log('[AppForge] Using LivingEntity AI Agent...');
        const task = userRequest || description || `Create a web app called "${name}"`;
        const agentResult = await runAIAgent(task, projectPath);
        
        if (agentResult && agentResult.files_created && agentResult.files_created.length > 0) {
          console.log('[AppForge] AI Agent created files:', agentResult.files_created);
          
          // Build deliverables from created files
          const deliverables = [
            { type: 'htmlpreview', label: 'Preview', url: '/project-preview/' + encodeURIComponent(name) + '/index.html' },
          ];
          
          for (const file of agentResult.files_created) {
            if (file.endsWith('.html') || file.endsWith('.jsx') || file.endsWith('.js') || file.endsWith('.css') || file.endsWith('.json') || file.endsWith('.py')) {
              deliverables.push({ type: 'code', label: path.basename(file), file });
            }
          }
          
          // Save metadata
          const packageJson = {
            name: name.toLowerCase().replace(/\s+/g, '-'),
            version: '0.1.0',
            private: true,
            appforgeMetadata: { 
              description: description || agentResult.summary || 'AI Generated', 
              type: type || 'web', 
              deliverables,
              aiAgent: true,
              filesCreated: agentResult.files_created
            },
          };
          await fs.writeJson(path.join(projectPath, 'package.json'), packageJson, { spaces: 2 });
          
          return res.json({ success: true, path: projectPath, deliverables, aiAgent: true });
        }
      } catch (agentErr) {
        console.error('[AppForge] AI Agent failed, falling back to simple generation:', agentErr.message);
      }
    }
    
    // Fallback to simple generation
    const deliverables = [
      { type: 'htmlpreview', label: 'Preview', url: '/project-preview/' + encodeURIComponent(name) + '/index.html' },
      { type: 'code', label: 'index.html', file: 'index.html' },
      { type: 'code', label: 'App.jsx', file: 'src/App.jsx' },
      { type: 'code', label: 'main.jsx', file: 'src/main.jsx' },
      { type: 'download', label: 'Package', file: 'package.json' },
    ];
    const packageJson = {
      name: name.toLowerCase().replace(/\s+/g, '-'),
      version: '0.1.0',
      private: true,
      appforgeMetadata: { description, type, deliverables },
      scripts: { dev: 'vite', build: 'vite build' },
      dependencies: { react: '^18.2.0', 'react-dom': '^18.2.0' },
    };
    let indexHtml = `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/><title>${name}</title>
<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:system-ui,sans-serif;min-height:100vh;background:linear-gradient(135deg,#0ea5e9 0%,#d946ef 100%);display:flex;align-items:center;justify-content:center;padding:2rem;}
.card{background:white;padding:3rem;border-radius:1.5rem;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25);max-width:500px;text-align:center;}
h1{font-size:2rem;color:#0f172a;margin-bottom:1rem;}p{color:#64748b;line-height:1.6;}.badge{display:inline-block;background:linear-gradient(135deg,#0ea5e9,#d946ef);color:white;padding:0.5rem 1rem;border-radius:2rem;font-size:0.85rem;font-weight:600;}</style>
</head>
<body><div class="card"><h1>${name}</h1><p>${description || 'Generated by AppForge'}</p><span class="badge">AppForge</span></div></body>
</html>`;
    let appJsx = `import React from 'react';\nexport default function App() {\n  return (\n    <div style={{ fontFamily: 'sans-serif', padding: '2rem' }}>\n      <h1>${name}</h1>\n      <p>${description || 'Generated by AppForge'}</p>\n    </div>\n  );\n}`;
    let mainJsx = `import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);`;

    const aiResult = await generateProjectWithAI({ name, description, userRequest });
    if (aiResult) {
      indexHtml = aiResult.indexHtml;
      appJsx = aiResult.appJsx;
      mainJsx = aiResult.mainJsx;
    }
    await fs.writeJson(path.join(projectPath, 'package.json'), packageJson, { spaces: 2 });
    await fs.writeFile(path.join(projectPath, 'index.html'), indexHtml);
    await fs.ensureDir(path.join(projectPath, 'src'));
    await fs.writeFile(path.join(projectPath, 'src', 'App.jsx'), appJsx);
    await fs.writeFile(path.join(projectPath, 'src', 'main.jsx'), mainJsx);
    res.json({ success: true, path: projectPath, deliverables });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/files', async (req, res) => {
  const { project, file } = req.query;
  if (!project || !file) return res.status(400).json({ error: 'Missing params' });
  const filePath = path.join(PROJECTS_DIR, project, file);
  if (!path.resolve(filePath).startsWith(path.resolve(PROJECTS_DIR))) return res.status(403).json({ error: 'Access denied' });
  try {
    if (await fs.pathExists(filePath)) {
      const content = await fs.readFile(filePath, 'utf-8');
      res.json({ content });
    } else res.status(404).json({ error: 'File not found' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/files', async (req, res) => {
  const { project, file, content } = req.body;
  if (!project || !file || content === undefined) return res.status(400).json({ error: 'Missing params' });
  const filePath = path.join(PROJECTS_DIR, project, file);
  if (!path.resolve(filePath).startsWith(path.resolve(PROJECTS_DIR))) return res.status(403).json({ error: 'Access denied' });
  try {
    await fs.ensureDir(path.dirname(filePath));
    await fs.writeFile(filePath, content);
    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.use('/project-preview', express.static(PROJECTS_DIR));

app.get('/api/download', async (req, res) => {
  const { project, file } = req.query;
  if (!project || !file) return res.status(400).send('Missing params');
  const filePath = path.join(PROJECTS_DIR, project, file);
  if (!path.resolve(filePath).startsWith(path.resolve(PROJECTS_DIR))) return res.status(403).send('Access denied');
  try {
    if (await fs.pathExists(filePath)) res.download(filePath);
    else res.status(404).send('Not found');
  } catch (e) {
    res.status(500).send(e.message);
  }
});

app.delete('/api/projects/:name', async (req, res) => {
  const projectPath = path.join(PROJECTS_DIR, req.params.name);
  if (!path.resolve(projectPath).startsWith(path.resolve(PROJECTS_DIR))) return res.status(403).json({ error: 'Access denied' });
  try {
    if (await fs.pathExists(projectPath)) {
      await fs.remove(projectPath);
      res.json({ success: true });
    } else res.status(404).json({ error: 'Project not found' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// AI: optional OpenAI-compatible endpoint with runtime config
async function getOpenAI() {
  const { apiKey, baseURL } = runtimeAiConfig();
  if (!apiKey) return null;
  if (!openaiClient) {
    const OpenAI = (await import('openai')).default;
    openaiClient = new OpenAI({
      apiKey,
      baseURL,
    });
  }
  return openaiClient;
}

// Run LivingEntity AI Agent to create project
async function runAIAgent(task, projectPath) {
  const { apiKey, baseURL } = runtimeAiConfig();
  if (!apiKey) return null;

  const agentScript = path.resolve(__dirname, 'ai_agent.py');
  const model = process.env.OPENAI_MODEL || 'llama-3.3-70b';

  return new Promise((resolve, reject) => {
    const args = [agentScript, task, projectPath, apiKey];
    if (baseURL) args.push(baseURL);
    args.push(model);

    console.log('[AI Agent] Starting...', { task: task.slice(0, 100), projectPath });

    const pythonExe = resolvePythonExe();
    const proc = spawn(pythonExe, ['-u', ...args], {
      cwd: LIVING_ENTITY_PATH,
      env: { ...process.env, PYTHONPATH: LIVING_ENTITY_PATH, PYTHONIOENCODING: 'utf-8' },
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      const text = data.toString();
      stdout += text;
      console.log('[AI Agent]', text.trim());
    });

    proc.stderr.on('data', (data) => {
      const text = data.toString();
      stderr += text;
      if (!text.includes('DeprecationWarning') && !text.includes('UserWarning')) {
        console.error('[AI Agent Error]', text.trim());
      }
    });

    proc.on('close', (code) => {
      console.log('[AI Agent] Finished with code:', code);
      if (code === 0) {
        // Parse result from stdout
        const resultMatch = stdout.match(/=== RESULT ===\s*([\s\S]+)$/);
        if (resultMatch) {
          try {
            const result = JSON.parse(resultMatch[1].trim());
            resolve(result);
          } catch (e) {
            resolve({ files_created: [], output: stdout.split('\n'), complete: true });
          }
        } else {
          resolve({ files_created: [], output: stdout.split('\n'), complete: true });
        }
      } else {
        reject(new Error(`AI Agent failed: ${stderr || 'Unknown error'}`));
      }
    });

    proc.on('error', (err) => {
      reject(new Error(`Failed to start AI Agent: ${err.message}`));
    });

    // Timeout after 3 minutes
    setTimeout(() => {
      proc.kill('SIGTERM');
      reject(new Error('AI Agent timed out'));
    }, 180000);
  });
}

async function generateProjectWithAI({ name, description, userRequest }) {
  const client = await getOpenAI();
  if (!client) return null;
  const prompt = `You are AppForge AI - an automated coding agent.

YOUR CAPABILITIES:
- Create, edit, and delete any files and folders
- Generate code in ANY language (JS, TS, Python, C#, Swift, Kotlin, C++, etc.)
- Create ANY type of application (web, mobile, games, desktop, CLI, API)
- Run terminal commands

YOUR LIMITATIONS:
- You CANNOT see the screen or visual output
- You CANNOT interact with GUI or click buttons
- You work ONLY through text: files and terminal commands
- You cannot verify visual appearance - you work blindly

USER REQUEST: ${userRequest || description || 'Build a modern web app.'}
APP NAME: ${name}

For this AppForge platform, generate a WEB-BASED preview that demonstrates the concept.
Even if the user asked for Unity/mobile/desktop - create a web preview that shows the idea.

Return JSON with keys:
- "indexHtml": a complete static HTML page with inline CSS showing a preview/mockup of the app concept.
- "appJsx": a React component (App.jsx) that demonstrates the core functionality.
- "mainJsx": a React entry file (main.jsx) that renders App.

Rules:
- Output JSON only, no markdown.
- The indexHtml must be self-contained (no external scripts).
- Make it functional and visually represent what the user asked for.
- If it's a game concept, show game UI/mechanics in the web preview.`;

  const completion = await client.chat.completions.create({
    model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
    messages: [
      { role: 'system', content: 'You are a senior frontend engineer. Output strict JSON only. Always create web-based alternatives for non-web requests.' },
      { role: 'user', content: prompt },
    ],
    max_tokens: 2000,
    temperature: 0.7,
  });

  const raw = completion.choices[0]?.message?.content || '';
  const parsed = extractJson(raw);
  if (!parsed || !parsed.indexHtml || !parsed.appJsx || !parsed.mainJsx) return null;
  return {
    indexHtml: String(parsed.indexHtml),
    appJsx: String(parsed.appJsx),
    mainJsx: String(parsed.mainJsx),
  };
}

app.post('/api/ai/chat', async (req, res) => {
  const { message, context } = req.body;
  if (!message) return res.status(400).json({ error: 'Message required' });
  const client = await getOpenAI();
  if (!client) {
    return res.json({
      response: 'AI key not configured yet. Save an OpenAI or Cerebras key in Settings to chat.',
      blocked: false,
    });
  }
  try {
    const completion = await client.chat.completions.create({
      model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
      messages: [
        { role: 'system', content: (context || '') + '\nYou are a helpful coding assistant. Reply briefly.' },
        { role: 'user', content: message },
      ],
      max_tokens: 1024,
    });
    const text = completion.choices[0]?.message?.content || 'No response';
    res.json({ response: text, blocked: false });
  } catch (e) {
    res.status(500).json({ error: e.message, response: 'AI error: ' + e.message });
  }
});

app.get('/api/ai/status', async (req, res) => {
  const { apiKey, baseURL } = runtimeAiConfig();
  const configured = !!apiKey;
  res.json({
    configured,
    provider: detectProvider(baseURL, apiKey),
    capabilities: ['chat', 'create-project', 'ai-agent'],
    ready: configured,
    baseURL,
    agentEnabled: true,
  });
});

// SSE endpoint for real-time agent progress
app.get('/api/agent/stream/:name', async (req, res) => {
  const { name } = req.params;
  const task = req.query.task || `Create a web app called "${name}"`;
  const projectPath = path.join(PROJECTS_DIR, name);

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const sendEvent = (event, data) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    if (typeof res.flush === 'function') {
      res.flush();
    }
  };

  res.write(':ok\n\n');
  if (typeof res.flush === 'function') {
    res.flush();
  }

  try {
    await fs.ensureDir(projectPath);
    sendEvent('status', { message: 'Starting AI Agent...', phase: 'init' });

    const { apiKey, baseURL } = runtimeAiConfig();
    if (!apiKey) {
      sendEvent('agent_error', { message: 'API key not configured' });
      res.end();
      return;
    }

    const agentScript = path.resolve(__dirname, 'ai_agent.py');
    const agentExists = fs.pathExistsSync(agentScript);
    const model = process.env.OPENAI_MODEL || 'llama-3.3-70b';

    const pythonExe = resolvePythonExe();
    const pythonExists = pythonExe !== 'python' ? fs.pathExistsSync(pythonExe) : true;
    const args = [pythonExe, '-u', agentScript, task, projectPath, apiKey];
    if (baseURL) args.push(baseURL);
    args.push(model);

    sendEvent('status', { message: 'AI Agent thinking...', phase: 'thinking' });
    sendEvent('log', { message: `Agent script: ${agentScript} (${agentExists ? 'found' : 'missing'})` });
    sendEvent('log', { message: `Python: ${pythonExe} (${pythonExists ? 'ok' : 'missing'})` });

    let stderrBuffer = '';
    const proc = spawn(args[0], args.slice(1), {
      cwd: LIVING_ENTITY_PATH,
      env: { ...process.env, PYTHONPATH: LIVING_ENTITY_PATH, PYTHONIOENCODING: 'utf-8' },
    });

    proc.on('error', (err) => {
      sendEvent('agent_error', { message: `Failed to start AI Agent: ${err.message}` });
      res.end();
    });

    proc.on('error', (err) => {
      sendEvent('error', { message: `AI Agent failed to start: ${err.message}` });
      res.end();
    });

    proc.stdout.on('data', (data) => {
      const text = data.toString().trim();
      if (text.startsWith('[AI]:')) {
        sendEvent('output', { message: text.replace('[AI]: ', '') });
      } else if (text.includes('Created:')) {
        const file = text.match(/Created:\s*(.+)/)?.[1];
        if (file) sendEvent('file', { file, action: 'created' });
      } else if (text && !text.includes('=== RESULT ===')) {
        sendEvent('log', { message: text });
      }
    });

    proc.stderr.on('data', (data) => {
      const text = data.toString().trim();
      if (text.length > 0) {
        stderrBuffer += text + '\n';
        if (!text.includes('Warning')) {
          sendEvent('log', { message: text, type: 'error' });
        }
      }
    });

    proc.on('close', async (code) => {
      if (code === 0) {
        // Read created files
        const files = await fs.readdir(projectPath);
        const deliverables = [
          { type: 'htmlpreview', label: 'Preview', url: '/project-preview/' + encodeURIComponent(name) + '/index.html' },
        ];
        
        const addFiles = async (dir, prefix = '') => {
          const items = await fs.readdir(path.join(projectPath, dir), { withFileTypes: true });
          for (const item of items) {
            const relPath = prefix ? `${prefix}/${item.name}` : item.name;
            if (item.isDirectory() && item.name !== '.ai_memory' && item.name !== 'node_modules') {
              await addFiles(path.join(dir, item.name), relPath);
            } else if (item.isFile()) {
              const ext = path.extname(item.name);
              if (['.html', '.jsx', '.js', '.css', '.json', '.py', '.ts', '.tsx'].includes(ext)) {
                deliverables.push({ type: 'code', label: item.name, file: relPath });
              }
            }
          }
        };
        await addFiles('.');
        
        // Save metadata
        const pkgPath = path.join(projectPath, 'package.json');
        let pkg = { name: name.toLowerCase().replace(/\s+/g, '-'), version: '0.1.0' };
        if (await fs.pathExists(pkgPath)) {
          try { pkg = await fs.readJson(pkgPath); } catch {}
        }
        pkg.appforgeMetadata = { description: task, type: 'web', deliverables, aiAgent: true };
        await fs.writeJson(pkgPath, pkg, { spaces: 2 });

        sendEvent('complete', { deliverables, success: true });
      } else {
        sendEvent('agent_error', {
          message: `AI Agent failed (code ${code ?? 'unknown'})`,
          details: stderrBuffer.trim().slice(-2000)
        });
      }
      res.end();
    });

    // Timeout
    setTimeout(() => {
      proc.kill('SIGTERM');
      sendEvent('agent_error', { message: 'AI Agent timed out' });
      res.end();
    }, 180000);

  } catch (err) {
    sendEvent('agent_error', { message: err.message });
    res.end();
  }
});

app.listen(PORT, () => {
  console.log('AppForge server at http://localhost:' + PORT);
  console.log('Projects:', PROJECTS_DIR);
  console.log('LivingEntity:', LIVING_ENTITY_PATH);
});
