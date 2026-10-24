import { readFile } from "node:fs/promises";
import path from "node:path";
import { appendQuery } from "./input.js";

export class CliError extends Error {
  constructor(message, exitCode, response) {
    super(message);
    this.exitCode = exitCode;
    this.response = response;
  }
}

function normalize(raw, requestId) {
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return { success: true, message: "", data: raw, request_id: requestId, raw };
  }
  const success = typeof body.success === "boolean"
    ? body.success
    : typeof body.code === "number"
      ? body.code >= 200 && body.code < 300
      : true;
  return {
    success,
    message: body.message ?? body.msg ?? "",
    data: body.data,
    warnings: body.warnings,
    error_code: body.error_code,
    request_id: requestId,
    raw,
  };
}

export async function request(runtime, spec, payload, uploadFile, fetchImpl = fetch, pathParams = {}) {
  if (!runtime.server) {
    throw new CliError("未配置服务地址，请使用 --server、MANGO_SERVER 或 profile", 2);
  }
  const base = runtime.server.replace(/\/+$/, "");
  const apiBase = base.endsWith("/api") ? base : `${base}/api`;
  const route = spec.path.replace(/\{(\w+)\}/g, (_match, key) => {
    const value = pathParams[key];
    if (!/^[1-9]\d*$/.test(String(value ?? "")) || !Number.isSafeInteger(Number(value))) {
      throw new CliError(`路径参数 ${key} 必须是正整数`, 2);
    }
    return encodeURIComponent(String(value));
  });
  const url = new URL(`${apiBase}/${route.replace(/^\/+/, "")}`);
  const headers = { Accept: "application/json" };
  if (runtime.token) {
    headers.Authorization = runtime.authPrefix
      ? `${runtime.authPrefix} ${runtime.token}`
      : runtime.token;
  }

  const init = {
    method: spec.method,
    headers,
  };
  if (spec.method === "GET") {
    appendQuery(url, payload);
  } else if (spec.multipart) {
    if (!uploadFile) throw new CliError("--file 不能为空", 2);
    const form = new FormData();
    const content = await readFile(uploadFile);
    form.append("test_file", new Blob([content]), path.basename(uploadFile));
    for (const [key, value] of Object.entries(payload)) {
      if (value != null) form.append(key, typeof value === "string" ? value : JSON.stringify(value));
    }
    init.body = form;
  } else {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(payload);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), runtime.timeout);
  timeout.unref?.();
  init.signal = controller.signal;
  let response;
  let raw;
  try {
    response = await fetchImpl(url, init);
    raw = await response.text();
  } catch (error) {
    if (error.name === "TimeoutError" || error.name === "AbortError") {
      throw new CliError("请求超时", 7);
    }
    throw new CliError(`网络请求失败: ${error.message}`, 6);
  } finally {
    clearTimeout(timeout);
  }
  const result = normalize(raw, response.headers.get("x-request-id") || undefined);
  if (!response.ok) {
    const exitCode = response.status === 401 ? 3 : response.status === 403 ? 4 : 6;
    throw new CliError(`HTTP ${response.status}: ${result.message}`, exitCode, result);
  }
  if (!result.success) throw new CliError(result.message || "平台业务校验失败", 5, result);
  return result;
}

export function render(result, format = "json") {
  if (format === "raw") return `${result.raw ?? ""}\n`;
  const output = { success: result.success, message: result.message };
  for (const key of ["data", "warnings", "error_code", "request_id"]) {
    if (result[key] !== undefined && result[key] !== "") output[key] = result[key];
  }
  return `${JSON.stringify(output, null, 2)}\n`;
}
