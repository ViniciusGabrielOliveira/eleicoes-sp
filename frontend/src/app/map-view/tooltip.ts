import * as L from 'leaflet';

/** Mantém nome, ranking e percentuais dentro da janela do mapa. */
export function bindVoteTooltip(layer:L.Layer,map:L.Map,content:()=>HTMLElement):void{
 layer.bindTooltip(content,{sticky:true,direction:'center',className:'vote-tooltip',opacity:1});
 layer.on('tooltipopen mousemove',()=>{
  const tooltip=layer.getTooltip();if(!tooltip?.isOpen())return;
  tooltip.options.offset=L.point(0,-12);tooltip.update();
  const element=tooltip.getElement();if(!element)return;
  const bounds=element.getBoundingClientRect(),viewport=map.getContainer().getBoundingClientRect();
  let dx=0,dy=0;
  if(bounds.left<viewport.left+8)dx=viewport.left+8-bounds.left;
  else if(bounds.right>viewport.right-8)dx=viewport.right-8-bounds.right;
  if(bounds.top<viewport.top+8)dy=viewport.top+8-bounds.top;
  else if(bounds.bottom>viewport.bottom-8)dy=viewport.bottom-8-bounds.bottom;
  tooltip.options.offset=L.point(dx,-12+dy);tooltip.update();
 });
}
