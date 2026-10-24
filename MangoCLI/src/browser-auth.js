import { createHash, randomBytes } from "node:crypto";
import http from "node:http";
import { spawn } from "node:child_process";
import { decodeJwt } from "./auth.js";
import { CliError } from "./client.js";
import { readConfig, saveConfig } from "./config.js";
import { CLI_VERSION } from "./version.js";

function base64url(value) {
  return Buffer.from(value).toString("base64url");
}

export function openDefaultBrowser(url) {
  let command;
  let args;
  if (process.platform === "darwin") {
    command = "open";
    args = [url];
  } else if (process.platform === "win32") {
    command = "rundll32.exe";
    args = ["url.dll,FileProtocolHandler", url];
  } else {
    command = "xdg-open";
    args = [url];
  }
  const child = spawn(command, args, { detached: true, stdio: "ignore" });
  child.unref();
  child.on("error", () => {});
}

function callbackPage(ok, message) {
  const title = ok ? "CLI 授权成功" : "CLI 授权失败";
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>${title}</title></head>`
    + `<body style="font-family:system-ui;padding:48px;text-align:center"><h2>${title}</h2>`
    + `<p>${message}</p><p>现在可以关闭此页面并返回终端。</p></body></html>`;
}

function waitForCallback(server, expectedState, waitMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new CliError("浏览器授权等待超时，请重新执行 mango auth login", 7)), waitMs);
    timer.unref?.();
    server.on("request", (request, response) => {
      const url = new URL(request.url || "/", "http://127.0.0.1");
      if (request.method !== "GET" || url.pathname !== "/callback") {
        response.writeHead(404).end();
        return;
      }
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state");
      const error = url.searchParams.get("error");
      const valid = !error && Boolean(code) && state === expectedState;
      response.writeHead(valid ? 200 : 400, { "Content-Type": "text/html; charset=utf-8", "Connection": "close" });
      response.end(callbackPage(valid, valid ? "测试平台已完成授权。" : "授权参数无效或已被取消。"));
      clearTimeout(timer);
      if (valid) resolve(code);
      else reject(new CliError(error || "浏览器返回的授权状态无效", 3));
    });
  });
}

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return server.address().port;
}

async function exchange(runtime, code, verifier, redirectUri, fetchImpl) {
  const base = runtime.server.replace(/\/+$/, "");
  const apiBase = base.endsWith("/api") ? base : `${base}/api`;
  let response;
  try {
    response = await fetchImpl(`${apiBase}/cli/auth/token`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ code, code_verifier: verifier, redirect_uri: redirectUri }),
    });
  } catch (error) {
    throw new CliError(`授权换取失败: ${error.message}`, 6);
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.code !== 200 || !body.data?.token) {
    throw new CliError(body.msg || `授权换取失败 (HTTP ${response.status})`, response.status === 401 ? 3 : 6);
  }
  return body.data;
}

async function persistToken(runtime, token) {
  const config = await readConfig(runtime.configPath);
  config.current = runtime.profileName;
  config.profiles ||= {};
  config.profiles[runtime.profileName] = {
    ...config.profiles[runtime.profileName],
    server: runtime.server,
    web_url: runtime.webUrl,
    token,
  };
  await saveConfig(runtime.configPath, config);
}

export async function checkCliVersion(runtime, fetchImpl = fetch) {
  const base = runtime.server.replace(/\/+$/, "");
  const apiBase = base.endsWith("/api") ? base : `${base}/api`;
  let response;
  try {
    const url = new URL(`${apiBase}/cli/auth/version`);
    url.searchParams.set("version", CLI_VERSION);
    response = await fetchImpl(url, { headers: { Accept: "application/json" } });
  } catch (error) {
    throw new CliError(`CLI 版本校验失败: ${error.message}`, 6);
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.code !== 200) {
    const latest = body.data?.latest_version;
    const suffix = latest ? `，服务器版本 ${latest}` : "";
    throw new CliError(`${body.msg || "CLI 版本与服务器不一致"}${suffix}`, 8);
  }
  return body.data;
}

export async function browserLogin(runtime, options = {}) {
  if (!runtime.server) throw new CliError("未配置服务地址，请先执行 mango config set", 2);
  const fetchImpl = options.fetchImpl || fetch;
  await checkCliVersion(runtime, fetchImpl);
  const verifier = base64url(randomBytes(48));
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  const state = base64url(randomBytes(32));
  const server = http.createServer();
  const port = await listen(server);
  const redirectUri = `http://127.0.0.1:${port}/callback`;
  const webBase = runtime.webUrl.replace(/\/+$/, "");
  const query = new URLSearchParams({
    redirect_uri: redirectUri,
    state,
    code_challenge: challenge,
    version: CLI_VERSION,
  });
  const authorizationUrl = `${webBase}/#/cli-auth?${query}`;
  const callback = waitForCallback(server, state, options.waitMs || 300000);
  try {
    if (options.noOpen) options.stdout?.write(`${authorizationUrl}\n`);
    else (options.openBrowser || openDefaultBrowser)(authorizationUrl);
    const code = await callback;
    const result = await exchange(runtime, code, verifier, redirectUri, fetchImpl);
    await persistToken(runtime, result.token);
    return { ...result, claims: decodeJwt(result.token) };
  } finally {
    server.closeAllConnections?.();
    await new Promise((resolve) => server.close(() => resolve()));
  }
}

export function tokenNeedsLogin(token) {
  if (!token) return true;
  const claims = decodeJwt(token);
  if (!claims) return true;
  return Boolean(claims.exp && claims.exp * 1000 <= Date.now());
}
