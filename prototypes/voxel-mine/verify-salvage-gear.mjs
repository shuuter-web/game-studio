import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH});
const page=await browser.newPage({viewport:{width:390,height:844}});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
try {
  await page.goto(pathToFileURL(path.resolve('prototypes/voxel-mine/index.html')).href+'?seed=84084&fresh=salvage');
  await page.waitForFunction(()=>typeof discoverSalvageGear==='function');
  const result=await page.evaluate(()=>{
    resetGame();debugDepart(1);
    const candidates=Array.from(cells,(value,index)=>({value,index})).filter(entry=>entry.value);
    const expected=candidates.filter(({index})=>makeRandomGenerator(hashSeed(worldSeed+':salvage:'+islandLevel+':'+tripSerial+':'+index))()<SALVAGE_GEAR_DISCOVERY.chance);
    const excluded=discoverSalvageGear(expected[0].index);
    gainGear('first-discovery');
    const fuel=expedition.fuel,turns=expedition.turns;
    reseedLogic(887);const expectedRandom=random();reseedLogic(887);
    const first=discoverSalvageGear(expected[0].index),duplicate=discoverSalvageGear(expected[0].index);
    const second=discoverSalvageGear(expected[1].index),third=discoverSalvageGear(expected[2].index);
    const rngStable=random()===expectedRandom;
    const gearIds=[...expedition.gearIds];debugSave();
    return {excluded,first,duplicate,second,third,rngStable,gearIds,count:player.gears.length,noCost:fuel===expedition.fuel&&turns===expedition.turns};
  });
  if(result.excluded||!result.first||result.duplicate||!result.second||result.third||!result.rngStable||result.count!==3||!result.noCost)throw Error(JSON.stringify(result));
  await page.reload();await page.waitForFunction(()=>typeof discoverSalvageGear==='function');
  const restored=await page.evaluate(()=>{
    const count=player.gears.length;debugReturn();const summary=document.getElementById('result-details').textContent;
    debugAcknowledgeResult();debugDepart(1);
    const next=Array.from(cells,(value,index)=>({value,index})).find(({value,index})=>value&&makeRandomGenerator(hashSeed(worldSeed+':salvage:'+islandLevel+':'+tripSerial+':'+index))()<SALVAGE_GEAR_DISCOVERY.chance);
    const found=discoverSalvageGear(next.index);
    return {count,summary,found,after:player.gears.length};
  });
  if(restored.count!==3||!restored.summary.includes('重量')||!restored.found||restored.after!==4)throw Error(JSON.stringify(restored));
  // 本番の破壊経路でも抽選・回収されることを検証する。
  const actual=await page.evaluate(()=>{
    resetGame();gainGear('first-discovery');debugDepart(1);
    const target=Array.from(cells,(value,index)=>({value,index})).find(({value,index})=>value&&makeRandomGenerator(hashSeed(worldSeed+':salvage:'+islandLevel+':'+tripSerial+':'+index))()<SALVAGE_GEAR_DISCOVERY.chance);
    const before=player.gears.length;breakCell(target.index,0,false);const after=player.gears.length;
    breakCell(target.index,0,false);return {before,after,again:player.gears.length};
  });
  if(actual.after!==actual.before+1||actual.again!==actual.after)throw Error(JSON.stringify(actual));
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS salvage gear: first discovery priority, deterministic draw, two per trip, no duplicate, no RNG drift, no extra cost, reload, result facts, next-trip discovery, actual break path');
} finally {await browser.close();}
