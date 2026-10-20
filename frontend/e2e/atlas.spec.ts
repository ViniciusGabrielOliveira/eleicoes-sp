import {test,expect} from '@playwright/test';

function control(page:import('@playwright/test').Page,label:string){
 return page.locator('app-multi-select').filter({has:page.locator('.label',{hasText:new RegExp('^'+label+'$','i')})});
}
test('mapa real: múltiplas cidades, bairros, cargo e legenda',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1440,height:1120});
 await page.goto('/atlas/');
 await expect(page).toHaveTitle('Atlas Eleitoral SP · 2026');
 await expect(page.locator('.rank-item').first()).toBeVisible();
 await expect(page.locator('.loading')).toHaveCount(0);
 await expect(page.locator('.leaflet-votePixels-pane')).toHaveCSS('z-index','450');
 const pixels=await page.locator('.electoral-pixels').evaluate((canvas:HTMLCanvasElement)=>{
  const rgba=canvas.getContext('2d')!.getImageData(0,0,canvas.width,canvas.height).data;
  let count=0;for(let i=3;i<rgba.length;i+=4)if(rgba[i])count++;return count;
 });
 expect(pixels).toBeGreaterThan(1000);
 await expect(page.locator('.leaflet-voteTargets-pane path[data-symbol-shape="circle"]').first()).toBeVisible();
 expect(await page.locator('.leaflet-voteTargets-pane path[data-symbol-shape="circle"]').first().getAttribute('d')).toContain('a');
 await page.screenshot({path:'../reports/atlas-desktop.png',fullPage:true});
 const cities=control(page,'Cidades');await cities.locator('summary').click();
 await cities.locator('input').fill('são paulo');
 await cities.getByRole('button',{name:'SÃO PAULO',exact:true}).click();
 await expect(page.locator('.territory-label')).toContainText('BAIRROS',{timeout:30000});
 await expect(page.locator('.loading')).toHaveCount(0);
 await cities.locator('input').fill('campinas');
 await cities.getByRole('button',{name:'CAMPINAS',exact:true}).click();
 await expect(cities.locator('summary')).toContainText('2 selecionados');
 await cities.locator('summary').click();
 await expect(page.locator('.loading')).toHaveCount(0);
 const bairros=control(page,'Bairros');await bairros.locator('summary').click();
 await bairros.locator('input').fill('vila mariana');
 await bairros.getByRole('button',{name:'VILA MARIANA · SÃO PAULO',exact:true}).click();
 await bairros.locator('input').fill('ipiranga');
 await bairros.getByRole('button',{name:'IPIRANGA · SÃO PAULO',exact:true}).click();
 await expect(bairros.locator('summary')).toContainText('2 selecionados');
 await bairros.locator('summary').click();
 await expect(page.locator('.loading')).toHaveCount(0);
 await expect(page.locator('.map-message')).toHaveCount(0);
 await page.screenshot({path:'../reports/atlas-neighborhoods.png',fullPage:true});
 const block=page.locator('.leaflet-voteTargets-pane path[data-area-key="71072|VILA MARIANA"]');
 await expect(block).toHaveAttribute('data-symbol-shape','circle');
 await block.hover();
 await expect(page.locator('.leaflet-tooltip .tooltip-candidate')).toHaveCount(5);
 await expect(page.locator('.leaflet-tooltip')).toContainText('VILA MARIANA');
 const tipBounds=await page.locator('.leaflet-tooltip').boundingBox();
 const mapBounds=await page.locator('.map').boundingBox();
 expect(tipBounds!.y).toBeGreaterThanOrEqual(mapBounds!.y);
 expect(tipBounds!.y+tipBounds!.height).toBeLessThanOrEqual(mapBounds!.y+mapBounds!.height);
 await expect(page.locator('.leaflet-tooltip')).toContainText('% do total nacional do candidato');
 const reference=await page.request.get('/map/data?office=1&round=1&level=neighborhood&municipalities=71072&neighborhoods=71072%7CVILA%20MARIANA');
 const top=(await reference.json()).areas[0].top_five;
 for(let i=0;i<5;i++){
  const text=new Intl.NumberFormat('pt-BR').format(top[i].votes)+' votos — '+new Intl.NumberFormat('pt-BR',{maximumFractionDigits:6}).format(top[i].national_share_pct)+'%';
  await expect(page.locator('.leaflet-tooltip .tooltip-candidate').nth(i)).toContainText(text);
 }
 await page.screenshot({path:'../reports/atlas-hover.png',fullPage:true});
 await page.locator('.select-field select').first().selectOption('6');
 await expect(page.locator('.loading')).toHaveCount(0);
 await expect(page.locator('.rank-name').first()).not.toContainText('FLAVIO');
 const votes=await page.locator('.total-votes strong').innerText();
 const scale=await page.locator('.vote-scale').innerText();
 const available=await (await page.request.get('/candidates?office=6&round=1&limit=2')).json();
 const candidates=control(page,'Candidatos no mosaico');await candidates.locator('summary').click();
 await candidates.locator('.list button').first().click();
 await candidates.locator('summary').click();
 await expect(page.locator('.loading')).toHaveCount(0);
 await expect(page.locator('.rank-item')).toHaveCount(1);
 await expect(page.getByText('Outros candidatos',{exact:true})).toHaveCount(0);
 const params=new URLSearchParams({office:'6',round:'1',level:'neighborhood'});
 params.append('municipalities','71072');params.append('municipalities','62910');
 params.append('neighborhoods','71072|VILA MARIANA');params.append('neighborhoods','71072|IPIRANGA');
 params.append('candidate_ids',String(available[0].candidate_id));
 const selected=await (await page.request.get('/map/data?'+params)).json();
 await expect(page.locator('.total-votes strong')).toHaveText(new Intl.NumberFormat('pt-BR').format(selected.candidates[0].votes));
 await expect(page.locator('.vote-scale')).toHaveText(scale);
 const gray=await page.locator('.electoral-pixels').evaluate((canvas:HTMLCanvasElement)=>{
  const rgba=canvas.getContext('2d')!.getImageData(0,0,canvas.width,canvas.height).data;
  let count=0;for(let i=0;i<rgba.length;i+=4)if(rgba[i]===120&&rgba[i+1]===135&&rgba[i+2]===126&&rgba[i+3]===255)count++;return count;
 });
 expect(gray).toBe(0);
 await page.screenshot({path:'../reports/atlas-filtered.png',fullPage:true});
 await candidates.locator('summary').click();
 await candidates.locator('.list button').nth(1).click();
 await candidates.locator('summary').click();
 await expect(page.locator('.rank-item')).toHaveCount(2);
 await expect(page.getByText('Outros candidatos',{exact:true})).toHaveCount(0);
 await expect(page.locator('.vote-scale')).toHaveText(scale);
 await candidates.locator('summary').click();
 await candidates.getByRole('button',{name:'Limpar',exact:true}).click();
 await candidates.locator('summary').click();
 await expect(page.locator('.total-votes strong')).toHaveText(votes);
 await expect(page.getByText('Outros candidatos',{exact:true}).first()).toBeVisible();
 expect(errors).toEqual([]);
});

test('mobile: layout, zoom e mapa em tela de alta densidade',async({browser})=>{
 const context=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:2});
 const page=await context.newPage();
 await page.goto('/atlas/');
 await expect(page.locator('.rank-item').first()).toBeVisible();
 await expect(page.locator('.loading')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 const cities=control(page,'Cidades');await cities.locator('summary').click();
 expect(await cities.locator('.popover').evaluate(e=>e.getBoundingClientRect().right<=innerWidth)).toBe(true);
 await cities.getByRole('button',{name:'Concluir'}).click();
 await page.locator('.leaflet-control-zoom-in').click();
 await expect(page.locator('.electoral-pixels')).toHaveCSS('visibility','visible');
 await page.screenshot({path:'../reports/atlas-mobile.png',fullPage:true});
 await context.close();
});

test('tabela separada acompanha pizzas e expande todos os candidatos',async({page})=>{
 await page.goto('/atlas/');
 await expect(page.locator('.loading')).toHaveCount(0,{timeout:30000});
 const table=page.locator('app-territory-table');
 await expect(table.getByRole('heading',{name:'Pizzas visíveis no mapa'})).toBeVisible();
 await expect(table.locator('.territory-summary').first()).toBeVisible();
 const visible=await page.locator('.leaflet-voteTargets-pane path[data-area-key]').count();
 await expect(table.locator('.territory-summary')).toHaveCount(visible);
 await table.locator('.territory-summary button').first().click();
 await expect(table.locator('.candidate-details')).toBeVisible();
 expect(await table.locator('.candidate-details tbody tr').count()).toBeGreaterThan(5);
 await table.locator('.territory-summary button').first().click();
 await expect(table.locator('.candidate-details')).toHaveCount(0);
});

test('visão presidencial pinta territórios e mostra margem sem pizzas',async({page})=>{
 await page.goto('/atlas/');
 await expect(page.locator('.loading')).toHaveCount(0,{timeout:30000});
 const style=page.getByLabel('Estilo do mapa');
 await style.selectOption('winner');
 await expect(page.locator('.winner-note')).toContainText('pontos percentuais');
 await expect(page.locator('.leaflet-voteTargets-pane path')).toHaveCount(0);
 await expect(page.locator('app-territory-table h2')).toHaveText('Locais visíveis no mapa');
 await expect(page.locator('app-territory-table .territory-summary').first()).toBeVisible();
 await page.screenshot({path:'../reports/atlas-winners.png',fullPage:true});
 await page.locator('.select-field select').first().selectOption('3');
 await expect(style).toHaveValue('pizza');
 await expect(style.locator('option[value="winner"]')).toHaveCount(0);
});
