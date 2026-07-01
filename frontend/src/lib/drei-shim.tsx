// drei-shim.tsx — Reemplaza los imports de @react-three/drei que usa Aithera.
// @react-three/drei@9.122.0 tiene un bug: faltan los archivos index.js / index.cjs.js
// en la raiz del paquete, lo que rompe la resolucion de Vite.
// Este shim implementa solo lo que el proyecto necesita (Gltf, useGLTF) usando
// @react-three/fiber + three.js directamente, sin depender de drei.

import { useRef, useEffect } from "react";
import { useLoader, useFrame } from "@react-three/fiber";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import * as THREE from "three";

// -----------------------------------------------------------------------------
// Gltf — carga un archivo .glb/.gltf y lo renderiza como <primitive>.
// API compatible con drei's <Gltf src={...} scale={...} position={...} />.
// -----------------------------------------------------------------------------

interface GltfProps {
  src: string;
  scale?: number | [number, number, number];
  position?: [number, number, number];
  rotation?: [number, number, number];
  [key: string]: unknown;
}

export function Gltf({ src, scale, position, rotation, ...rest }: GltfProps) {
  const gltf = useLoader(GLTFLoader, src);

  return (
    <primitive
      object={gltf.scene}
      scale={scale}
      position={position}
      rotation={rotation}
      {...rest}
    />
  );
}

// -----------------------------------------------------------------------------
// useGLTF — hook compatible con drei's useGLTF(path).
// Devuelve el objeto gltf (con .scene, .animations, etc.) y expone
// .preload(path) para precarga sin render.
// Implementacion: useLoader envuelve un GLTFLoader compartido; el preload
// simplemente dispara una carga con el mismo loader que queda cacheada.
// -----------------------------------------------------------------------------

const _gltfLoader = new GLTFLoader();

export function useGLTF(path: string) {
  return useLoader(GLTFLoader, path);
}

(useGLTF as unknown as { preload: (path: string) => void }).preload = (path: string) => {
  // Dispara una carga temprana para que cuando el componente llame
  // useLoader(GLTFLoader, path) ya este cacheada en el loader interno de R3F.
  _gltfLoader.load(path, () => {}, undefined, () => {});
};
