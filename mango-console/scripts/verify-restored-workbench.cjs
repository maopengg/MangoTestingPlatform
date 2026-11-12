// Reuse a running Vite service. The fixture mocks every platform request.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const baseUrl = process.env.MANGO_VISUAL_BASE_URL || 'http://localhost:5173';
const output = process.env.MANGO_VISUAL_OUTPUT || '/tmp';
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});const results=[];
for(const width of [1900,2560,3840]){
 const page=await browser.newPage({viewport:{width,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`${baseUrl}/tests/fixtures/morning-recovery.html`,{waitUntil:'networkidle'});await page.waitForTimeout(700);
 const body=page.locator('.arco-table-body').first();const layout=await body.evaluate(e=>{const r=e.getBoundingClientRect(),p=e.closest('.api-case-panel').getBoundingClientRect();return {height:e.clientHeight,total:e.scrollHeight,width:r.width,panelWidth:p.width,x:r.x,panelX:p.x}});
 assert(layout.total>layout.height+200,`scrollable table ${width}`);assert(layout.width<=layout.panelWidth,`table fits ${width}`);
 await body.hover();await page.mouse.wheel(0,300);await page.waitForTimeout(100);assert(await body.evaluate(e=>e.scrollTop)>0,`wheel scrolls body ${width}`);
 assert.equal(await page.evaluate(()=>window.scrollY),0,`wheel must not scroll page ${width}`);
 const grid=page.locator('.mango-mcp-capability-grid');const promptTop=await page.locator('.mango-mcp-prompt-panel').evaluate(e=>e.getBoundingClientRect().top);
 await grid.hover();await page.mouse.wheel(0,300);await page.waitForTimeout(100);assert(await grid.evaluate(e=>e.scrollTop)>0,`MCP grid scroll ${width}`);
 assert.equal(await page.locator('.mango-mcp-prompt-panel').evaluate(e=>e.getBoundingClientRect().top),promptTop,`MCP prompt fixed ${width}`);
 await grid.evaluate(e=>e.scrollTop=0);const monitor=page.locator('.mango-mcp-capability-item[aria-label^="监控中心"]');await monitor.focus();await page.waitForTimeout(250);
 assert(await page.locator('.mango-mcp-capability-detail').filter({hasText:'启动或停止监控'}).isVisible(),`MCP detail focus ${width}`);
 await page.locator('h2').first().click();
 const chart=await page.locator('.mango-report-source-trend__chart').evaluate(e=>({available:e.clientHeight,svg:e.querySelector('svg')?.getBoundingClientRect().height}));assert(chart.svg>=chart.available*.9,`trend fills ${width}`);
 assert.equal(await page.locator('.mango-status-total strong').nth(1).innerText(),'99.07%');
 const clipped=await page.locator('.mango-recovery-charts section').evaluateAll(cards=>cards.flatMap(card=>{const r=card.getBoundingClientRect();return [...card.querySelectorAll('svg text')].filter(e=>{const b=e.getBoundingClientRect();return b.width&&b.height&&(b.x<r.x-1||b.right>r.right+1||b.y<r.y-1||b.bottom>r.bottom+1)}).map(e=>e.textContent)}));assert.deepEqual(clipped,[],`chart text clipping ${width}`);
 assert((await page.locator('.mango-recovery-charts section').first().innerText()).includes('10 份 · 100.00%'), `report count unit ${width}`);
 const palette=await page.evaluate(()=>{const color=getComputedStyle(document.documentElement).getPropertyValue('--m-danger').trim();document.documentElement.style.setProperty('--m-chart-1',color);window.dispatchEvent(new Event('mango-theme-change'));return color});
 await page.waitForTimeout(350);assert(await page.locator('.mango-chart-item').evaluate((e,color)=>[...e.querySelectorAll('path')].some(path=>path.getAttribute('fill')===color),palette),`pie theme redraw ${width}`);
 assert((await page.locator('.mango-footer-container').innerText()).includes(String(new Date().getFullYear())),`automatic copyright year ${width}`);
 assert.deepEqual(errors,[],`runtime errors ${width}`);await page.screenshot({path:`${output}/mango-recovery-${width}.png`,fullPage:true});
 results.push({width,scale:await page.evaluate(()=>getComputedStyle(document.documentElement).fontSize),table:layout,trend:chart,errors:errors.length});await page.close();
}
console.log(JSON.stringify(results,null,2));await browser.close()})().catch(e=>{console.error(e);process.exit(1)});
