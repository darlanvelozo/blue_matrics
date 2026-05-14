import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "../button";

describe("Button", () => {
  it("renders text", () => {
    render(<Button>Enviar</Button>);
    expect(screen.getByRole("button", { name: "Enviar" })).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const user = userEvent.setup();
    const handle = vi.fn();
    render(<Button onClick={handle}>Click</Button>);
    await user.click(screen.getByRole("button"));
    expect(handle).toHaveBeenCalledTimes(1);
  });

  it("is disabled when disabled prop is true", () => {
    render(<Button disabled>X</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
