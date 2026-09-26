import {createRequire} from 'node:module';
import {mkdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url)),require=createRequire(import.meta.url);
let playwright;for(const candidate of[process.env.PLAYWRIGHT_MODULE_PATH,'playwright'].filter(Boolean))try{playwright=require(candidate);break}catch{}
if(!playwright)throw Error('Set PLAYWRIGHT_MODULE_PATH');
const browser=await playwright.chromium.launch(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{});
const page=await browser.newPage({viewport:{width:390,height:844}}),failures=[],errors=[];
page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text())});
const check=(name,condition,detail='')=>{console.log(`${condition?'PASS':'FAIL'} ${name} ${detail}`);if(!condition)failures.push(name)};
const url=pathToFileURL(path.join(here,'index.html')).href+'?seed=8080&fresh=v08';
const artifacts=path.resolve(process.env.VOXEL_ARTIFACT_DIR||path.join(here,'../../artifacts/voxel-mine'));await mkdir(artifacts,{recursive:true});
async function fresh(){await page.goto(url);await page.waitForFunction(()=>typeof debugState==='function');await page.evaluate(()=>resetGame())}
async function equip(traits){return page.evaluate(traits=>{player.workshopUnlocked=true;player.gears=[];player.equippedGearIds=[];for(const traitId of traits){const gear=debugGrantGear(traitId);player.equippedGearIds.push(gear.id)}renderBase();return debugGearState()},traits)}
async function terrainFixture(traits,{enemy=false}={}){await fresh();await equip(traits);await page.evaluate(enemy=>{expedition.routeLevel=1;debugDepart(enemy?2:1);cells.fill(0);damage.fill(0);pendingBreaks.length=0;creatures.length=0;trees.length=0;expedition.returnRequested=false;expedition.fuel=20;expedition.turns=0;expedition.actionPendingThreat=false;expedition.gearRuntime={stakes:[],autoResolvedTurn:0};for(const [x,y,z] of[[5,3,5],[6,3,5],[4,3,5],[5,4,5],[5,3,6],[7,3,5],[8,3,5]])cells[cellIndex(x,y,z)]=M_STONE;solidCount=7;player.pickaxe=5;player.power=0;player.range=0;player.chain=0;if(enemy){expedition.enemy.cellIndex=cellIndex(12,3,12);expedition.enemy.turnsUntilAttack=4}rebuildSurface()},enemy)}
try{
  await fresh();
  const traits=await page.evaluate(()=>GEAR_TRAITS.map(({id,weight})=>({id,weight}))),newTraits=traits.filter(entry=>['autoDrill','tripleAmp','canopyResonator'].includes(entry.id));
  check('Three conditional traits exist with weights 3,2,2',JSON.stringify(newTraits)===JSON.stringify([{id:'autoDrill',weight:3},{id:'tripleAmp',weight:2},{id:'canopyResonator',weight:2}]),JSON.stringify(newTraits));
  const rolls=await page.evaluate(()=>Array.from({length:500},(_,index)=>createGear('qa-'+index).trait));
  check('Random gear generation can roll every conditional trait',newTraits.every(({id})=>rolls.includes(id)),JSON.stringify(Object.fromEntries(newTraits.map(({id})=>[id,rolls.filter(value=>value===id).length]))));
  await fresh();
  const loadout=await page.evaluate(()=>{player.workshopUnlocked=true;player.gears=[];player.equippedGearIds=[];for(const traitId of['chain','tripleAmp','canopyResonator','appraisal'])debugGrantGear(traitId);const firstThree=player.gears.slice(0,3).map(gear=>debugToggleGear(gear.id));const fourth=debugToggleGear(player.gears[3].id);return{firstThree,fourth,ids:player.equippedGearIds.length,weight:equippedWeight()}});
  check('Port loadout still enforces maximum 3 and capacity 6',loadout.firstThree.every(Boolean)&&loadout.ids===3&&loadout.weight===5&&!loadout.fourth,JSON.stringify(loadout));
  check('Gear changes remain port-only',await page.evaluate(()=>{debugDepart(1);return !debugToggleGear(player.equippedGearIds[0])}));

  await terrainFixture(['autoDrill']);
  const placed=await page.evaluate(()=>{const center=cellIndex(5,3,5),before={fuel:expedition.fuel,turns:expedition.turns};debugMineCell(center);return{before,after:{fuel:expedition.fuel,turns:expedition.turns},runtime:debugGearState().runtime,damage:Array.from(damage)}});
  check('Auto drill places per equipped individual on first valid manual terrain action',placed.runtime.stakes.length===1&&placed.runtime.stakes[0].cellIndex===await page.evaluate(()=>cellIndex(5,3,5))&&placed.runtime.stakes[0].placedTurn===1,JSON.stringify(placed.runtime));
  check('Placement turn does not fire auto drill',placed.damage.every(value=>value===0));
  const fired=await page.evaluate(()=>{const before={fuel:expedition.fuel,turns:expedition.turns,enemy:expedition.enemy?.turnsUntilAttack};beginAction();completeAction();const damaged=Array.from(damage).map((value,index)=>({value,index})).filter(entry=>entry.value);return{before,after:{fuel:expedition.fuel,turns:expedition.turns,enemy:expedition.enemy?.turnsUntilAttack},damaged,runtime:debugGearState().runtime}});
  const expectedNearest=await page.evaluate(()=>cellIndex(4,3,5));
  check('Next action drills exactly one candidate ordered by distance then index',fired.damaged.length===1&&fired.damaged[0].index===expectedNearest&&fired.damaged[0].value===1,JSON.stringify(fired));
  check('Auto drill adds no fuel, turn, or threat cost',fired.after.fuel===fired.before.fuel-1&&fired.after.turns===fired.before.turns+1&&fired.after.enemy===fired.before.enemy);
  check('Auto drill never targets outside Manhattan distance 2',await page.evaluate(()=>{const stake=expedition.gearRuntime.stakes[0],origin=[];indexToXYZ(stake.cellIndex,origin);return autoDrillCandidates(stake).every(({index})=>{const p=[];indexToXYZ(index,p);return p.reduce((sum,value,axis)=>sum+Math.abs(value-origin[axis]),0)<=2})}));
  const savedStake=await page.evaluate(()=>{debugSave();return JSON.stringify(expedition.gearRuntime)});await page.reload();await page.waitForFunction(()=>typeof debugState==='function');
  check('Auto drill runtime survives save and reload',await page.evaluate(expected=>JSON.stringify(expedition.gearRuntime)===expected,savedStake));
  const visual=await page.evaluate(()=>({boxes:autoDrillBoxes().length,faces:buildPropFaces().filter(face=>face.entity.type==='autoDrill').length}));
  check('Placed auto drill has a 3D world mesh',visual.boxes>1&&visual.faces>0,JSON.stringify(visual));
  await page.screenshot({path:path.join(artifacts,'gear-auto-drill-v080.png'),fullPage:true});

  await terrainFixture(['autoDrill','autoDrill']);
  const multiple=await page.evaluate(()=>{debugMineCell(cellIndex(5,3,5));const blocks=expedition.blocksDestroyed;beginAction();completeAction();return{stakes:expedition.gearRuntime.stakes.length,damaged:Array.from(damage).filter(Boolean).length,destroyed:expedition.blocksDestroyed-blocks}});
  check('Multiple equipped auto drills place and each emit fixed output 1',multiple.stakes===2&&multiple.damaged===0&&multiple.destroyed===1,JSON.stringify(multiple));

  await terrainFixture(['tripleAmp']);
  const triple=await page.evaluate(()=>{const sample=[];for(const turn of[1,2,3,4,6]){expedition.turns=turn;sample.push([turn,actionRangeBonus('terrain')])}return sample});
  check('Triple amplifier applies only on turns 3 and 6',JSON.stringify(triple)===JSON.stringify([[1,0],[2,0],[3,1],[4,0],[6,1]]),JSON.stringify(triple));
  const consumed=await page.evaluate(()=>{expedition.turns=2;beginAction();completeAction();return{turn:expedition.turns,bonus:actionRangeBonus('terrain')}});
  check('A non-mining action consumes the third-turn amplification',consumed.turn===3&&consumed.bonus===1&&await page.evaluate(()=>{beginAction();return actionRangeBonus('terrain')===0}));

  await fresh();await equip(['canopyResonator','tripleAmp']);await page.evaluate(()=>debugDepart(1));
  const bonuses=await page.evaluate(()=>{expedition.turns=1;const ordinary=[actionRangeBonus('terrain'),actionRangeBonus('wood'),actionRangeBonus('leaf')];expedition.turns=3;const stacked=[actionRangeBonus('terrain'),actionRangeBonus('wood'),actionRangeBonus('leaf')];return{ordinary,stacked}});
  check('Canopy affects leaf targets only and bonuses add with cap +2',JSON.stringify(bonuses)===JSON.stringify({ordinary:[0,0,1],stacked:[1,1,2]}),JSON.stringify(bonuses));
  const treeLoot=await page.evaluate(()=>{const tree=trees.find(entry=>entry.kind==='large');const boxes=treeBoxes('large');tree.removedBlocks=[];player.inventory.timber=0;player.treasures=[];expedition.treasureIds=[];expedition.turns=1;const leaf=3,affected=treeBlocksInRange(boxes,leaf,actionRangeBonus('leaf'));for(const id of affected)removeLargeTreeBlock(tree,id);return{affected,removed:[...tree.removedBlocks],timber:player.inventory.timber||0,treasures:player.treasures.length,timberYield:TREE_CONFIG.largeBlockTimberYield}});
  check('Leaf area removes each block once without duplicating wood or leaf rewards',new Set(treeLoot.affected).size===treeLoot.affected.length&&treeLoot.removed.length===treeLoot.affected.length&&treeLoot.timber===treeLoot.affected.filter(id=>id<3).length*treeLoot.timberYield&&treeLoot.treasures===treeLoot.affected.filter(id=>id>=3).length,JSON.stringify(treeLoot));
  await page.screenshot({path:path.join(artifacts,'gear-build-v080.png'),fullPage:true});

  await terrainFixture(['autoDrill'],{enemy:true});
  const order=await page.evaluate(()=>{const stakeCell=cellIndex(5,3,5),manualTarget=cellIndex(6,3,5),chainTarget=cellIndex(7,3,5),autoTarget=cellIndex(4,3,5);cells.fill(0);damage.fill(0);player.chain=0;cells[stakeCell]=M_GRASS;cells[autoTarget]=M_STONE;solidCount=2;rebuildSurface();debugMineCell(stakeCell);player.chain=1;cells[manualTarget]=M_COPPER;cells[chainTarget]=M_COPPER;solidCount=3;expedition.enemy.turnsUntilAttack=4;debugMineCell(manualTarget);const queued=pendingBreaks.length,threatBefore=expedition.enemy.turnsUntilAttack,blocksBefore=expedition.blocksDestroyed,candidatesBefore=autoDrillCandidates(expedition.gearRuntime.stakes[0]);nowSeconds+=100;processPendingBreaks();return{queued,threatBefore,threatAfter:expedition.enemy.turnsUntilAttack,autoDamage:damage[autoTarget],autoCell:cells[autoTarget],extraDestroyed:expedition.blocksDestroyed-blocksBefore,turns:expedition.turns,fuel:expedition.fuel,runtime:expedition.gearRuntime,candidatesBefore,candidatesAfter:autoDrillCandidates(expedition.gearRuntime.stakes[0])}});
  check('Pending chain settles before auto drill and enemy countdown',order.queued>0&&order.threatBefore===4&&order.threatAfter===3&&(order.autoDamage===1||order.autoCell===0)&&order.extraDestroyed>=1&&order.turns===2,JSON.stringify(order));
  check('Fuel reaching zero does not lose delayed chain/auto rewards',await page.evaluate(()=>{expedition.fuel=0;return expedition.blocksDestroyed>=2&&player.stats.mined>=2}));

  await fresh();await page.evaluate(()=>localStorage.setItem(saveKey(),JSON.stringify({version:8,worldSeed,player:{coins:999},island:{}})));await page.reload();await page.waitForFunction(()=>typeof debugState==='function');
  check('Schema 8 and invalid old saves reset into schema 10',await page.evaluate(()=>player.coins===0&&JSON.parse(localStorage.getItem(saveKey())).version===10));
  check('No runtime errors',errors.length===0,JSON.stringify(errors));
}finally{await browser.close()}
if(failures.length){console.error(`\n${failures.length} failed: ${failures.join(', ')}`);process.exitCode=1}else console.log('\nAll voxel-mine v0.8 conditional gear checks passed.');
