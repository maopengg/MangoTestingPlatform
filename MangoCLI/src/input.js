import { readFile } from "node:fs/promises";

export function parseValue(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export function collectParam(value, previous) {
  return [...previous, value];
}

async function readStream(stream) {
  const chunks = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString("utf8");
}

export async function buildPayload(options, stdin) {
  if (options.input && options.stdin) {
    throw new Error("--input 和 --stdin 不能同时使用");
  }
  let payload = {};
  let content = "";
  if (options.input === "-" || options.stdin) content = await readStream(stdin);
  else if (options.input) content = await readFile(options.input, "utf8");
  if (content.trim()) {
    payload = JSON.parse(content);
    if (!payload || Array.isArray(payload) || typeof payload !== "object") {
      throw new Error("输入必须是 JSON 对象");
    }
  }
  for (const item of options.param || []) {
    const index = item.indexOf("=");
    if (index < 1) throw new Error(`参数必须使用 key=value: ${item}`);
    payload[item.slice(0, index).trim()] = parseValue(item.slice(index + 1));
  }
  return payload;
}

export function appendQuery(url, payload) {
  for (const [key, value] of Object.entries(payload)) {
    if (value == null) continue;
    if (Array.isArray(value)) {
      for (const item of value) url.searchParams.append(key, stringify(item));
    } else {
      url.searchParams.append(key, stringify(value));
    }
  }
}

function stringify(value) {
  return typeof value === "string" ? value : JSON.stringify(value);
}
