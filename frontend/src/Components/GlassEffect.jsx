import React from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, MeshReflectorMaterial } from "@react-three/drei";

// Optional: Slow rotation for even more glassy vibes
function AnimatedGlassSphere() {
  const ref = React.useRef();
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.rotation.y = clock.getElapsedTime() * 0.35;
      ref.current.rotation.x = Math.sin(clock.getElapsedTime() * 0.2) * 0.12;
    }
  });
  return (
    <mesh ref={ref} position={[0, 0, 0]}>
      <sphereGeometry args={[1.4, 64, 64]} />
      <MeshReflectorMaterial
        color="#ffffff"
        blur={[80, 160]}
        mixBlur={1}
        reflectivity={1}
        transparent
        opacity={0.32}
        metalness={0.85}
        roughness={0.15}
        mirror={0.9}
        envMapIntensity={1.3}
      />
    </mesh>
  );
}

const GlassEffect = () => (
  <Canvas
    style={{
      position: "absolute",
      inset: 0,
      width: "100vw",
      height: "100vh",
      zIndex: 1,
      pointerEvents: "none", // lets you click UI below
    }}
    camera={{ position: [0, 0, 6.5], fov: 44 }}
  >
    <ambientLight intensity={1.4} />
    <directionalLight position={[2, 3, 7]} intensity={0.7} />
    <AnimatedGlassSphere />
    <Environment preset="city" />
  </Canvas>
);

export default GlassEffect;