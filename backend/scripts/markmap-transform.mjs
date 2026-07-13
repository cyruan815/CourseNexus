import { Transformer } from 'markmap-lib';

let markdown = '';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) markdown += chunk;

try {
  const transformer = new Transformer();
  const { root, features } = transformer.transform(markdown);
  const assets = transformer.getUsedAssets(features);
  const serializableAssets = {
    styles: (assets.styles ?? []).filter((item) => item.type === 'style' || item.type === 'stylesheet'),
    scripts: (assets.scripts ?? []).filter((item) => item.type === 'script' && typeof item.data?.src === 'string'),
  };
  process.stdout.write(JSON.stringify({ root, features, assets: serializableAssets }));
} catch (error) {
  process.stderr.write(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
