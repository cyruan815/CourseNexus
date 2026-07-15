import { useEffect, useRef } from "react";

const PARTICLE_COLORS = ["#2F80ED", "#14B8A6", "#4F46E5", "#7C3AED"];
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const TAU = Math.PI * 2;

interface RingParticle {
  alpha: number;
  anchorDamping: number;
  anchorMaxSpeed: number;
  anchorSpring: number;
  anchorVx: number;
  anchorVy: number;
  anchorX: number;
  anchorY: number;
  angularVelocity: number;
  baseAngle: number;
  baseRadius: number;
  breathAmplitude: number;
  color: string;
  damping: number;
  flutter: number;
  flutterPhase: number;
  flutterSpeed: number;
  lateralAmplitude: number;
  lateralPhase: number;
  lateralSpeed: number;
  length: number;
  lineWidth: number;
  orientationOffset: number;
  radialDrift: number;
  radialPhase: number;
  radialSpeed: number;
  spring: number;
  vx: number;
  vy: number;
  x: number;
  y: number;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

function normalizeAngle(angle: number): number {
  return Math.atan2(Math.sin(angle), Math.cos(angle));
}

function createRingParticles(
  width: number,
  height: number,
  originX: number,
  originY: number,
): RingParticle[] {
  const diagonal = Math.hypot(width, height);
  const particleCount = clamp(Math.round((width * height) / 2_100), 520, 1_100);
  const minimumRadius = clamp(Math.min(width, height) * 0.06, 48, 82);
  const maximumRadius = diagonal * 0.64;
  const spokeCount = clamp(Math.round(diagonal / 19), 72, 128);

  return Array.from({ length: particleCount }, (_, index) => {
    const radialProgress = (index + Math.random()) / particleCount;
    const baseRadius = minimumRadius + radialProgress * (maximumRadius - minimumRadius);
    const spokeAngle = Math.floor(Math.random() * spokeCount) / spokeCount * TAU;
    const baseAngle = spokeAngle + (Math.random() - 0.5) * (TAU / spokeCount) * 0.32;
    const colorProgress = (baseAngle / TAU + radialProgress * 0.2) % 1;
    const colorIndex = Math.floor(colorProgress * PARTICLE_COLORS.length);

    return {
      alpha: 0.2 + Math.random() * 0.4 + (1 - radialProgress) * 0.1,
      anchorDamping: 0.92 + Math.random() * 0.045,
      anchorMaxSpeed: 0.35 + Math.random() * 0.5,
      anchorSpring: 0.00006 + Math.random() * 0.0001,
      anchorVx: 0,
      anchorVy: 0,
      anchorX: originX,
      anchorY: originY,
      angularVelocity: (Math.random() - 0.5) * 0.0000012,
      baseAngle,
      baseRadius,
      breathAmplitude: 0.09 + Math.random() * 0.14,
      color: PARTICLE_COLORS[colorIndex],
      damping: 0.955 + Math.random() * 0.025,
      flutter: 0.004 + Math.random() * 0.012,
      flutterPhase: Math.random() * TAU,
      flutterSpeed: 0.00022 + Math.random() * 0.00034,
      lateralAmplitude: 14 + Math.random() * (32 + radialProgress * 38),
      lateralPhase: Math.random() * TAU,
      lateralSpeed: 0.000045 + Math.random() * 0.00011,
      length: 2.8 + Math.random() * 5 + (1 - radialProgress) * 1.4,
      lineWidth: 0.8 + Math.random() * 1.05 + (1 - radialProgress) * 0.16,
      orientationOffset: (Math.random() - 0.5) * 0.34,
      radialDrift: 7 + Math.random() * 24,
      radialPhase: Math.random() * TAU,
      radialSpeed: 0.00007 + Math.random() * 0.00009,
      spring: 0.00065 + Math.random() * 0.0012,
      vx: 0,
      vy: 0,
      x: originX + Math.cos(baseAngle) * baseRadius,
      y: originY + Math.sin(baseAngle) * baseRadius,
    };
  });
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

      if (pointer.x === 0 && pointer.y === 0) {
        pointer.x = width / 2;
        pointer.y = height / 2;
      }

      particles = createRingParticles(width, height, pointer.x, pointer.y);
    }

    function updateAnchor(particle: RingParticle, delta: number) {
      particle.anchorVx += (pointer.x - particle.anchorX) * particle.anchorSpring * delta;
      particle.anchorVy += (pointer.y - particle.anchorY) * particle.anchorSpring * delta;

      const damping = Math.pow(particle.anchorDamping, delta);
      particle.anchorVx *= damping;
      particle.anchorVy *= damping;

      const speed = Math.hypot(particle.anchorVx, particle.anchorVy);

      if (speed > particle.anchorMaxSpeed) {
        particle.anchorVx = (particle.anchorVx / speed) * particle.anchorMaxSpeed;
        particle.anchorVy = (particle.anchorVy / speed) * particle.anchorMaxSpeed;
      }

      particle.anchorX += particle.anchorVx * delta;
      particle.anchorY += particle.anchorVy * delta;
    }

    function updateParticle(particle: RingParticle, time: number, delta: number) {
      updateAnchor(particle, delta);

      const globalBreath = Math.sin(time * 0.00022) * 0.035;
      const independentBreath = Math.sin(time * particle.radialSpeed + particle.radialPhase)
        * particle.breathAmplitude;
      const radius = particle.baseRadius * (1 + globalBreath + independentBreath)
        + Math.sin(time * particle.radialSpeed * 1.7 + particle.radialPhase * 1.31) * particle.radialDrift;
      const angle = particle.baseAngle
        + time * particle.angularVelocity
        + Math.sin(time * particle.flutterSpeed + particle.flutterPhase) * 0.022;
      const lateralOffset = Math.sin(time * particle.lateralSpeed + particle.lateralPhase)
        * particle.lateralAmplitude;
      const radialX = Math.cos(angle);
      const radialY = Math.sin(angle);
      const tangentX = -radialY;
      const tangentY = radialX;
      const targetX = particle.anchorX + radialX * radius + tangentX * lateralOffset;
      const targetY = particle.anchorY + radialY * radius + tangentY * lateralOffset;
      const flutterX = Math.sin(time * particle.flutterSpeed + particle.flutterPhase) * particle.flutter;
      const flutterY = Math.cos(time * particle.flutterSpeed * 0.79 + particle.flutterPhase * 1.7) * particle.flutter;

      particle.vx += ((targetX - particle.x) * particle.spring + flutterX) * delta;
      particle.vy += ((targetY - particle.y) * particle.spring + flutterY) * delta;

      const damping = Math.pow(particle.damping, delta);
      particle.vx *= damping;
      particle.vy *= damping;

      const speed = Math.hypot(particle.vx, particle.vy);
      const maximumSpeed = 2;

      if (speed > maximumSpeed) {
        particle.vx = (particle.vx / speed) * maximumSpeed;
        particle.vy = (particle.vy / speed) * maximumSpeed;
      }

      particle.x += particle.vx * delta;
      particle.y += particle.vy * delta;
    }

    function drawParticles(time: number, delta = 1, shouldUpdate = true) {
      context.clearRect(0, 0, width, height);
      context.lineCap = "round";

      particles.forEach((particle) => {
        if (shouldUpdate) {
          updateParticle(particle, time, delta);
        }

        if (particle.x < -12 || particle.x > width + 12 || particle.y < -12 || particle.y > height + 12) {
          return;
        }

        const radialAngle = Math.atan2(particle.y - particle.anchorY, particle.x - particle.anchorX);
        const radialOrientation = radialAngle + particle.orientationOffset
          + Math.sin(time * particle.flutterSpeed * 0.71 + particle.flutterPhase) * 0.12;
        const speed = Math.hypot(particle.vx, particle.vy);
        const velocityAngle = speed > 0.02 ? Math.atan2(particle.vy, particle.vx) : radialOrientation;
        const velocityInfluence = clamp(speed / 8, 0, 0.18);
        const orientation = radialOrientation
          + normalizeAngle(velocityAngle - radialOrientation) * velocityInfluence;
        const length = particle.length
          * (1 + Math.sin(time * particle.radialSpeed + particle.radialPhase) * 0.1);
        const halfLength = length / 2;
        const offsetX = Math.cos(orientation) * halfLength;
        const offsetY = Math.sin(orientation) * halfLength;

        context.beginPath();
        context.moveTo(particle.x - offsetX, particle.y - offsetY);
        context.lineTo(particle.x + offsetX, particle.y + offsetY);
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
      drawParticles(time, delta);
      animationFrame = window.requestAnimationFrame(animate);
    }

    function startAnimation() {
      if (
        reducedMotion.matches
        || document.visibilityState === "hidden"
        || typeof window.requestAnimationFrame !== "function"
        || animationFrame !== null
      ) {
        drawParticles(0, 1, false);
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
      const bounds = canvas.getBoundingClientRect();
      pointer.x = event.clientX - bounds.left;
      pointer.y = event.clientY - bounds.top;
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
