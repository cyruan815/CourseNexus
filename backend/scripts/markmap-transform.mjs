import { Transformer } from 'markmap-lib';

let markdown = '';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) markdown += chunk;

try {
  const transformer = new Transformer();
  const { root, features } = transformer.transform(markdown);
  const assets = transformer.getUsedAssets(features);
  process.stdout.write(JSON.stringify({ root, features, assets }));
} catch (error) {
  process.stderr.write(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
