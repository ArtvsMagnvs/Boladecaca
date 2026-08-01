import { render } from "./render";
import { TIERS, BASE_POINT_SIZE } from "../../src/avcs/constants";
import * as fs from "fs";
const lum=(o:any)=>{render(o);return (globalThis as any).__lastLum as number;};
let target=0;
for (const t of ["Q4","Q3","Q2"] as const) { const s=TIERS[t];
  const o={N:s.particles,dprTier:s.dpr,pointSize:BASE_POINT_SIZE*s.pointScale,
    brightBoost:s.brightBoost,hardness:s.edgeHardness,seedFrac:s.seedFraction,label:t};
  const L=lum(o); if(t==="Q4")target=L;
  console.log(`${t}: luz ${(100*L/target).toFixed(1)}% de Q4`);
  fs.writeFileSync(`./out/R_${t}.png`, render(o as any));
}
