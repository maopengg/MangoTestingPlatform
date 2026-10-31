import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { createRequire } from 'node:module'
const ts=createRequire(new URL('../mango-console/package.json',import.meta.url))('typescript')
const readSource=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8')

const source=readSource('mango-console/src/api/axios.config.ts')
const ast=ts.createSourceFile('axios.ts',source,ts.ScriptTarget.Latest,true)
const names=new Set(['deploymentConfig','baseURL','minioURL','webSocketURL'])
const body=ast.statements.filter(s=>ts.isFunctionDeclaration(s)&&['currentBaseURL','currentApiHost','currentWebSocketURL'].includes(s.name?.text)||
  ts.isVariableStatement(s)&&s.declarationList.declarations.some(d=>names.has(d.name.text)))
  .map(s=>s.getText(ast).replace(/^export /,'').replaceAll('import.meta.env','buildEnv')).join('\n')
const run=new Function('window','buildEnv',ts.transpileModule(body,{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText+';return {baseURL,minioURL,webSocketURL}')

test('runtime API/socket/storage override bundled values',()=>{
 const result=run({__MANGO_CONFIG__:{apiBase:'https://api.example.com/api',socketURL:'wss://api.example.com/ws/web/socket?',storageBase:'https://files.example.com/bucket'},location:{}},
 {VITE_APP_BASE_URL:'old',VITE_APP_SOCKET_URL:'old',VITE_APP_MINIO_URL:'old'})
 assert.deepEqual(result,{baseURL:'https://api.example.com/api',webSocketURL:'wss://api.example.com/ws/web/socket?',minioURL:'https://files.example.com/bucket'})
})
test('same origin deployment uses /api on any frontend port',()=>{
 for(const port of ['8000','8001','443']){
  const result=run({__MANGO_CONFIG__:{apiBase:'/api',socketURL:'wss://web.example.com/ws/web/socket?',storageBase:''},location:{port}}, {})
  assert.equal(result.baseURL,'/api')
  assert.equal(result.minioURL,'')
 }
})
test('Vite dev retains existing API and realtime fallbacks',()=>{
 const result=run({location:{port:'5173',hostname:'localhost',protocol:'http:',host:'localhost:5173'}},{VITE_APP_BASE_URL:'/api'})
 assert.equal(result.baseURL,'http://localhost:8000/api')
 assert.equal(result.webSocketURL,'ws://localhost:8011/ws/web/socket?')
})
test('runtime script loads before application and is never cached',()=>{
 const html=readSource('mango-console/index.html')
 assert.ok(html.indexOf('/runtime-config.js')<html.indexOf('/src/main.ts'))
 const nginx=readSource('mango-console/nginx/default.conf')
 assert.match(nginx,/location = \/runtime-config.js \{[^}]*Cache-Control "no-store"/)
})
