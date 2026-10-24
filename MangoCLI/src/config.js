import { readFile, mkdir, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

export function defaultConfigPath(env = process.env) {
  if (env.MANGO_CONFIG) return env.MANGO_CONFIG;
  if (process.platform === "win32" && env.APPDATA) {
    return path.join(env.APPDATA, "mango", "config.json");
  }
  const root = env.XDG_CONFIG_HOME || path.join(os.homedir(), ".config");
  return path.join(root, "mango", "config.json");
}

export async function readConfig(filePath) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") return { current: "default", profiles: {} };
    if (error instanceof SyntaxError) throw new Error(`配置格式错误: ${error.message}`);
    throw error;
  }
}

export async function saveConfig(filePath, config) {
  await mkdir(path.dirname(filePath), { recursive: true, mode: 0o700 });
  await writeFile(filePath, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
}

export async function loadRuntime(options, env = process.env) {
  const configPath = options.config || defaultConfigPath(env);
  const config = await readConfig(configPath);
  const profileName = options.profile || config.current || "default";
  const profile = config.profiles?.[profileName] || {};
  return {
    configPath,
    profileName,
    server: options.server || env.MANGO_SERVER || profile.server || "",
    webUrl: options.webUrl || env.MANGO_WEB_URL || profile.web_url
      || (options.server || env.MANGO_SERVER || profile.server || "").replace(/\/api\/?$/, ""),
    token: env.MANGO_TOKEN || profile.token || "",
    authPrefix: env.MANGO_AUTH_PREFIX || profile.auth_prefix || "",
  };
}

export async function clearStoredToken(runtime) {
  const config = await readConfig(runtime.configPath);
  if (config.profiles?.[runtime.profileName]) {
    delete config.profiles[runtime.profileName].token;
    await saveConfig(runtime.configPath, config);
  }
}
