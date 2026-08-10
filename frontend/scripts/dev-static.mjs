import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const fallbackDir = path.join(rootDir, "fallback");

const HOST = process.env.HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 5173);
const API_ORIGIN = process.env.API_ORIGIN || "http://127.0.0.1:8000";

const MIME_BY_EXT = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon"
};

async function sendFile(res, targetPath) {
  try {
    const fileStat = await stat(targetPath);
    if (!fileStat.isFile()) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }

    const ext = path.extname(targetPath).toLowerCase();
    const contentType = MIME_BY_EXT[ext] || "application/octet-stream";
    const body = await readFile(targetPath);
    res.writeHead(200, { "Content-Type": contentType, "Cache-Control": "no-store" });
    res.end(body);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("Not found");
  }
}

function buildProxyRequestHeaders(req) {
  const headers = { ...req.headers };
  delete headers.host;
  delete headers.connection;
  delete headers["content-length"];
  return headers;
}

async function readRequestBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(typeof chunk === "string" ? Buffer.from(chunk) : chunk);
  }
  if (chunks.length === 0) {
    return undefined;
  }
  return Buffer.concat(chunks);
}

async function proxyApiRequest(req, res) {
  const incomingUrl = new URL(req.url || "/", `http://${HOST}:${PORT}`);
  const targetUrl = new URL(incomingUrl.pathname + incomingUrl.search, API_ORIGIN);
  const body = req.method === "GET" || req.method === "HEAD" ? undefined : await readRequestBody(req);

  const options = {
    method: req.method,
    headers: buildProxyRequestHeaders(req),
    body
  };

  const proxyRequest = fetch(targetUrl, options);

  proxyRequest
    .then(async (proxyResponse) => {
      const headers = {};
      proxyResponse.headers.forEach((value, key) => {
        if (key.toLowerCase() !== "transfer-encoding") {
          headers[key] = value;
        }
      });

      const buffer = Buffer.from(await proxyResponse.arrayBuffer());
      res.writeHead(proxyResponse.status, headers);
      res.end(buffer);
    })
    .catch((error) => {
      res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ detail: `Proxy error: ${error.message}` }));
    });
}

const server = createServer((req, res) => {
  const requestUrl = new URL(req.url || "/", `http://${HOST}:${PORT}`);

  if (requestUrl.pathname.startsWith("/api/")) {
    void proxyApiRequest(req, res);
    return;
  }

  const normalizedPath = path.normalize(requestUrl.pathname).replace(/^([.][.][/\\])+/, "");
  const relativePath = normalizedPath.replace(/^[/\\]+/, "");
  const candidate = path.join(fallbackDir, relativePath || "index.html");

  if (normalizedPath === "/" || normalizedPath === "\\") {
    void sendFile(res, path.join(fallbackDir, "index.html"));
    return;
  }

  void stat(candidate)
    .then((fileStat) => {
      if (fileStat.isFile()) {
        return sendFile(res, candidate);
      }
      return sendFile(res, path.join(fallbackDir, "index.html"));
    })
    .catch(() => sendFile(res, path.join(fallbackDir, "index.html")));
});

server.listen(PORT, HOST, () => {
  console.log(`Static dev server running at http://${HOST}:${PORT}`);
  console.log(`Proxying /api requests to ${API_ORIGIN}`);
});
