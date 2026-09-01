import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

app.use(express.json());

// Proxy API requests if BACKEND_URL is set and fetch is available
if (BACKEND_URL) {
  app.use(['/api', '/health'], async (req, res) => {
    try {
      const targetUrl = `${BACKEND_URL.replace(/\/+$/, '')}${req.originalUrl}`;
      const headers = { ...req.headers };
      delete headers.host;

      const init = {
        method: req.method,
        headers,
      };

      if (['POST', 'PUT', 'PATCH'].includes(req.method) && req.body) {
        init.body = JSON.stringify(req.body);
      }

      const response = await fetch(targetUrl, init);
      const data = await response.text();

      response.headers.forEach((value, name) => {
        res.setHeader(name, value);
      });
      res.status(response.status).send(data);
    } catch (err) {
      console.error(`Proxy error for ${req.originalUrl}:`, err.message);
      res.status(502).json({ error: 'Backend gateway error', message: err.message });
    }
  });
}

// Serve production static assets
const distPath = path.join(__dirname, 'dist');
app.use(express.static(distPath));

// Fallback to index.html for Single Page Application routing
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Digital Twin Production Server running on http://0.0.0.0:${PORT}`);
  console.log(`Serving static files from: ${distPath}`);
  console.log(`Backend proxy target: ${BACKEND_URL}`);
});
