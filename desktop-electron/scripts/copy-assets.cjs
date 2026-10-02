const { copyFileSync, mkdirSync } = require('node:fs');
mkdirSync('.out/renderer', { recursive: true });
for (const name of ['index.html', 'styles.css']) copyFileSync(`renderer/${name}`, `.out/renderer/${name}`);
