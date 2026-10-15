export type CoreNetwork={
  nodeCount:number;
  orangeNodeCount:number;
  nodePositions:Float32Array;
  nodeColors:Float32Array;
  nodeSeeds:Float32Array;
  links:Float32Array;
  flowSeeds:Float32Array;
};

/** Deterministic Fibonacci sphere and sparse short-range network for the CORE.
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
    const orange=i%113===17;
    if(orange){
      orangeNodeCount++;
      nodeColors[j]=1;nodeColors[j+1]=.48;nodeColors[j+2]=.17;
    }else{
      const tint=((i*19)%31)/100;
      nodeColors[j]=.18+tint*.25;nodeColors[j+1]=.75+tint*.25;nodeColors[j+2]=.92+tint*.08;
    }
  }
  const edgeCount=nodeCount+Math.ceil(nodeCount/7);
  const links=new Float32Array(edgeCount*6);
  const flowSeeds=new Float32Array(edgeCount);
  let edge=0;
  for(let i=0;i<nodeCount;i++){
    for(const offset of i%7===0?[1,7]:[1]){
      const next=(i+offset)%nodeCount;
      const from=i*3,to=next*3,at=edge*6;
      links[at]=nodePositions[from];links[at+1]=nodePositions[from+1];links[at+2]=nodePositions[from+2];
      links[at+3]=nodePositions[to];links[at+4]=nodePositions[to+1];links[at+5]=nodePositions[to+2];
      flowSeeds[edge]=((edge*47)%997)/997;
      edge++;
    }
  }
  return {nodeCount,orangeNodeCount,nodePositions,nodeColors,nodeSeeds,links,flowSeeds};
}
