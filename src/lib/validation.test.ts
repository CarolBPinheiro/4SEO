import { describe, it, expect } from "vitest";
import {
  urlSchema,
  siteCreateSchema,
  siteUpdateSchema,
  getPasswordStrength,
  isValidUrl,
  validateSiteCreate,
  validateSiteUpdate,
} from "@/lib/validation";

describe("urlSchema", () => {
  it("should accept valid HTTPS URLs", () => {
    expect(() => urlSchema.parse("https://example.com")).not.toThrow();
    expect(() => urlSchema.parse("https://www.example.com/path")).not.toThrow();
    expect(() => urlSchema.parse("https://subdomain.example.com")).not.toThrow();
  });

  it("should accept valid HTTP URLs", () => {
    expect(() => urlSchema.parse("http://example.com")).not.toThrow();
  });

  it("should reject invalid URLs", () => {
    expect(() => urlSchema.parse("not-a-url")).toThrow();
    expect(() => urlSchema.parse("ftp://example.com")).toThrow();
    expect(() => urlSchema.parse("")).toThrow();
    expect(() => urlSchema.parse("example.com")).toThrow();
  });

  it("should reject URLs that are too short", () => {
    expect(() => urlSchema.parse("http://a")).toThrow();
  });
});

describe("siteCreateSchema", () => {
  it("should validate correct site data", () => {
    const result = siteCreateSchema.safeParse({
      baseUrl: "https://example.com",
      platform: "shopify",
    });
    expect(result.success).toBe(true);
  });

  it("should allow optional platform", () => {
    const result = siteCreateSchema.safeParse({
      baseUrl: "https://example.com",
    });
    expect(result.success).toBe(true);
  });

  it("should reject invalid platform", () => {
    const result = siteCreateSchema.safeParse({
      baseUrl: "https://example.com",
      platform: "invalid-platform",
    });
    expect(result.success).toBe(false);
  });
});

describe("siteUpdateSchema", () => {
  it("should allow partial updates", () => {
    expect(siteUpdateSchema.safeParse({ platform: "vtex" }).success).toBe(true);
    expect(siteUpdateSchema.safeParse({ baseUrl: "https://new.com" }).success).toBe(true);
    expect(siteUpdateSchema.safeParse({}).success).toBe(true);
  });
});

describe("getPasswordStrength", () => {
  it("should return weak for short passwords", () => {
    expect(getPasswordStrength("abc").label).toBe("Fraca");
  });

  it("should return medium for moderate passwords", () => {
    expect(getPasswordStrength("Password1").label).toBe("Média");
  });

  it("should return strong for complex passwords", () => {
    expect(getPasswordStrength("MyP@ssw0rd123!").label).toBe("Forte");
  });
});

describe("isValidUrl", () => {
  it("should return true for valid URLs", () => {
    expect(isValidUrl("https://example.com")).toBe(true);
    expect(isValidUrl("http://test.org/path")).toBe(true);
  });

  it("should return false for invalid URLs", () => {
    expect(isValidUrl("not-a-url")).toBe(false);
    expect(isValidUrl("")).toBe(false);
    expect(isValidUrl("ftp://test.com")).toBe(false);
  });
});

describe("validateSiteCreate", () => {
  it("should return data for valid input", () => {
    const result = validateSiteCreate({
      baseUrl: "https://shop.example.com",
      platform: "lojaintegrada",
    });
    
    expect("data" in result).toBe(true);
    if ("data" in result) {
      expect(result.data.baseUrl).toBe("https://shop.example.com");
      expect(result.data.platform).toBe("lojaintegrada");
    }
  });

  it("should return error for invalid input", () => {
    const result = validateSiteCreate({
      baseUrl: "invalid",
    });
    
    expect("error" in result).toBe(true);
  });
});

describe("validateSiteUpdate", () => {
  it("should return data for valid partial update", () => {
    const result = validateSiteUpdate({
      platform: "nuvemshop",
    });
    
    expect("data" in result).toBe(true);
    if ("data" in result) {
      expect(result.data.platform).toBe("nuvemshop");
    }
  });

  it("should return error for invalid URL", () => {
    const result = validateSiteUpdate({
      baseUrl: "not-valid",
    });
    
    expect("error" in result).toBe(true);
  });
});
