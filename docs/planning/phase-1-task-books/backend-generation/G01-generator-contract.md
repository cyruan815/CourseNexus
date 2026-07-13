# G01 Generator Contract - Simplified POC

The shared generation endpoint validates ownership and material scope, resolves one `MaterialGenerationContext`, rejects total-context overflow, invokes one independent generator, and persists one `AIGeneratedContent` record.

```python
class GeneratorOutput(BaseModel):
    title: str
    content: str | None = None
    content_json: dict[str, Any]

class Generator(Protocol):
    def generate(self, *, context: MaterialGenerationContext, parameters: dict[str, Any]) -> GeneratorOutput: ...
```

The five generators do not return chunk bindings. Success does not write `source_citations`. API compatibility keeps top-level `source_citations=[]`. Invalid parameters, no material, and oversized context do not create history; model and schema failures do.
