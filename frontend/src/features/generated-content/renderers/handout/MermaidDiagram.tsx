import { useEffect, useId, useState } from "react";

type MermaidRenderState =
  | { status: "loading" }
  | { status: "ready"; svg: string }
  | { status: "error" };

let mermaidRenderSequence = 0;

export function MermaidDiagram({ chart }: { chart: string }) {
  const reactId = useId();
  const renderId = `handout-mermaid-${reactId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const [state, setState] = useState<MermaidRenderState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });

    void (async () => {
      try {
        const { default: mermaid } = await import("mermaid");
        mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });
        const requestId = `${renderId}-${++mermaidRenderSequence}`;
        const { svg } = await mermaid.render(requestId, chart);
        if (active) setState({ status: "ready", svg });
      } catch {
        if (active) setState({ status: "error" });
      }
    })();

    return () => {
      active = false;
    };
  }, [chart, renderId]);

  if (state.status === "loading") {
    return (
      <div className="handout-mermaid handout-mermaid-loading" aria-live="polite">
        {"Mermaid \u56fe\u8868\u6e32\u67d3\u4e2d..."}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="handout-mermaid handout-mermaid-error" role="alert">
        <strong>{"Mermaid \u56fe\u8868\u6e32\u67d3\u5931\u8d25"}</strong>
        <pre>
          <code>{chart}</code>
        </pre>
      </div>
    );
  }

  return (
    <div
      className="handout-mermaid handout-mermaid-diagram"
      dangerouslySetInnerHTML={{ __html: state.svg }}
    />
  );
}
