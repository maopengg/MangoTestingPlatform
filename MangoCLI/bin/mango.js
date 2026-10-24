#!/usr/bin/env node

import { run } from "../src/cli.js";

try {
  await run(process.argv);
} catch (error) {
  if (!error.alreadyReported && error.message) {
    process.stderr.write(`${error.message}\n`);
  }
  process.exitCode = Number.isInteger(error.exitCode) ? error.exitCode : 2;
}
