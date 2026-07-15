import { useEffect, useRef } from "react";

const PARTICLE_COLORS = ["#2F80ED", "#14B8A6", "#4F46E5", "#7C3AED"];
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const TAU = Math.PI * 2;

interface RingParticle {
  alpha: number;
  angle: number;
  angularVelocity: number;
  color: string;
  length: number;
  lineWidth: number;
  phase: number;
  radius: number;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function createRingParticles(width: number, height: number): RingParticle[] {
  const diagonal = Math.hypot(width, height);
  const ringCount = clamp(Math.round(Math.min(width, height) / 44), 14, 24);
  const targetCount = clamp(Math.round((width * height) / 1_100), 320, 1_200);
  const minimumRadius = 38;
  const maximumRadius = diagonal * 0.88;
  const ringRadii = Array.from({ length: ringCount }, (_, index) => {
    const progress = index / Math.max(1, ringCount - 1);
    return minimumRadius + Math.pow(progress, 0.92) * (maximumRadius - minimumRadius);
  });
  const radiusTotal = ringRadii.reduce((total, radius) => total + radius, 0);
  const minimumParticlesPerRing = 18;
  const distributedParticleCount = Math.max(0, targetCount - minimumParticlesPerRing * ringCount);
  const particles: RingParticle[] = [];

  ringRadii.forEach((ringRadius, ringIndex) => {
    const ringParticleCount = minimumParticlesPerRing + Math.round((ringRadius / radiusTotal) * distributedParticleCount);
    const direction = ringIndex % 2 === 0 ? 1 : -1;

    for (let particleIndex = 0; particleIndex < ringParticleCount; particleIndex += 1) {
      const baseAngle = (particleIndex / ringParticleCount) * TAU;
      const angleJitter = (Math.random() - 0.5) * (TAU / ringParticleCount) * 0.3;
      const colorOffset = Math.floor((baseAngle / TAU) * PARTICLE_COLORS.length);

      particles.push({
        alpha: 0.22 + Math.random() * 0.42,
        angle: baseAngle + angleJitter,
        angularVelocity: direction * (0.000008 + Math.random() * 0.00001),
        color: PARTICLE_COLORS[(ringIndex + colorOffset) % PARTICLE_COLORS.length],
        length: 2.8 + Math.random() * 5.4,
        lineWidth: 0.8 + Math.random() * 1.2,
        phase: Math.random() * TAU,
        radius: ringRadius + (Math.random() - 0.5) * 11,
      });
    }
  });

  return particles;
}

export function WelcomeParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvasElement = canvasRef.current;

    if (!canvasElement) {
      return;
    }

    const drawingContext = canvasElement.getContext("2d");

    if (!drawingContext) {
      return;
    }

    const canvas: HTMLCanvasElement = canvasElement;
    const context: CanvasRenderingContext2D = drawingContext;
    const center = { x: 0, y: 0 };
    const pointer = { x: 0, y: 0 };
    const reducedMotion = window.matchMedia(REDUCED_MOTION_QUERY);
    let animationFrame: number | null = null;
    let height = 1;
    let lastTime = 0;
    let particles: RingParticle[] = [];
    let width = 1;

    function resizeCanvas() {
      const parentBounds = canvas.parentElement?.getBoundingClientRect();
      width = Math.max(1, Math.round(parentBounds?.width || window.innerWidth));
      height = Math.max(1, Math.round(parentBounds?.height || window.innerHeight));
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);

      canvas.width = Math.round(width * pixelRatio);
      canvas.height = Math.round(height * pixelRatio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      particles = createRingParticles(width, height);

      if (center.x === 0 && center.y === 0) {
        center.x = width / 2;
        center.y = height / 2;
        pointer.x = center.x;
        pointer.y = center.y;
      }
    }

    function drawParticles(time: number) {
      context.clearRect(0, 0, width, height);
      context.lineCap = "round";

      particles.forEach((particle) => {
        const angle = particle.angle + time * particle.angularVelocity;
        const radius = particle.radius + Math.sin(time * 0.00022 + particle.phase) * 2.4;
        const x = center.x + Math.cos(angle) * radius;
        const y = center.y + Math.sin(angle) * radius;

        if (x < -12 || x > width + 12 || y < -12 || y > height + 12) {
          return;
        }

        const tangent = angle + Math.PI / 2;
        const halfLength = particle.length / 2;
        const offsetX = Math.cos(tangent) * halfLength;
        const offsetY = Math.sin(tangent) * halfLength;

        context.beginPath();
        context.moveTo(x - offsetX, y - offsetY);
        context.lineTo(x + offsetX, y + offsetY);
        context.globalAlpha = particle.alpha;
        context.lineWidth = particle.lineWidth;
        context.strokeStyle = particle.color;
        context.stroke();
      });

      context.globalAlpha = 1;
    }

    function animate(time: number) {
      const delta = lastTime === 0 ? 1 : clamp((time - lastTime) / (1000 / 60), 0.5, 2);
      lastTime = time;
      const centerEase = 1 - Math.pow(0.978, delta);
      center.x += (pointer.x - center.x) * centerEase;
      center.y += (pointer.y - center.y) * centerEase;
      drawParticles(time);
      animationFrame = window.requestAnimationFrame(animate);
    }

    function startAnimation() {
      if (
        reducedMotion.matches ||
        document.visibilityState === "hidden" ||
        typeof window.requestAnimationFrame !== "function" ||
        animationFrame !== null
      ) {
        drawParticles(0);
        return;
      }

      lastTime = 0;
      animationFrame = window.requestAnimationFrame(animate);
    }

    function stopAnimation() {
      if (animationFrame !== null && typeof window.cancelAnimationFrame === "function") {
        window.cancelAnimationFrame(animationFrame);
      }
      animationFrame = null;
    }

    function handlePointerMove(event: PointerEvent) {
      pointer.x = event.clientX;
      pointer.y = event.clientY;
    }

    function handleMotionPreferenceChange() {
      stopAnimation();
      startAnimation();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "hidden") {
        stopAnimation();
      } else {
        startAnimation();
      }
    }

    resizeCanvas();
    const resizeObserver = new ResizeObserver(resizeCanvas);
    resizeObserver.observe(canvas.parentElement ?? canvas);
    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    document.addEventListener("visibilitychange", handleVisibilityChange);
    reducedMotion.addEventListener("change", handleMotionPreferenceChange);
    startAnimation();

    return () => {
      stopAnimation();
      resizeObserver.disconnect();
      window.removeEventListener("pointermove", handlePointerMove);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      reducedMotion.removeEventListener("change", handleMotionPreferenceChange);
    };
  }, []);

  return <canvas aria-hidden="true" className="auth-welcome__particles" ref={canvasRef} />;
}
