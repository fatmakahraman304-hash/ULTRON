export type CoreNetwork={
  nodeCount:number;
  orangeNodeCount:number;
  nodePositions:Float32Array;
  nodeColors:Float32Array;
  nodeSeeds:Float32Array;
  links:Float32Array;
  flowSeeds:Float32Array;
};

/** Deterministic Fibonacci sphere and spatially local network for the CORE.
 * Geometry is capped to keep low-end laptop GPUs within a predictable budget.
 */
export function buildCoreNetwork(requested=1400):CoreNetwork{
  const value=Number.isFinite(requested)?Math.trunc(requested):1400;
  const nodeCount=Math.max(128,Math.min(2400,value));
  const nodePositions=new Float32Array(nodeCount*3);
  const nodeColors=new Float32Array(nodeCount*3);
  const nodeSeeds=new Float32Array(nodeCount);
  const goldenAngle=Math.PI*(3-Math.sqrt(5));
  let orangeNodeCount=0;
  for(let i=0;i<nodeCount;i++){
    const y=1-2*(i+.5)/nodeCount;
    const radial=Math.sqrt(Math.max(0,1-y*y));
    const theta=goldenAngle*i;
    const radius=1.58+((i*37)%101)/101*.14;
    const j=i*3;
    nodePositions[j]=Math.cos(theta)*radial*radius;
    nodePositions[j+1]=y*radius;
    nodePositions[j+2]=Math.sin(theta)*radial*radius;
    nodeSeeds[i]=((i*73)%997)/997;
    const orange=i%67===17;
    if(orange){
      orangeNodeCount++;
      nodeColors[j]=1;nodeColors[j+1]=.48;nodeColors[j+2]=.17;
    }else{
      const tint=((i*19)%31)/100;
      nodeColors[j]=.18+tint*.25;nodeColors[j+1]=.75+tint*.25;nodeColors[j+2]=.92+tint*.08;
    }
  }
  // Fibonacci indices are not spatial neighbours: i+1 forms long chords and
  // visible latitude stripes. Connect three actual nearest surface neighbours.
  const edges:number[]=[];
  const seen=new Set<string>();
  for(let i=0;i<nodeCount;i++){
    const nearest:Array<{index:number;distance:number}>=[];
    const a=i*3;
    for(let j=0;j<nodeCount;j++){
      if(i===j)continue;
      const b=j*3;
      const distance=(nodePositions[a]-nodePositions[b])**2+(nodePositions[a+1]-nodePositions[b+1])**2+(nodePositions[a+2]-nodePositions[b+2])**2;
      if(distance>.65**2)continue;
      if(nearest.length<3||distance<nearest[nearest.length-1].distance){
        nearest.push({index:j,distance});nearest.sort((x,y)=>x.distance-y.distance);nearest.length=Math.min(3,nearest.length);
      }
    }
    for(const neighbour of nearest){
      const j=neighbour.index,key=`${Math.min(i,j)}:${Math.max(i,j)}`;
      if(seen.has(key))continue;seen.add(key);
      edges.push(...nodePositions.subarray(a,a+3),...nodePositions.subarray(j*3,j*3+3));
    }
  }
  const links=new Float32Array(edges);
  const flowSeeds=Float32Array.from({length:edges.length/6},(_,i)=>((i*47)%997)/997);
  return {nodeCount,orangeNodeCount,nodePositions,nodeColors,nodeSeeds,links,flowSeeds};
}
