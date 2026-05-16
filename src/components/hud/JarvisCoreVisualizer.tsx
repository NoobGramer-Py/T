import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { VisualizerMode } from "../../store";

// ── JARVIS Blue palette ────────────────────────────────────────────────────────
const C_BRIGHT  = 0xa0f4ff;   // ice-white cyan
const C_CYAN    = 0x00d4ff;   // primary JARVIS blue
const C_DEEP    = 0x0088cc;   // deep arc blue
const C_DARKER  = 0x004488;   // dark indigo

const RING_CONFIGS = [
  { r: 1.0, tube: 0.008, col: C_BRIGHT, spd:  0.50, tilt: [0,              0, 0] as [number,number,number] },
  { r: 1.35,tube: 0.005, col: C_CYAN,   spd: -0.36, tilt: [Math.PI / 5,    0, 0] as [number,number,number] },
  { r: 1.65,tube: 0.007, col: C_DEEP,   spd:  0.26, tilt: [Math.PI / 3,    0, 0] as [number,number,number] },
  { r: 1.95,tube: 0.004, col: C_CYAN,   spd: -0.18, tilt: [Math.PI / 2,    0, 0] as [number,number,number] },
  { r: 2.35,tube: 0.006, col: C_DEEP,   spd:  0.13, tilt: [Math.PI * 0.62, 0, 0] as [number,number,number] },
  { r: 2.75,tube: 0.003, col: C_BRIGHT, spd: -0.09, tilt: [Math.PI * 0.78, 0, 0] as [number,number,number] },
];

const PARTICLE_COUNT = 700;

function addMat(color: number, opacity: number) {
  return new THREE.MeshBasicMaterial({
    color, transparent: true, opacity,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
}

interface Props { mode: VisualizerMode; }

export function JarvisCoreVisualizer({ mode }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const modeRef  = useRef<VisualizerMode>(mode);
  const frameRef = useRef<number>(0);

  useEffect(() => { modeRef.current = mode; }, [mode]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const W = container.clientWidth  || 320;
    const H = container.clientHeight || 400;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 100);
    camera.position.z = 6;

    // Core icosahedron — wireframe blue
    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(0.5, 3),
      addMat(C_BRIGHT, 0.8)
    );
    (core.material as THREE.MeshBasicMaterial).wireframe = true;
    scene.add(core);

    // Inner solid glow core
    const innerCore = new THREE.Mesh(
      new THREE.SphereGeometry(0.22, 16, 16),
      addMat(C_BRIGHT, 0.55)
    );
    scene.add(innerCore);

    // Halos — blue gradient
    const haloColors = [C_CYAN, C_CYAN, C_DEEP, C_DEEP, C_DARKER];
    const halos = haloColors.map((col, i) =>
      new THREE.Mesh(
        new THREE.SphereGeometry(0.5 + (i + 1) * 0.15, 16, 16),
        new THREE.MeshBasicMaterial({
          color: col, transparent: true,
          opacity: 0.055 - i * 0.009,
          side: THREE.BackSide,
          blending: THREE.AdditiveBlending, depthWrite: false,
        })
      )
    );
    halos.forEach(h => scene.add(h));

    // Orbit rings
    const rings = RING_CONFIGS.map(({ r, tube, col, spd, tilt }) => {
      const pivot = new THREE.Group();
      pivot.rotation.set(...tilt);
      const ring = new THREE.Mesh(new THREE.TorusGeometry(r, tube, 8, 160), addMat(col, 0.90));
      const glow = new THREE.Mesh(new THREE.TorusGeometry(r, tube * 14, 8, 160), addMat(col, 0.06));
      pivot.add(ring, glow);
      scene.add(pivot);
      return { pivot, spd };
    });

    // Arc reactor flat disc ring
    const arcDisc = new THREE.Mesh(
      new THREE.TorusGeometry(0.62, 0.018, 8, 64),
      addMat(C_CYAN, 0.75)
    );
    scene.add(arcDisc);

    // Particles — blue cloud
    const pArr  = new Float32Array(PARTICLE_COUNT * 3);
    const pData = Array.from({ length: PARTICLE_COUNT }, () => ({
      orb:   0.9 + Math.random() * 2.1,
      ang:   Math.random() * Math.PI * 2,
      spd:   (0.10 + Math.random() * 0.50) * (Math.random() > 0.5 ? 1 : -1),
      phase: Math.random() * Math.PI * 2,
      amp:   0.12 + Math.random() * 0.20,
    }));
    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute("position", new THREE.BufferAttribute(pArr, 3));
    const pMat = new THREE.PointsMaterial({
      color: C_CYAN, size: 0.022, transparent: true, opacity: 0.70,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    scene.add(new THREE.Points(pGeo, pMat));

    // Sparks — bright ice
    const sArr  = new Float32Array(180 * 3);
    const sData = Array.from({ length: 180 }, () => ({
      orb:   0.5 + Math.random() * 0.95,
      ang:   Math.random() * Math.PI * 2,
      spd:   (0.9 + Math.random() * 1.3) * (Math.random() > 0.5 ? 1 : -1),
      inc:   (Math.random() - 0.5) * Math.PI * 0.9,
    }));
    const sGeo = new THREE.BufferGeometry();
    sGeo.setAttribute("position", new THREE.BufferAttribute(sArr, 3));
    const sMat = new THREE.PointsMaterial({
      color: C_BRIGHT, size: 0.013, transparent: true, opacity: 0.85,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    scene.add(new THREE.Points(sGeo, sMat));

    // Pulse waves
    const pulses: { mesh: THREE.Mesh; s: number; o: number }[] = [];
    let pulseAccum = 0;
    const spawnPulse = () => {
      const mesh = new THREE.Mesh(
        new THREE.TorusGeometry(0.55, 0.010, 8, 64),
        addMat(C_CYAN, 0.75)
      );
      scene.add(mesh);
      pulses.push({ mesh, s: 1.0, o: 0.75 });
    };

    const onResize = () => {
      const w = container.clientWidth, h = container.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    let lastTs = 0;
    const coreRot = { x: 0, y: 0 };

    const tick = (ts: number) => {
      frameRef.current = requestAnimationFrame(tick);
      const t  = ts * 0.001;
      const dt = Math.min(t - lastTs, 0.05);
      lastTs   = t;

      const m    = modeRef.current;
      const mult = m === "speaking" ? 2.8 : m === "listening" ? 1.65 : 1.0;

      const breathe = 1 + Math.sin(t * 1.4) * 0.055;
      const flicker = 1 + Math.sin(t * 11.0) * 0.012 * (m !== "idle" ? 1 : 0);

      coreRot.x += dt * 0.24 * mult;
      coreRot.y += dt * 0.42 * mult;
      core.rotation.x = coreRot.x;
      core.rotation.y = coreRot.y;
      core.scale.setScalar(breathe * flicker);

      innerCore.scale.setScalar(breathe * mult * 0.6 + 0.4);
      (innerCore.material as THREE.MeshBasicMaterial).opacity = Math.min(0.55 * mult, 0.9);

      // Arc disc flat spin
      arcDisc.rotation.z += dt * 0.8 * mult;
      arcDisc.scale.setScalar(breathe);

      halos.forEach((h, i) => {
        h.scale.setScalar(breathe * mult * 0.45 + 0.55);
        (h.material as THREE.MeshBasicMaterial).opacity =
          Math.min((0.055 - i * 0.009) * mult, 0.20);
      });

      rings.forEach(({ pivot, spd }, i) => {
        pivot.rotation.z += spd * dt * mult;
        if (m === "speaking") {
          pivot.scale.setScalar(1 + Math.sin(t * 8 + i * 1.2) * 0.09);
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
      for (let i = 0; i < 180; i++) {
        const s = sData[i];
        s.ang += s.spd * dt * mult;
        sa[i * 3]     = Math.cos(s.ang) * Math.cos(s.inc) * s.orb;
        sa[i * 3 + 1] = Math.sin(s.inc) * s.orb;
        sa[i * 3 + 2] = Math.sin(s.ang) * Math.cos(s.inc) * s.orb;
      }
      sGeo.attributes.position.needsUpdate = true;

      const pulseInterval = m === "speaking" ? 0.55 : m === "listening" ? 1.1 : 2.4;
      pulseAccum += dt;
      if (pulseAccum >= pulseInterval) {
        pulseAccum = 0;
        spawnPulse();
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.s += dt * 2.0 * mult;
        p.o -= dt * 0.50 * mult;
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

  return <div ref={mountRef} style={{ width: "100%", height: "100%", minHeight: 300 }} />;
}
