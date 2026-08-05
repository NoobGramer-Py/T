import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useTStore } from "../../store";

export function UltronCoreCanvas({ height = 280, width = "100%" }: { height?: number | string; width?: number | string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const visualizerMode = useTStore((s) => s.visualizerMode);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const W = container.clientWidth || 300;
    const H = container.clientHeight || 280;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
    camera.position.z = 6.5;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);

    container.appendChild(renderer.domElement);

    const C_RED    = 0xff0033;
    const C_CRIM   = 0x800016;
    const C_WHITE  = 0xffffff;
    const C_SILVER = 0xa0aab0;

    const M = (color: number, opacity: number, side = THREE.FrontSide) =>
      new THREE.MeshBasicMaterial({
        color, transparent: true, opacity, side,
        blending: THREE.AdditiveBlending, depthWrite: false,
      });

    // Nucleus & Geodesic Wireframe
    const innerNucleus = new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 32), M(C_WHITE, 0.8));
    scene.add(innerNucleus);

    const geoMesh = new THREE.Mesh(new THREE.IcosahedronGeometry(0.65, 2), M(C_RED, 0.65));
    geoMesh.material.wireframe = true;
    scene.add(geoMesh);

    const outerIcoMesh = new THREE.Mesh(new THREE.IcosahedronGeometry(0.95, 1), M(C_SILVER, 0.25));
    outerIcoMesh.material.wireframe = true;
    scene.add(outerIcoMesh);

    // Rings
    const RINGS = [
      { r: 1.15, tube: 0.010, col: C_WHITE, spd:  0.8, tilt: [0, 0, 0] },
      { r: 1.45, tube: 0.007, col: C_RED,   spd: -0.5, tilt: [Math.PI/4, 0, 0] },
      { r: 1.80, tube: 0.005, col: C_CRIM,  spd:  0.4, tilt: [Math.PI/3, Math.PI/6, 0] },
      { r: 2.15, tube: 0.008, col: C_RED,   spd: -0.3, tilt: [Math.PI*0.6, 0, 0] },
    ];

    const ringGroups = RINGS.map(({ r, tube, col, spd, tilt }) => {
      const pivot = new THREE.Group();
      pivot.rotation.set(tilt[0], tilt[1], tilt[2]);
      pivot.add(new THREE.Mesh(new THREE.TorusGeometry(r, tube, 12, 100), M(col, 0.85)));
      scene.add(pivot);
      return { pivot, spd };
    });

    // Particles
    const PC = 600;
    const pArr = new Float32Array(PC * 3);
    const pData = Array.from({ length: PC }, () => ({
      orb: 1.0 + Math.random() * 2.2,
      ang: Math.random() * Math.PI * 2,
      spd: (0.1 + Math.random() * 0.4) * (Math.random() > 0.5 ? 1 : -1),
      phase: Math.random() * Math.PI * 2,
      amp: 0.1 + Math.random() * 0.3,
    }));
    const pGeo = new THREE.BufferGeometry();
    pGeo.setAttribute("position", new THREE.BufferAttribute(pArr, 3));
    const pMesh = new THREE.Points(
      pGeo,
      new THREE.PointsMaterial({
        color: C_RED,
        size: 0.022,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    scene.add(pMesh);

    let animId: number;
    let last = 0;
    let rotX = 0, rotY = 0;

    const animate = (ts: number) => {
      animId = requestAnimationFrame(animate);
      const t = ts * 0.001;
      const dt = Math.min(t - last, 0.05);
      last = t;

      const speedMult = visualizerMode === "speaking" ? 2.5 : visualizerMode === "executing" ? 3.0 : visualizerMode === "listening" ? 2.0 : 1.0;

      rotX += dt * 0.2 * speedMult;
      rotY += dt * 0.35 * speedMult;

      geoMesh.rotation.set(rotX, rotY, 0);
      outerIcoMesh.rotation.set(-rotX * 0.5, -rotY * 0.4, 0);

      const breathe = 1 + Math.sin(t * 2 * speedMult) * 0.05;
      geoMesh.scale.setScalar(breathe);
      innerNucleus.scale.setScalar(0.85 + Math.sin(t * 3 * speedMult) * 0.1);

      ringGroups.forEach(({ pivot, spd }, i) => {
        pivot.rotation.z += spd * dt * speedMult;
        pivot.scale.setScalar(1 + Math.sin(t * 2 + i) * 0.02 * speedMult);
      });

      for (let i = 0; i < PC; i++) {
        const p = pData[i];
        p.ang += p.spd * dt * speedMult;
        pArr[i * 3] = Math.cos(p.ang) * p.orb;
        pArr[i * 3 + 1] = Math.sin(p.ang * 0.6 + p.phase) * p.orb * p.amp;
        pArr[i * 3 + 2] = Math.sin(p.ang) * p.orb;
      }
      pGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animId = requestAnimationFrame(animate);

    const handleResize = () => {
      if (!containerRef.current) return;
      const w = containerRef.current.clientWidth || 300;
      const h = containerRef.current.clientHeight || 280;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", handleResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [visualizerMode]);

  return (
    <div
      ref={containerRef}
      style={{
        width,
        height,
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    />
  );
}
