import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GeneratedContentRenderer } from "../../../src/features/generated-content/GeneratedContentRenderer";

const base = { generation_status: "success", content: null, content_json: null };

describe("GeneratedContentRenderer", () => {
  it("dispatches valid content and degrades malformed or unknown content", () => {
    const { rerender } = render(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "outline", content_json: { sections: [{ id: "sec_001", sort_order: 1, title: "Section", summary: "Summary", review_suggestion: "Review" }] } } as never} /></MantineProvider>);
    expect(screen.getByRole("heading", { name: "Section" })).toBeInTheDocument();
    rerender(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "quiz", content_json: { questions: "broken" } } as never} /></MantineProvider>);
    expect(screen.getByText("内容结构不可读取")).toBeInTheDocument();
    rerender(<MantineProvider><GeneratedContentRenderer content={{ ...base, content_type: "future_type", content: "Readable fallback" } as never} /></MantineProvider>);
    expect(screen.getByText("Readable fallback")).toBeInTheDocument();
  });
});
