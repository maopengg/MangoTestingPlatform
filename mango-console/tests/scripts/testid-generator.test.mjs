import assert from 'node:assert/strict';
import test from 'node:test';

import { transformVueSource } from '../../scripts/testid-generator.mjs';

test('preserves Vue comparison and arrow expressions', () => {
  const source = `<template>
  <div>
    <button v-if="items.length > 0" aria-label="保存" @click="() => save()">保存</button>
  </div>
</template>`;
  const result = transformVueSource(source);

  assert.deepEqual(result.errors, []);
  assert.match(result.source, /v-if="items\.length > 0"/);
  assert.match(result.source, /@click="\(\) => save\(\)"/);
  assert.match(result.source, /data-testid="qa-example-button-保存"/);
});

test('only adds ids to semantic interactive elements', () => {
  const source = `<template>
  <section>
    <div>说明</div>
    <a-input placeholder="订单名称" />
    <span @click="openDetail">查看详情</span>
    <button><IconOnly /></button>
  </section>
</template>`;
  const result = transformVueSource(source);

  assert.deepEqual(result.errors, []);
  assert.equal(result.insertions.length, 2);
  assert.match(result.source, /<a-input placeholder="订单名称" data-testid="qa-example-input-订单名称" \/>/);
  assert.match(result.source, /<span @click="openDetail" data-testid="qa-example-span-查看详情">/);
  assert.doesNotMatch(result.source, /<div[^>]+data-testid/);
  assert.doesNotMatch(result.source, /<button[^>]+data-testid/);
});

test('keeps existing ids and makes generated ids unique', () => {
  const source = `<template>
  <div>
    <button aria-label="保存" data-testid="custom-save">保存</button>
    <button aria-label="提交">提交</button>
    <button aria-label="提交">提交</button>
  </div>
</template>`;
  const result = transformVueSource(source);

  assert.deepEqual(result.errors, []);
  assert.equal(result.insertions.length, 2);
  assert.match(result.source, /data-testid="custom-save"/);
  assert.match(result.source, /data-testid="qa-example-button-提交"/);
  assert.match(result.source, /data-testid="qa-example-button-提交-2"/);
});
