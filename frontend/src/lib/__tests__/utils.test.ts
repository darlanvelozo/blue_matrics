import { describe, expect, it } from "vitest";
import { cn, formatCurrencyBRL, formatPercent } from "../utils";

describe("cn", () => {
  it("merges tailwind classes deduplicating conflicting ones", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
  it("handles falsy values", () => {
    expect(cn("a", false, undefined, "b")).toBe("a b");
  });
});

describe("formatCurrencyBRL", () => {
  it("formats integer to BRL without decimals", () => {
    const out = formatCurrencyBRL(1234);
    //   (NBSP) entre R$ e o número
    expect(out).toMatch(/^R\$\s?1\.234$/);
  });
});

describe("formatPercent", () => {
  it("formats fraction to percent string", () => {
    expect(formatPercent(0.124)).toBe("12,4%");
  });
});
