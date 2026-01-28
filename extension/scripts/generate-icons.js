/**
 * Icon generation script
 * Run with: node scripts/generate-icons.js
 *
 * For production, create proper PNG icons at these sizes:
 * - icon16.png (16x16)
 * - icon32.png (32x32)
 * - icon48.png (48x48)
 * - icon128.png (128x128)
 *
 * You can use the icon.svg as a base and convert with tools like:
 * - ImageMagick: convert icon.svg -resize 16x16 icon16.png
 * - Online tools like https://cloudconvert.com/svg-to-png
 */

const fs = require('fs');
const path = require('path');

// Create placeholder PNG files (1x1 blue pixel as base64)
// These should be replaced with actual icons
const placeholderPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
  'base64'
);

const sizes = [16, 32, 48, 128];
const iconsDir = path.join(__dirname, '..', 'public', 'icons');

sizes.forEach(size => {
  const filename = `icon${size}.png`;
  const filepath = path.join(iconsDir, filename);

  // Write placeholder (in production, generate proper sized icons)
  fs.writeFileSync(filepath, placeholderPng);
  console.log(`Created placeholder: ${filename}`);
});

console.log('\nNote: Replace these placeholders with properly sized PNG icons.');
console.log('Use the icon.svg as a reference and convert to PNG at each size.');
