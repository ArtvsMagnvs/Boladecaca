// Valida sintácticamente el shader de simulación COMPLETO (con includes
// resueltos, igual que hace ShaderSystem en runtime).
const fs=require("fs"), path=require("path");
const D=path.join(__dirname,"../../src/avcs/shaders/glsl");
const read=n=>fs.readFileSync(path.join(D,n+".glsl"),"utf8");
let src=read("simVelocity.frag");
src=src.replace(/#include "([^"]+)"/g,(_,n)=>read(n));
// preámbulo que antepone GPUComputationRenderer
const full=`#define resolution vec2(256.0,256.0)\nuniform sampler2D texturePosition;\nuniform sampler2D textureVelocity;\n`+src;
const { parser } = require("@shaderfrog/glsl-parser");
try { parser.parse(full); console.log("✓ simVelocity + fields: GLSL sintácticamente válido"); }
catch(e){ console.error("✗ ERROR GLSL:", e.message); process.exit(1); }
// y el fragment de render
try { const f=read("render.frag").replace(/#include "([^"]+)"/g,(_,n)=>read(n));
  parser.parse("precision highp float;\n"+f); console.log("✓ render.frag: válido"); }
catch(e){ console.error("✗ ERROR render.frag:", e.message); process.exit(1); }
