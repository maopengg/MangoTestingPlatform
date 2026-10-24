import { createHash } from 'node:crypto';
import { readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import vueCompilerSfc from '@vue/compiler-sfc';

const { parse } = vueCompilerSfc;
const NODE_TYPE = {
  ELEMENT: 1,
  TEXT: 2,
  ATTRIBUTE: 6,
  DIRECTIVE: 7,
};

const ATTRIBUTE_NAME = 'data-testid';
const PREFIX = 'qa';
const SOURCE_ROOT = path.resolve(process.cwd(), 'src');
const NATIVE_INTERACTIVE_TAGS = new Set([
  'a',
  'button',
  'input',
  'option',
  'select',
  'textarea',
]);
const INTERACTIVE_COMPONENT_PATTERNS = [
  /^a-(button|checkbox|date-picker|dropdown|input|link|menu-item|option|pagination|radio|select|slider|switch|tab-pane|textarea|time-picker|upload)(-|$)/,
  /^(router-link)$/,
];
const EVENT_NAMES = new Set(['change', 'click', 'dblclick', 'input', 'submit']);
const SEMANTIC_ATTRIBUTES = ['aria-label', 'name', 'placeholder', 'title', 'id'];
const IGNORED_TAGS = new Set(['component', 'keep-alive', 'slot', 'template', 'transition', 'transition-group']);

function normalizeToken(value) {
  return String(value || '')
    .normalize('NFKC')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\p{Letter}\p{Number}_-]+/gu, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^[-_]+|[-_]+$/g, '');
}

function shorten(value, maxLength = 110) {
  if (value.length <= maxLength) return value;
  const digest = createHash('sha1').update(value).digest('hex').slice(0, 8);
  return `${value.slice(0, maxLength - digest.length - 1)}-${digest}`;
}

function staticAttributeValue(node, name) {
  const attribute = node.props.find(
    (prop) => prop.type === NODE_TYPE.ATTRIBUTE && prop.name === name && prop.value,
  );
  if (attribute?.value?.content) return attribute.value.content;

  const binding = node.props.find(
    (prop) =>
      prop.type === NODE_TYPE.DIRECTIVE &&
      prop.name === 'bind' &&
      prop.arg?.isStatic &&
      prop.arg.content === name &&
      prop.exp?.isStatic,
  );
  if (!binding?.exp?.content) return '';
  const expression = binding.exp.content.trim();
  const match = expression.match(/^(['"])(.*)\1$/s);
  return match ? match[2] : '';
}

function directText(node) {
  return node.children
    .filter((child) => child.type === NODE_TYPE.TEXT)
    .map((child) => child.content.trim())
    .filter(Boolean)
    .join(' ')
    .slice(0, 60);
}

function hasInteractiveEvent(node) {
  return node.props.some(
    (prop) =>
      prop.type === NODE_TYPE.DIRECTIVE &&
      prop.name === 'on' &&
      prop.arg?.isStatic &&
      EVENT_NAMES.has(prop.arg.content),
  );
}

function isInteractive(node) {
  if (IGNORED_TAGS.has(node.tag)) return false;
  if (NATIVE_INTERACTIVE_TAGS.has(node.tag)) return true;
  if (INTERACTIVE_COMPONENT_PATTERNS.some((pattern) => pattern.test(node.tag))) return true;
  return hasInteractiveEvent(node);
}

function semanticName(node) {
  for (const name of SEMANTIC_ATTRIBUTES) {
    const value = normalizeToken(staticAttributeValue(node, name));
    if (value) return value;
  }
  return normalizeToken(directText(node));
}

function hasTestId(node) {
  return node.props.some(
    (prop) => prop.type === NODE_TYPE.ATTRIBUTE && prop.name === ATTRIBUTE_NAME,
  );
}

function collectExistingTestIds(node, values) {
  if (!node) return;
  if (node.type === NODE_TYPE.ELEMENT) {
    const value = staticAttributeValue(node, ATTRIBUTE_NAME);
    if (value) values.add(value);
  }
  for (const child of node.children || []) collectExistingTestIds(child, values);
  for (const branch of node.branches || []) collectExistingTestIds(branch, values);
}

function openingTagInsertOffset(source, startOffset) {
  let quote = '';
  for (let index = startOffset; index < source.length; index += 1) {
    const character = source[index];
    if (quote) {
      if (character === quote && source[index - 1] !== '\\') quote = '';
      continue;
    }
    if (character === '"' || character === "'") {
      quote = character;
      continue;
    }
    if (character === '>') {
      let offset = source[index - 1] === '/' ? index - 1 : index;
      while (offset > startOffset && /\s/.test(source[offset - 1])) offset -= 1;
      return offset;
    }
  }
  return -1;
}

function fileNamespace(filename) {
  const relative = path.relative(SOURCE_ROOT, filename).replace(/\\/g, '/');
  return normalizeToken(relative.replace(/\/(index)?\.vue$/i, '').replace(/\.vue$/i, '')) || 'root';
}

function uniqueTestId(base, usedValues) {
  let value = shorten(base);
  let suffix = 2;
  while (usedValues.has(value)) {
    value = shorten(`${base}-${suffix}`);
    suffix += 1;
  }
  usedValues.add(value);
  return value;
}

function collectInsertions(node, source, namespace, usedValues, insertions) {
  if (!node) return;
  if (node.type === NODE_TYPE.ELEMENT && isInteractive(node) && !hasTestId(node)) {
    const name = semanticName(node);
    if (name) {
      const tag = normalizeToken(node.tag.replace(/^a-/, ''));
      const testId = uniqueTestId(`${PREFIX}-${namespace}-${tag}-${name}`, usedValues);
      const offset = openingTagInsertOffset(source, node.loc.start.offset);
      if (offset < 0) throw new Error(`无法识别 <${node.tag}> 的开始标签位置`);
      insertions.push({ offset, testId, tag: node.tag, line: node.loc.start.line });
    }
  }
  for (const child of node.children || []) {
    collectInsertions(child, source, namespace, usedValues, insertions);
  }
  for (const branch of node.branches || []) {
    collectInsertions(branch, source, namespace, usedValues, insertions);
  }
}

export function transformVueSource(source, filename = path.join(SOURCE_ROOT, 'Example.vue')) {
  const parsed = parse(source, { filename });
  if (parsed.errors.length) {
    return { source, insertions: [], errors: parsed.errors.map(String) };
  }
  if (!parsed.descriptor.template?.ast) return { source, insertions: [], errors: [] };

  const usedValues = new Set();
  collectExistingTestIds(parsed.descriptor.template.ast, usedValues);
  const insertions = [];
  collectInsertions(
    parsed.descriptor.template.ast,
    source,
    fileNamespace(filename),
    usedValues,
    insertions,
  );

  let nextSource = source;
  for (const insertion of [...insertions].sort((left, right) => right.offset - left.offset)) {
    nextSource = `${nextSource.slice(0, insertion.offset)} ${ATTRIBUTE_NAME}="${insertion.testId}"${nextSource.slice(insertion.offset)}`;
  }

  const validation = parse(nextSource, { filename });
  return {
    source: nextSource,
    insertions,
    errors: validation.errors.map(String),
  };
}

async function listVueFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const target = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...(await listVueFiles(target)));
    else if (entry.isFile() && entry.name.endsWith('.vue')) files.push(target);
  }
  return files.sort();
}

async function run() {
  const write = process.argv.includes('--write');
  const check = process.argv.includes('--check');
  const files = await listVueFiles(SOURCE_ROOT);
  const plans = [];
  const errors = [];

  for (const filename of files) {
    const source = await readFile(filename, 'utf8');
    const result = transformVueSource(source, filename);
    if (result.errors.length) errors.push({ filename, errors: result.errors });
    if (result.insertions.length) plans.push({ filename, ...result });
  }

  if (errors.length) {
    for (const item of errors) {
      console.error(`\n${path.relative(process.cwd(), item.filename)}`);
      for (const error of item.errors) console.error(`  - ${error}`);
    }
    console.error(`\n检测到 ${errors.length} 个模板解析错误，未写入任何文件。`);
    process.exitCode = 2;
    return;
  }

  const total = plans.reduce((sum, plan) => sum + plan.insertions.length, 0);
  for (const plan of plans) {
    console.log(`\n${path.relative(process.cwd(), plan.filename)}`);
    for (const item of plan.insertions.slice(0, 20)) {
      console.log(`  L${item.line} <${item.tag}> ${item.testId}`);
    }
    if (plan.insertions.length > 20) console.log(`  ... 其余 ${plan.insertions.length - 20} 项`);
  }

  if (write) {
    for (const plan of plans) await writeFile(plan.filename, plan.source, 'utf8');
    console.log(`\n已为 ${plans.length} 个文件写入 ${total} 个稳定测试标识。`);
    return;
  }

  console.log(`\n预览：${plans.length} 个文件缺少 ${total} 个稳定测试标识。`);
  if (check && total > 0) process.exitCode = 1;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) run().catch((error) => {
  console.error(error);
  process.exitCode = 2;
});
