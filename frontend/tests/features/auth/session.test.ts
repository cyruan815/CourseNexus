import { afterEach, describe, expect, it } from "vitest";

import {
  TOKEN_STORAGE_KEY,
  clearSessionToken,
  getSessionToken,
  setSessionToken,
} from "../../../src/features/auth/session";

describe("auth session", () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it("stores bearer token in localStorage", () => {
    setSessionToken("token-123");

    expect(getSessionToken()).toBe("token-123");
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe("token-123");
  });

  it("clears stored token", () => {
    setSessionToken("token-123");

    clearSessionToken();

    expect(getSessionToken()).toBeNull();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
  });
});
