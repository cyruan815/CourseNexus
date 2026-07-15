import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WelcomeParticleCanvas } from "../../../src/features/auth/WelcomeParticleCanvas";

describe("WelcomeParticleCanvas", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts one animation loop and cancels it when unmounted", () => {
    const requestAnimationFrame = vi.fn().mockReturnValue(17);
    const cancelAnimationFrame = vi.fn();
    vi.stubGlobal("requestAnimationFrame", requestAnimationFrame);
    vi.stubGlobal("cancelAnimationFrame", cancelAnimationFrame);

    const { unmount } = render(<WelcomeParticleCanvas />);

    expect(document.querySelector("canvas.auth-welcome__particles")).toBeInTheDocument();
    expect(requestAnimationFrame).toHaveBeenCalledTimes(1);

    unmount();

    expect(cancelAnimationFrame).toHaveBeenCalledWith(17);
  });

  it("renders a static field when reduced motion is requested", () => {
    const requestAnimationFrame = vi.fn().mockReturnValue(17);
    vi.stubGlobal("requestAnimationFrame", requestAnimationFrame);
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({
      matches: true,
      media: "(prefers-reduced-motion: reduce)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    render(<WelcomeParticleCanvas />);

    expect(requestAnimationFrame).not.toHaveBeenCalled();
  });
});
