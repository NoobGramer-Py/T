import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { VisualizerMode } from "../../store";

// ─── Constants ────────────────────────────────────────────────────────────────
const C_BRIGHT = 0xffe566;
const C_GOLD   = 0xffb300;
const C_ORANGE = 0xff6e00;
const C_DEEP   = 0xff4400;

const RING_CONFIGS = [
  { r: 1.0, tube: 0.009, col: C_BRIGHT, spd:  0.55, tilt: [0,              0, 0] as [number,number,number] },
  { r: 1.3, tube: 0.006, col: C_GOLD,   spd: -0.38, tilt: [Math.PI / 5,    0, 0] as [number,number,number] },
  { r: 1.6, tube: 0.008, col: C_ORANGE, spd:  0.28, tilt: [Math.PI / 3,    0, 0] as [number,number,number] },
  { r: 1.9, tube: 0.005, col: C_GOLD,   spd: -0.20, tilt: [Math.PI / 2,    0, 0] as [number,number,number] },
  { r: 2.3, tube: 0.007, col: C_ORANGE, spd:  0.15, tilt: [Math.PI * 0.62, 0, 0] as [number,number,number] },
  { r: 2.7, tube: 0.004, col: C_BRIGHT, spd: -0.10, tilt: [Math.PI * 0.78, 0, 0] as [number,number,number] },
];

const PARTICLE_COUNT = 600;

function buildAdditiveMat(color: number, opacity: number) {
  return new THREE.MeshBasicMaterial({
    color, transparent: true, opacity,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
}

interface Props {
  mode: VisualizerMode;
}

export function JarvisCoreVisualizer({ mode }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const modeRef  = useRef<VisualizerMode>(mode);
  const frameRef = useRef<number>(0);

  // Keep modeRef current without re-running the effect
  useEffect(() => { modeRef.current = mode; }, [mode]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const W = container.clientWidth  || 320;
    const H = container.clientHeight || 400;

    // ── Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // ── Scene / Camera
    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 100);
    camera.position.z = 6;

    // ── Core icosahedron
    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.5, 3),
      buildAdditiveMat(C_BRIGHT, 0.85)
    );
    (core.material as THREE.MeshBasicMaterial).wireframe = true;
    scene.add(core);

    // ── Halos
    const halos = Array.from({ length: 5 }, (_, i) =>
      new THREE.Mesh(
        new THREE.SphereGeometry(0.5 + (i + 1) * 0.14, 16, 16),
        new THREE.MeshBasicMaterial({
          color: i < 2 ? C_ORANGE : C_DEEP,
          transparent: true, opacity: 0.048 - i * 0.007,
          side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false,
        })
      )
    );
    halos.forEach(h => scene.add(h));

    // ── Rings
    const rings = RING_CONFIGS.map(({ r, tube, col, spd, tilt }) => {
      const pivot = new THREE.Group();
      pivot.rotation.set(...tilt);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(r, tube, 8, 160), buildAdditiveMat(col, 0.92));
      const glow = new THREE.Mesh(new THREE.TorusGeometry(r, tube * 12, 8, 160), buildAdditiveMat(col, 0.07));
      pivot.add(ring, glow);
      scene.add(pivot);
      return { pivot, spd };
    });

    // ── Particles
    const pArr  = new Float32Array(PARTICLE_COUNT * 3);
    const pData = Array.from({ length: PARTICLE_COUNT }, () => ({
      orb:   0.9 + Math.random() * 2.0,
      ang:   Math.random() * Math.PI * 2,
      spd:   (0.12 + Math.random() * 0.55) * (Math.random() > 0.5 ? 1 : -1),
      phase: Math.random() * Math.PI * 2,
      amp:   0.15 + Math.random() * 0.18,
    }));
    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute("position", new THREE.BufferAttribute(pArr, 3));
    const pMat = new THREE.PointsMaterial({
      color: C_GOLD, size: 0.025, transparent: true, opacity: 0.75,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    scene.add(new THREE.Points(pGeo, pMat));

    // ── Sparks
    const sArr  = new Float32Array(150 * 3);
    const sData = Array.from({ length: 150 }, () => ({
      orb:   0.5 + Math.random() * 0.9,
      ang:   Math.random() * Math.PI * 2,
      spd:   (0.8 + Math.random() * 1.2) * (Math.random() > 0.5 ? 1 : -1),
      inc:   (Math.random() - 0.5) * Math.PI * 0.8,
    }));
    const sGeo = new THREE.BufferGeometry();
    sGeo.setAttribute("position", new THREE.BufferAttribute(sArr, 3));
    const sMat = new THREE.PointsMaterial({
      color: C_BRIGHT, size: 0.015, transparent: true, opacity: 0.9,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    scene.add(new THREE.Points(sGeo, sMat));

    // ── Pulse rings
    const pulses: { mesh: THREE.Mesh; s: number; o: number }[] = [];
    let pulseAccum = 0;

    const spawnPulse = () => {
      const mesh = new THREE.Mesh(
        new THREE.TorusGeometry(0.52, 0.012, 8, 64),
        buildAdditiveMat(C_ORANGE, 0.8)
      );
      scene.add(mesh);
      pulses.push({ mesh, s: 1.0, o: 0.8 });
    };

    // ── Resize
    const onResize = () => {
      const w = container.clientWidth, h = container.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    // ── Animation loop
    let lastTs = 0;
    const coreRot = { x: 0, y: 0 };

    const tick = (ts: number) => {
      frameRef.current = requestAnimationFrame(tick);
      const t  = ts * 0.001;
      const dt = Math.min(t - lastTs, 0.05);
      lastTs   = t;

      const m    = modeRef.current;
      const mult = m === "speaking" ? 3.0 : m === "listening" ? 1.75 : 1.0;

      const breathe = 1 + Math.sin(t * 1.6) * 0.06;
      const flicker = 1 + Math.sin(t * 12.0) * 0.015 * (m !== "idle" ? 1 : 0);

      coreRot.x += dt * 0.28 * mult;
      coreRot.y += dt * 0.46 * mult;
      core.rotation.x = coreRot.x;
      core.rotation.y = coreRot.y;
      core.scale.setScalar(breathe * flicker);

      halos.forEach((h, i) => {
        h.scale.setScalar(breathe * mult * 0.5 + 0.5);
        (h.material as THREE.MeshBasicMaterial).opacity = Math.min((0.048 - i * 0.007) * mult, 0.22);
      });

      rings.forEach(({ pivot, spd }, i) => {
        pivot.rotation.z += spd * dt * mult;
        if (m === "speaking") {
          pivot.scale.setScalar(1 + Math.sin(t * 9 + i * 1.1) * 0.1);
        } else {
          pivot.scale.setScalar(1);
        }
      });

      const pa = pGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const p = pData[i];
        p.ang += p.spd * dt * mult;
        pa[i * 3]     = Math.cos(p.ang) * p.orb;
        pa[i * 3 + 1] = Math.sin(p.ang * 0.5 + p.phase) * p.orb * p.amp;
        pa[i * 3 + 2] = Math.sin(p.ang) * p.orb;
      }
      pGeo.attributes.position.needsUpdate = true;

      const sa = sGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < 150; i++) {
        const s = sData[i];
        s.ang += s.spd * dt * mult;
        sa[i * 3]     = Math.cos(s.ang) * Math.cos(s.inc) * s.orb;
        sa[i * 3 + 1] = Math.sin(s.inc) * s.orb;
        sa[i * 3 + 2] = Math.sin(s.ang) * Math.cos(s.inc) * s.orb;
      }
      sGeo.attributes.position.needsUpdate = true;

      const pulseInterval = m === "speaking" ? 0.6 : m === "listening" ? 1.2 : 2.5;
      pulseAccum += dt;
      if (pulseAccum >= pulseInterval) {
        pulseAccum = 0;
        spawnPulse();
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.s += dt * 2.2 * mult;
        p.o -= dt * 0.55 * mult;
        p.mesh.scale.setScalar(p.s);
        (p.mesh.material as THREE.MeshBasicMaterial).opacity = Math.max(0, p.o);
        if (p.o <= 0) {
          scene.remove(p.mesh);
          p.mesh.geometry.dispose();
          (p.mesh.material as THREE.MeshBasicMaterial).dispose();
          pulses.splice(i, 1);
        }
      }

      renderer.render(scene, camera);
    };

    frameRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={mountRef}
      style={{ width: "100%", height: "100%", minHeight: 300 }}
    />
  );
}
