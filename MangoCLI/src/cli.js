import { Command, CommanderError, Option } from "commander";
import { decodeJwt, readToken } from "./auth.js";
import { catalog } from "./catalog.js";
import { CliError, render, request } from "./client.js";
import { clearStoredToken, defaultConfigPath, loadRuntime, readConfig, saveConfig } from "./config.js";
import { buildPayload, collectParam } from "./input.js";
import { browserLogin, tokenNeedsLogin } from "./browser-auth.js";
import { CLI_VERSION } from "./version.js";
import { perfCommands, requireScenarioExecutionInput } from "./perf.js";
import { formatCommandContract, perfCommandContract } from "./contracts.js";

function parseTimeout(value) {
  const match = /^(\d+)(ms|s|m)?$/.exec(value);
  if (!match) throw new Error("timeout 必须是毫秒数或带 ms/s/m 后缀的时长");
  const factors = { ms: 1, s: 1000, m: 60000 };
  return Number(match[1]) * factors[match[2] || "ms"];
}

function globalOptions(program) {
  const options = program.opts();
  return { ...options, timeout: parseTimeout(options.timeout) };
}

function addCapabilityCommand(program, stdout) {
  const capability = program.command("capability").description("查询 MCP 到 CLI 的迁移能力目录").exitOverride();
  capability
    .command("list")
    .description("输出全部能力及迁移状态")
    .exitOverride()
    .option("--status <status>", "complete、pending_api、retired 或 protocol_mcp")
    .option("--domain <domain>", "按领域筛选")
    .action((options) => {
      const items = catalog.filter((item) =>
        (!options.status || item.status === options.status)
        && (!options.domain || item.domain === options.domain));
      stdout.write(`${JSON.stringify({ success: true, data: { count: items.length, items } }, null, 2)}\n`);
    });
}

function addConfigCommand(program, stdout, env) {
  const config = program.command("config").description("管理 CLI 配置").exitOverride();
  config
    .command("set")
    .description("创建或更新服务 profile")
    .exitOverride()
    .option("--name <name>", "profile 名称", "default")
    .requiredOption("--server <url>", "MangoServer 地址")
    .option("--web-url <url>", "测试平台页面地址；默认与 server 同源")
    .option("--auth-prefix <prefix>", "Authorization 前缀", "")
    .action(async (options) => {
      const root = program.opts();
      const configPath = root.config || defaultConfigPath(env);
      const data = await readConfig(configPath);
      data.current = options.name;
      data.profiles ||= {};
      data.profiles[options.name] = {
        ...data.profiles[options.name],
        server: options.server,
        web_url: options.webUrl || data.profiles[options.name]?.web_url || options.server.replace(/\/api\/?$/, ""),
        auth_prefix: options.authPrefix,
      };
      await saveConfig(configPath, data);
      stdout.write(`${JSON.stringify({ success: true, profile: options.name, config: configPath })}\n`);
    });
}

function addAuthCommand(program, io) {
  const auth = program.command("auth").description("登录和管理 REST API JWT").exitOverride();
  auth
    .command("login")
    .description("打开测试平台页面并自动完成 CLI 授权")
    .option("--no-open", "不自动打开浏览器，仅输出授权地址")
    .option("--wait <duration>", "等待页面授权的最长时间", "5m")
    .exitOverride()
    .action(async (options) => {
      const runtime = await loadRuntime(globalOptions(program), io.env);
      const result = await browserLogin(runtime, {
        noOpen: options.open === false,
        waitMs: parseTimeout(options.wait),
        stdout: io.stdout,
        fetchImpl: io.fetchImpl,
        openBrowser: io.openBrowser,
      });
      io.stdout.write(`${JSON.stringify({
        success: true,
        profile: runtime.profileName,
        username: result.username || result.claims?.username,
        user_id: result.user_id || result.claims?.id,
        expires_at: result.claims?.exp ? new Date(result.claims.exp * 1000).toISOString() : undefined,
      }, null, 2)}\n`);
    });
  auth
    .command("import")
    .description("从 stdin 导入页面登录 JWT；自动浏览器授权需后端接口补齐")
    .requiredOption("--token-stdin", "从 stdin 读取 token，避免进入 shell history")
    .exitOverride()
    .action(async () => {
      const root = globalOptions(program);
      const runtime = await loadRuntime(root, io.env);
      const token = await readToken(io.stdin);
      const claims = decodeJwt(token);
      if (!token || !claims) throw new CliError("stdin 中不是有效的 JWT 格式", 2);
      const config = await readConfig(runtime.configPath);
      config.current = runtime.profileName;
      config.profiles ||= {};
      config.profiles[runtime.profileName] = {
        ...config.profiles[runtime.profileName],
        server: runtime.server,
        token,
      };
      await saveConfig(runtime.configPath, config);
      io.stdout.write(`${JSON.stringify({
        success: true,
        profile: runtime.profileName,
        username: claims.username,
        user_id: claims.id,
        expires_at: claims?.exp ? new Date(claims.exp * 1000).toISOString() : undefined,
      }, null, 2)}\n`);
    });

  auth
    .command("status")
    .description("查看当前 profile 的本地 JWT 状态")
    .exitOverride()
    .action(async () => {
      const runtime = await loadRuntime(globalOptions(program), io.env);
      const claims = decodeJwt(runtime.token);
      const expiresAt = claims?.exp ? new Date(claims.exp * 1000) : null;
      io.stdout.write(`${JSON.stringify({
        success: true,
        profile: runtime.profileName,
        server: runtime.server,
        authenticated: Boolean(runtime.token),
        token_source: io.env.MANGO_TOKEN ? "environment" : runtime.token ? "profile" : undefined,
        user_id: claims?.id,
        username: claims?.username,
        expires_at: expiresAt?.toISOString(),
        expired: expiresAt ? expiresAt.getTime() <= Date.now() : undefined,
      }, null, 2)}\n`);
    });

  auth
    .command("logout")
    .description("删除当前 profile 保存的 JWT")
    .exitOverride()
    .action(async () => {
      const root = globalOptions(program);
      const runtime = await loadRuntime(root, io.env);
      const config = await readConfig(runtime.configPath);
      if (config.profiles?.[runtime.profileName]) delete config.profiles[runtime.profileName].token;
      await saveConfig(runtime.configPath, config);
      io.stdout.write(`${JSON.stringify({
        success: true,
        profile: runtime.profileName,
        warning: io.env.MANGO_TOKEN ? "MANGO_TOKEN 仍在环境变量中，需由调用方清除" : undefined,
      }, null, 2)}\n`);
    });
}

function addApiCommands(program, io) {
  const domains = new Map();
  for (const spec of [...catalog.filter((item) => item.status === "complete"), ...perfCommands]) {
    let domain = domains.get(spec.domain);
    if (!domain) {
      domain = program.command(spec.domain).description(`${spec.domain} 领域接口`).exitOverride();
      domains.set(spec.domain, domain);
      if (spec.domain === "perf") {
        domain.command("describe <command>")
          .description("输出性能测试命令的机器可读参数契约，无需登录")
          .exitOverride()
          .action((name) => {
            const contract = perfCommandContract(name);
            if (!contract) throw new CliError(`未知性能测试命令: ${name}`, 2);
            io.stdout.write(`${JSON.stringify({ success: true, data: contract }, null, 2)}\n`);
          });
      }
    }
    const command = domain.command(spec.command).description(spec.summary).exitOverride();
    if (spec.domain === "perf") {
      command.addHelpText("after", formatCommandContract(perfCommandContract(spec.command)));
    }
    command
      .option("--input <path>", "从 JSON 文件读取请求参数，使用 - 表示 stdin")
      .option("--stdin", "从 stdin 读取 JSON 请求参数")
      .option("-p, --param <key=value>", "追加页面 API 参数", collectParam, []);
    if (spec.path.includes("{id}")) command.requiredOption("--id <id>", "目标记录 ID（正整数）");
    if (spec.multipart) command.requiredOption("--file <path>", "需要上传的本地文件");
    command.action(async (options) => {
      const root = globalOptions(program);
      const runtime = await loadRuntime(root, io.env);
      runtime.timeout = root.timeout;
      if (tokenNeedsLogin(runtime.token)) {
        if (!io.stdin.isTTY) {
          throw new CliError("当前未登录；请先执行 mango auth login，或在交互终端重试当前命令", 3);
        }
        const login = await browserLogin(runtime, {
          waitMs: 300000,
          stdout: io.stdout,
          fetchImpl: io.fetchImpl,
          openBrowser: io.openBrowser,
        });
        runtime.token = login.token;
      }
      let payload = await buildPayload(options, io.stdin);
      if (spec.command === "switch-user-test-environment" && spec.domain === "project") {
        const value = payload.selected_environment;
        if (!Number.isSafeInteger(value) || value < 0 || Object.keys(payload).some(key => key !== "selected_environment")) {
          throw new CliError("请仅提供 selected_environment 整数环境ID，当前账号由登录身份确定", 2);
        }
        payload = [{ key: "selected_environment", value }];
      }
      const pathParams = { id: options.id };
      const performRequest = async () => {
        const call = (target, body = payload) => request(
          runtime, target, body, options.file, io.fetchImpl, pathParams,
        );
        if (spec.command === "execute-scenario" && spec.domain === "perf") {
          try {
            requireScenarioExecutionInput(payload);
          } catch (error) {
            throw new CliError(error.message, 2);
          }
          const preflight = await call({ path: "perf/scenario/{id}/preflight", method: "POST" }, {
            test_env: payload.test_env,
            selected_executor_fingerprints: payload.selected_executor_fingerprints,
          });
          if (preflight.data?.can_run !== true) {
            const message = "执行器数量或安全容量不足，性能场景未启动";
            throw new CliError(message, 5, { success: false, message, data: preflight.data });
          }
        }
        if (spec.aggregate) {
          const run = await call(spec);
          const sections = ["requests", "errors", "thresholds", "validity", "nodes"];
          const results = await Promise.all(sections.map((section) => call({
            path: `perf/run/{id}/${section}`, method: "GET",
          }, {})));
          const data = Object.fromEntries([
            ["run", run.data],
            ...sections.map((section, index) => [section, results[index].data]),
          ]);
          return {
            success: true,
            message: run.message,
            data,
            request_id: run.request_id,
            raw: JSON.stringify(data),
          };
        }
        return call(spec);
      };
      try {
        let response;
        try {
          response = await performRequest();
        } catch (error) {
          if (!(error instanceof CliError) || error.exitCode !== 3) throw error;
          await clearStoredToken(runtime);
          runtime.token = "";
          if (io.env.MANGO_TOKEN) {
            throw new CliError("MANGO_TOKEN 已失效，请清除该环境变量并重新执行 mango auth login", 3);
          }
          if (!io.stdin.isTTY) {
            throw new CliError("登录凭证已失效，本地 Token 已清除；请执行 mango auth login", 3);
          }
          io.stderr.write("登录凭证已失效，正在重新登录…\n");
          const login = await browserLogin(runtime, {
            waitMs: 300000,
            stdout: io.stdout,
            fetchImpl: io.fetchImpl,
            openBrowser: io.openBrowser,
          });
          runtime.token = login.token;
          response = await performRequest();
        }
        io.stdout.write(render(response, root.output));
      } catch (error) {
        if (error instanceof CliError && error.response) {
          io.stdout.write(render(error.response, root.output));
        }
        throw error;
      }
    });
  }
}

export function createProgram(overrides = {}) {
  const io = {
    stdin: overrides.stdin || process.stdin,
    stdout: overrides.stdout || process.stdout,
    stderr: overrides.stderr || process.stderr,
    env: overrides.env || process.env,
    fetchImpl: overrides.fetchImpl || globalThis.fetch,
    openBrowser: overrides.openBrowser,
  };
  const program = new Command();
  program
    .name("mango")
    .description("芒果测试平台 REST API CLI")
    .enablePositionalOptions()
    .version(CLI_VERSION)
    .showHelpAfterError()
    .option("--config <path>", "配置文件路径")
    .option("--profile <name>", "配置 profile")
    .option("--server <url>", "MangoServer 地址")
    .option("--web-url <url>", "测试平台页面地址；默认与 server 同源")
    .addOption(new Option("-o, --output <format>", "输出格式").choices(["json", "raw"]).default("json"))
    .option("--timeout <duration>", "HTTP 请求超时", "60s")
    .configureOutput({
      writeOut: (text) => io.stdout.write(text),
      writeErr: (text) => io.stderr.write(text),
    })
    .exitOverride();
  program
    .command("version")
    .description("输出 CLI 版本")
    .exitOverride()
    .action(() => io.stdout.write(`${JSON.stringify({ version: CLI_VERSION })}\n`));
  addCapabilityCommand(program, io.stdout);
  addConfigCommand(program, io.stdout, io.env);
  addAuthCommand(program, io);
  addApiCommands(program, io);
  return program;
}

export async function run(argv, overrides = {}) {
  const program = createProgram(overrides);
  try {
    await program.parseAsync(argv);
  } catch (error) {
    if (error instanceof CommanderError) {
      if (error.code === "commander.helpDisplayed" || error.code === "commander.version") return;
      error.exitCode = 2;
      error.alreadyReported = true;
    }
    throw error;
  }
}
