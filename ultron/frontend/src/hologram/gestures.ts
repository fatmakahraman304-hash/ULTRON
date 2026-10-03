export type Point = {x:number;y:number;z?:number};
export type Hand = Point[];
export type Gesture = {kind:'idle'|'grab'|'rotate'|'spread'|'zoom';x:number;y:number;distance:number};
const distance=(a:Point,b:Point)=>Math.hypot(a.x-b.x,a.y-b.y);
/** Scale-normalized pinch, with hysteresis to avoid a flickering grab. */
export class GestureInterpreter {
  private pinched=[false,false];
  reset(){this.pinched=[false,false];}
  read(hands:Hand[]):Gesture {
    const valid=hands.filter(h=>h.length>=21).slice(0,2).sort((a,b)=>a[0].x-b[0].x);
    if(!valid.length){this.reset();return {kind:'idle',x:.5,y:.5,distance:0};}
    const centers=valid.map((h,i)=>{
      const scale=Math.max(.025,distance(h[0],h[9]));
      const ratio=distance(h[4],h[8])/scale;
      this.pinched[i]=ratio<(this.pinched[i]?.55:.36);
      return {x:1-h[8].x,y:h[8].y};
    });
    if(valid.length===2){
      return {kind:this.pinched[0]&&this.pinched[1]?'spread':'zoom',x:(centers[0].x+centers[1].x)/2,y:(centers[0].y+centers[1].y)/2,distance:distance(centers[0],centers[1])};
    }
    this.pinched[1]=false;
    return {kind:this.pinched[0]?'grab':'rotate',...centers[0],distance:0};
  }
}
