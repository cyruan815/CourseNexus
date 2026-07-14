import { HandoutMarkdownRenderer } from "../features/generated-content/renderers/handout/HandoutMarkdownRenderer";
import { handoutPreviewMarkdown } from "../features/generated-content/renderers/handout/handoutMock";

export function HandoutPreviewPage() {
  return (
    <main className="handout-preview-page">
      <section className="handout-preview-shell">
        <div className="handout-preview-kicker">雾霾蓝 × 鼠尾草绿</div>
        <HandoutMarkdownRenderer markdown={handoutPreviewMarkdown} />
      </section>
    </main>
  );
}
