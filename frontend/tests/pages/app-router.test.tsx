import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { setSessionToken } from "../../src/features/auth/session";
import { AppRouter } from "../../src/router/AppRouter";

describe("AppRouter", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.history.pushState({}, "", "/");
  });

  it("redirects anonymous users to login", () => {
    window.history.pushState({}, "", "/");

    render(<AppRouter />);

    expect(screen.getByRole("heading", { name: "登录 CourseNexus" })).toBeInTheDocument();
  });

  it("renders home for authenticated users", () => {
    setSessionToken("token-123");
    window.history.pushState({}, "", "/");

    render(<AppRouter />);

    expect(screen.getByRole("heading", { name: "CourseNexus" })).toBeInTheDocument();
    expect(screen.getByText("课程工作台")).toBeInTheDocument();
  });

  it("keeps login page public", () => {
    window.history.pushState({}, "", "/login");

    render(<AppRouter />);

    expect(screen.getByRole("heading", { name: "登录 CourseNexus" })).toBeInTheDocument();
  });
});
