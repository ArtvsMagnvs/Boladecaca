// Permite importar los chunks GLSL como string crudo (Vite `?raw`).
declare module "*.glsl?raw" {
  const src: string;
  export default src;
}
