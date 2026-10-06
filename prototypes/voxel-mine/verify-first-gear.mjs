import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH});
const page=await browser.newPage({viewport:{width:390,height:844}});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
try {
  await page.goto(pathToFileURL(path.resolve('prototypes/voxel-mine/index.html')).href+'?seed=83083&fresh=first-gear');
  await page.waitForFunction(()=>typeof debugDepart==='function');
  const result=await page.evaluate(()=>{
    resetGame();debugDepart(1);cells.fill(0);damage.fill(0);creatures.length=0;trees.length=0;pendingBreaks.length=0;
    for(let x=2;x<7;x++)cells[cellIndex(x,2,2)]=M_GRASS;
    solidCount=5;rebuildSurface();
    debugMineCell(cellIndex(2,2,2));debugMineCell(cellIndex(3,2,2));
    const before=player.gears.length;
    debugMineCell(cellIndex(4,2,2));
    const gear={...player.gears[0]},notification=document.getElementById('gear-find-stack').textContent;
    debugMineCell(cellIndex(5,2,2));debugSave();
    return {before,gear,notification,count:player.gears.length,haul:expedition.gearIds,fuel:expedition.fuel,equipped:player.equippedGearIds.length};
  });
  if(result.before!==0||result.count!==1||!['autoDrill','tripleAmp','canopyResonator'].includes(result.gear.trait)||result.haul[0]!==result.gear.id||result.fuel!==16||result.equipped!==0||!result.notification.includes('港で搭載'))throw Error(JSON.stringify(result));
  await page.reload();await page.waitForFunction(()=>typeof debugDepart==='function');
  const persisted=await page.evaluate(()=>{
    const gear=player.gears[0];debugReturn();const summary=document.getElementById('result-details').textContent;
    debugAcknowledgeResult();const equipped=debugToggleGear(gear.id);debugDepart(1);
    return {count:player.gears.length,equipped,ids:player.equippedGearIds,summary,range:actionRangeBonus('terrain'),gear};
  });
  if(persisted.count!==1||!persisted.equipped||persisted.ids[0]!==persisted.gear.id||!persisted.summary.includes(persisted.gear.name))throw Error(JSON.stringify(persisted));
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS first gear: three blocks, conditional trait, single reward, no extra fuel, reload, result, manual equip, next expedition');
} finally {await browser.close();}
