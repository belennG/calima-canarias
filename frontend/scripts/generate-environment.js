// Reads the repo's shared .env and writes src/app/environment.ts, so the browser
// bundle gets the ArcGIS API key without that key ever living in committed source.
// Runs automatically before `npm start` / `npm run build` (see package.json).

const fs = require('fs');
const path = require('path');

require('dotenv').config({ path: path.join(__dirname, '..', '..', '.env') });

const apiKey = process.env.ARCGIS_API_KEY;
if (!apiKey) {
  throw new Error('ARCGIS_API_KEY is not set in the repo .env - see .env.example');
}

const outPath = path.join(__dirname, '..', 'src', 'app', 'environment.ts');
fs.writeFileSync(outPath, `export const ARCGIS_API_KEY = '${apiKey}';\n`);
console.log('Generated src/app/environment.ts from the repo .env');
