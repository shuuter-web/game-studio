import {createRequire} from 'node:module';
import {mkdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH});
const page=await browser.newPage({viewport:{width:390,height:844}});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
await mkdir('artifacts/voxel-mine',{recursive:true});
try {
  await page.goto(pathToFileURL(path.resolve('prototypes/voxel-mine/index.html')).href+'?seed=86086&fresh=gear-art');
  await page.waitForFunction(()=>typeof gearIllustration==='function');
  const result=await page.evaluate(()=>{
    resetGame();
    for(const trait of GEAR_TRAITS){const gear=debugGrantGear(trait.id);gear.name='雲鉄製・旧名称';}
    renderBase();debugSave();
    return {count:document.querySelectorAll('.gear-card .gear-art').length,names:[...document.querySelectorAll('.gear-title')].map(el=>el.textContent),unique:new Set(Object.values(GEAR_ILLUSTRATIONS)).size,labels:[...document.querySelectorAll('.gear-card .gear-art')].map(el=>el.getAttribute('aria-label')),overflow:document.documentElement.scrollWidth>innerWidth};
  });
  if(result.count!==9||result.unique!==9||result.names.some(name=>name.includes('雲鉄製')||name.includes('旧名称'))||result.labels.some(label=>!label.includes('装置'))||result.overflow)throw Error(JSON.stringify(result));
  await page.locator('#port-gears').scrollIntoViewIfNeeded();
  await page.screenshot({path:'artifacts/voxel-mine/gear-illustrations-v086.png'});
  await page.reload();await page.waitForFunction(()=>typeof gearIllustration==='function');
  const restored=await page.evaluate(()=>{const oldNames=player.gears.every(gear=>gear.name==='雲鉄製・旧名称');return oldNames&&document.querySelectorAll('.gear-card .gear-art').length===9&&!document.getElementById('port-gears').textContent.includes('雲鉄製');});
  if(!restored)throw Error('Old save display compatibility');
  await page.evaluate(()=>{debugDepart(1);gainGear('art-test');});
  if(await page.locator('#gear-find-stack .gear-art').count()!==1)throw Error('Acquisition illustration missing');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS gear art: 9 distinct machine drawings, functional names, old save compatibility, mobile layout, accessible labels, acquisition art');
} finally {await browser.close();}
