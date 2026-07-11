import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { HomePage } from "../../src/pages/HomePage";

function renderHomePage() {
  render(
    <MantineProvider>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </MantineProvider>,
  );
}

describe("HomePage", () => {
  it("renders the static course workbench from the homepage prototype", () => {
    renderHomePage();

    expect(screen.getByRole("heading", { name: "课程学习助手 Agent 平台" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "今日待办" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "日历" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "课程概览" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "计算机网络" })).toHaveAttribute("href", "/courses/computer-network");
    expect(screen.getByText("还没有学习计划")).toBeInTheDocument();
    expect(screen.getByText("添加课程")).toBeInTheDocument();
  });
});
