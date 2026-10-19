#!/usr/bin/env node
/**
 * Production static server for the Il-Malti app.
 *
 * Zero dependencies. Serves an explicit allowlist of files, so tools/,
 * tests/, .git/ and this script itself are never exposed over HTTP.
 *
 *   node server.js                 # 127.0.0.1:8080
 *   HOST=0.0.0.0 PORT=9000 node server.js
 *
 * Features: ETag / If-None-Match, Last-Modified / If-Modified-Since,
 * gzip, per-type Cache-Control, security headers, access log, graceful
 * shutdown (SIGTERM/SIGINT).
 */

"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const HOST = process.env.HOST || "127.0.0.1";
const PORT = Number(process.env.PORT || 8080);
const ROOT = __dirname;
const GZIP_MIN = 512;

const FILES = {
  "/index.html": { type: "text/html; charset=utf-8", cache: "no-cache" },
  "/styles.css": { type: "text/css; charset=utf-8", cache: "no-cache" },
  "/app.js": { type: "text/javascript; charset=utf-8", cache: "no-cache" },
  "/data/words.js": { type: "text/javascript; charset=utf-8", cache: "no-cache" },
  "/data/sentences.js": { type: "text/javascript; charset=utf-8", cache: "no-cache" },
  "/data/ipa.js": { type: "text/javascript; charset=utf-8", cache: "no-cache" },
  "/data/links.js": { type: "text/javascript; charset=utf-8", cache: "no-cache" },
  "/data/pairs.js": { type: "text/javascript; charset=utf-8", cache: "no-cache" },
};

const ALIASES = { "/": "/index.html" };

const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "connect-src 'self'",
  "form-action 'none'",
  "frame-ancestors 'none'",
  "base-uri 'none'",
].join("; ");

const SECURITY_HEADERS = {
  "Content-Security-Policy": CSP,
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "X-Frame-Options": "DENY",
};

function log(...args) {
  console.log(new Date().toISOString(), ...args);
}

function statFile(file) {
  return new Promise((resolve, reject) => {
    fs.stat(file, (err, st) => (err ? reject(err) : resolve(st)));
  });
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    fs.readFile(file, (err, buf) => (err ? reject(err) : resolve(buf)));
  });
}

function send(req, res, status, headers, body) {
  const merged = Object.assign({}, SECURITY_HEADERS, headers);
  res.writeHead(status, merged);
  if (req.method === "HEAD" || body == null) return res.end();
  res.end(body);
}

function accessLog(req, res, status, bytes, note) {
  const ip = req.socket.remoteAddress || "-";
  const enc = res.getHeader("Content-Encoding") || "-";
  log(
    `${ip} ${req.method} ${req.url} ${status} ${bytes}b ${enc}` +
      (note ? ` ${note}` : "")
  );
}

async function handle(req, res) {
  const started = process.hrtime.bigint();
  const url = new URL(req.url, "http://" + (req.headers.host || HOST));
  const pathname = decodeURIComponent(url.pathname);
  const target = ALIASES[pathname] || pathname;

  res.on("finish", () => {
    const ms = Number(process.hrtime.bigint() - started) / 1e6;
    if (process.env.ACCESS_LOG_MS === "1") {
      log(`  ↳ ${ms.toFixed(1)}ms`);
    }
  });

  if (req.method !== "GET" && req.method !== "HEAD") {
    send(req, res, 405, { Allow: "GET, HEAD", "Content-Type": "text/plain; charset=utf-8" }, "Method Not Allowed");
    return accessLog(req, res, 405, 0);
  }

  if (target === "/favicon.ico") {
    send(req, res, 204, { "Cache-Control": "public, max-age=86400" }, null);
    return accessLog(req, res, 204, 0);
  }

  const entry = FILES[target];
  if (!entry) {
    send(req, res, 404, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" }, "Not Found");
    return accessLog(req, res, 404, 0, "not in allowlist");
  }

  const file = path.join(ROOT, target);
  let st;
  try {
    st = await statFile(file);
  } catch (err) {
    log("ERROR reading", target, err.message);
    send(req, res, 500, { "Content-Type": "text/plain; charset=utf-8" }, "Internal Server Error");
    return accessLog(req, res, 500, 0);
  }

  const etag = `"${st.size.toString(16)}-${Math.floor(st.mtimeMs).toString(16)}"`;
  const lastModified = new Date(st.mtimeMs).toUTCString();

  const inm = req.headers["if-none-match"];
  const ims = req.headers["if-modified-since"];
  const etagHit = inm && inm.split(",").some((v) => v.trim() === etag);
  const timeHit = !inm && ims && new Date(ims).getTime() >= Math.floor(st.mtimeMs / 1000) * 1000;

  if (etagHit || timeHit) {
    send(req, res, 304, { ETag: etag, "Last-Modified": lastModified, "Cache-Control": entry.cache }, null);
    return accessLog(req, res, 304, 0, "not modified");
  }

  let buf;
  try {
    buf = await readFile(file);
  } catch (err) {
    log("ERROR reading", target, err.message);
    send(req, res, 500, { "Content-Type": "text/plain; charset=utf-8" }, "Internal Server Error");
    return accessLog(req, res, 500, 0);
  }

  const headers = {
    "Content-Type": entry.type,
    ETag: etag,
    "Last-Modified": lastModified,
    "Cache-Control": entry.cache,
    Vary: "Accept-Encoding",
  };

  const accepts = String(req.headers["accept-encoding"] || "");
  if (buf.length >= GZIP_MIN && /\bgzip\b/.test(accepts)) {
    buf = zlib.gzipSync(buf, { level: 6 });
    headers["Content-Encoding"] = "gzip";
  }

  headers["Content-Length"] = buf.length;
  send(req, res, 200, headers, buf);
  accessLog(req, res, 200, buf.length);
}

const server = http.createServer((req, res) => {
  handle(req, res).catch((err) => {
    log("UNHANDLED", req.url, err && err.stack);
    if (!res.headersSent) {
      send(req, res, 500, { "Content-Type": "text/plain; charset=utf-8" }, "Internal Server Error");
    } else {
      res.end();
    }
  });
});

server.keepAliveTimeout = 65000;
server.headersTimeout = 70000;

server.listen(PORT, HOST, () => {
  log(`Il-Malti static server listening on http://${HOST}:${PORT}`);
  log(`serving: ${Object.keys(FILES).join(", ")}`);
});

function shutdown(signal) {
  log(`received ${signal}, shutting down`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 3000).unref();
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
