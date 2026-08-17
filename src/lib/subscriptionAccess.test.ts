import { describe, expect, it } from "vitest";
import {
  canAccessTrialSurfaces,
  daysRemaining,
  isFullAccess,
  isTrialAccess,
  planDisplayName,
  resolvePostAuthPath,
} from "@/lib/subscriptionAccess";

describe("subscriptionAccess", () => {
  it("maps access levels", () => {
    expect(isFullAccess("full")).toBe(true);
    expect(isFullAccess("trial")).toBe(false);
    expect(isTrialAccess("trial")).toBe(true);
    expect(canAccessTrialSurfaces("trial")).toBe(true);
    expect(canAccessTrialSurfaces("full")).toBe(true);
    expect(canAccessTrialSurfaces("none")).toBe(false);
  });

  it("maps plan display names from catalog ids", () => {
    expect(planDisplayName("start")).toBe("Start");
    expect(planDisplayName("pro")).toBe("Pro");
    expect(planDisplayName(null)).toBe("—");
  });

  it("routes post-auth by access level", () => {
    expect(resolvePostAuthPath("full")).toBe("/dashboard");
    expect(resolvePostAuthPath("trial")).toBe("/dashboard");
    expect(resolvePostAuthPath("none")).toBe("/trial");
    expect(resolvePostAuthPath()).toBe("/trial");
  });

  it("computes trial days remaining", () => {
    const inThreeDays = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString();
    expect(daysRemaining(inThreeDays)).toBeGreaterThanOrEqual(3);
    expect(daysRemaining(null)).toBeNull();
  });
});
