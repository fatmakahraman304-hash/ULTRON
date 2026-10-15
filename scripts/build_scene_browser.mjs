// Render's Python-only service serves this deterministic bundled shared renderer.
import {build} from '../ultron/frontend/node_modules/esbuild/lib/main.js';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
await build({absWorkingDir:root,entryPoints:['ultron/frontend/src/spatial/browser.ts'],outfile:'ultron/cloud_service/static/scene-control.js',bundle:true,minify:true,format:'iife',target:'es2022',legalComments:'eof'});
await build({absWorkingDir:root,entryPoints:['ultron/frontend/src/spatial/intents.browser.ts'],outfile:'ultron/cloud_service/static/scene-intents.js',bundle:true,minify:true,format:'iife',target:'es2022',legalComments:'eof'});
