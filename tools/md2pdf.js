const fs = require('fs');
const puppeteer = require('/home/hermes/tmp/verify-browser/node_modules/puppeteer');

const [inMd, outPdf] = process.argv.slice(2);
if (!inMd || !outPdf) { console.error('usage: node md2pdf.js in.md out.pdf'); process.exit(1); }

const md = fs.readFileSync(inMd, 'utf8');
// Figures are referenced relative to the markdown file (results/REPORT.md ->
// results/figures/*.png). Resolve to absolute paths so Chromium finds them --
// relative paths in a data: URL context resolve against nothing and fail
// SILENTLY (empty img boxes).
const path = require('path');
const baseDir = path.dirname(path.resolve(inMd));

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function imgSrc(rel) {
  const abs = path.resolve(baseDir, rel);
  if (!fs.existsSync(abs)) {
    console.error('MISSING IMAGE: ' + abs);
    return '';
  }
  return 'data:image/png;base64,' + fs.readFileSync(abs).toString('base64');
}

// A cell is numeric if it parses as a number, a percentage, a decimal point
// value, or is an em/en-dash placeholder -- used to right-align columns.
function isNum(s) {
  const t = (s || '').trim();
  if (!t) return false;
  if (/^[–—-]+$/.test(t)) return true;
  return /^[-+]?[\d.,]+$/.test(t.replace(/[%$\s]/g, '')) && /\d/.test(t);
}

// Raw HTML passthrough for the few semantic blocks the converter doesn't know
// (abstract box, subtitle, keyword line). Only a small allowlist.
function raw(s) {
  if (/^<(div class="abstract"|div class="keyword"|p class="subtitle"|p class="authors"|hr)[\s>]/.test(s)) {
    return s;
  }
  return null;
}

// Minimal but table-aware markdown -> HTML (enough for our reports).
function convert(src) {
  const lines = src.split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // raw HTML passthrough (allowlisted) -- blocks may span several lines, e.g.
    // <div class="abstract"> ... </div>, so consume until the tag closes.
    if (/^<(div class="abstract"|div class="keyword")/.test(line.trim())) {
      const buf = [];
      let depth = 0;
      while (i < lines.length) {
        buf.push(lines[i]);
        depth += (lines[i].match(/<div\b/g) || []).length;
        depth -= (lines[i].match(/<\/div>/g) || []).length;
        i++;
        if (depth <= 0 && buf.some(l => /<\/div>/.test(l))) break;
      }
      // inline markdown inside the block (bold, quotes, code)
      let html = buf.map((l, k) => (k === 0 || k === buf.length - 1)
        ? l : inline(l)).join('\n');
      out.push(html);
      continue;
    }
    const r0 = raw(line.trim());
    if (r0) { out.push(r0); i++; continue; }

    // fenced code
    if (line.trim().startsWith('```')) {
      const body = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) { body.push(lines[i]); i++; }
      i++;
      out.push('<pre><code>' + esc(body.join('\n')) + '</code></pre>');
      continue;
    }

    // table: a header row followed by a separator row of dashes
    if (line.includes('|') && i + 1 < lines.length &&
        /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1])) {
      const cells = (r) => r.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(c => c.trim());
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        rows.push(cells(lines[i])); i++;
      }
      let h = '<table><thead><tr>' +
        head.map((c, i) => '<th' + (isNum(c) ? ' class="num"' : '') + '>' +
          inline(c) + '</th>').join('') + '</tr></thead><tbody>';
      for (const r of rows) {
        h += '<tr>' + r.map((c, i) =>
          '<td' + (isNum(c) || isNum(head[i]) ? ' class="num"' : '') + '>' +
          inline(c) + '</td>').join('') + '</tr>';
      }
      h += '</tbody></table>';
      out.push(h);
      continue;
    }

    // image + following italic line = figure with caption
    const img = line.trim().match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (img) {
      const src = imgSrc(img[2]);
      if (src) out.push('<figure><img src="' + src + '" alt="' + esc(img[1]) + '"></figure>');
      i++;
      // caption = the next non-empty line, rendered as <figcaption>
      while (i < lines.length && lines[i].trim() === '') i++;
      if (i < lines.length) {
        out.push('<figcaption>' + inline(lines[i].trim()) + '</figcaption>');
        i++;
      }
      continue;
    }

    // headings
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { out.push(`<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`); i++; continue; }

    // horizontal rule
    if (/^\s*---\s*$/.test(line)) { out.push('<hr>'); i++; continue; }

    // blockquote
    if (/^>\s?/.test(line)) {
      const b = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) { b.push(lines[i].replace(/^>\s?/, '')); i++; }
      out.push('<blockquote>' + convert(b.join('\n')) + '</blockquote>');
      continue;
    }

    // list
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      const ordered = /^\s*\d+\./.test(line);
      const items = [];
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*]|\d+\.)\s+/, '')); i++;
      }
      const tag = ordered ? 'ol' : 'ul';
      out.push('<' + tag + '>' + items.map(t => '<li>' + inline(t) + '</li>').join('') + '</' + tag + '>');
      continue;
    }

    // paragraph
    if (line.trim() === '') { i++; continue; }
    const p = [];
    while (i < lines.length && lines[i].trim() !== '' &&
           !lines[i].includes('|') &&
           !/^(#{1,6}\s|```|>|\s*([-*]|\d+\.)\s)/.test(lines[i])) {
      p.push(lines[i]); i++;
    }
    if (p.length) out.push('<p>' + inline(p.join(' ')) + '</p>');
    else i++;
  }
  return out.join('\n');
}

function inline(s) {
  s = esc(s);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold first, then italic. The italic pattern must not swallow a typographic
  // quote followed by a letter (e.g. '... auf den Keks" — i bin beim') -- require
  // a non-word, non-quote char before the opening asterisk.
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*\w„“"'])\*([^*]+?)\*(?![\w])/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return s;
}

const css = `
@page { size: A4; margin: 22mm 20mm 20mm 20mm; }
body {
  font-family: "Bitstream Charter", "Charter", "Liberation Serif", Georgia, serif;
  font-size: 10pt; line-height: 1.42; color: #111; margin: 0;
  text-rendering: optimizeLegibility; font-variant-numeric: oldstyle-nums;
  hyphens: auto;
}
h1 {
  font-size: 16pt; font-weight: 700; margin: 0 0 1mm 0; color: #000;
  letter-spacing: -0.01em; line-height: 1.18;
}
.subtitle { font-size: 10.5pt; color: #444; margin: 0 0 1mm 0; font-style: italic; }
.authors { font-size: 9pt; color: #333; margin: 2mm 0 0 0; }
h2 {
  font-size: 11.5pt; font-weight: 700; margin: 6.5mm 0 1.6mm 0; color: #000;
  page-break-after: avoid; letter-spacing: 0.01em;
}
h3 { font-size: 10.2pt; font-weight: 700; margin: 4.5mm 0 1.2mm 0; color: #1a1a1a;
     page-break-after: avoid; }
h4 { font-size: 9.6pt; font-weight: 600; margin: 3.5mm 0 1mm 0; color: #333;
     page-break-after: avoid; }
p { margin: 0 0 2.1mm 0; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 2.4mm 0; padding-left: 5mm; }
li { margin-bottom: 0.9mm; }
table {
  border-collapse: collapse; width: 100%; margin: 2mm 0 3.5mm 0;
  font-size: 8pt; page-break-inside: avoid;
  font-variant-numeric: tabular-nums lining-nums;
}
th {
  background: #ececec; color: #000; text-align: left; padding: 1.3mm 1.6mm;
  font-weight: 700; border-top: 0.7pt solid #444; border-bottom: 0.5pt solid #888;
}
td { padding: 1.1mm 1.6mm; border-bottom: 0.3pt solid #ccc; }
td.num, th.num { text-align: right; }
tr:last-child td { border-bottom: 0.5pt solid #888; }
table.tight { font-size: 7.2pt; }
code {
  font-family: "DejaVu Sans Mono", monospace; font-size: 7.6pt;
  background: #f0f0f0; padding: 0.3mm 0.9mm; border-radius: 1pt;
}
pre {
  background: #f7f7f7; border-left: 2pt solid #666; padding: 2.2mm 2.8mm;
  white-space: pre-wrap; word-break: break-word; font-size: 7.2pt;
  page-break-inside: avoid; margin: 2mm 0 3mm 0; line-height: 1.32;
}
blockquote {
  border-left: 2pt solid #bbb; margin: 2mm 0; padding: 1.2mm 0 1.2mm 2.6mm;
  color: #333; font-size: 9.2pt;
}
figure { margin: 3.5mm 0 1.5mm 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption {
  font-size: 8.2pt; color: #333; text-align: left; margin: 1.2mm 0 3.5mm 0;
  line-height: 1.34; page-break-inside: avoid;
}
hr { border: none; border-top: 0.4pt solid #bbb; margin: 5mm 0; }
a { color: #1a4a6e; text-decoration: none; }
.small { font-size: 8pt; color: #555; }
.abstract {
  background: #f6f7f8; border-left: 2.5pt solid #333; padding: 2.6mm 3mm;
  margin: 3mm 0 4mm 0; font-size: 9.2pt; page-break-inside: avoid;
}
.abstract h4 { margin-top: 0; }
.keyword { font-size: 8.6pt; color: #333; font-style: italic; margin: 1.5mm 0 0 0; }
`;

const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${css}</style></head>
<body>${convert(md)}</body></html>`;

(async () => {
  const browser = await puppeteer.launch({
    args: ['--no-sandbox', '--disable-gpu'],
  });
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  await page.pdf({
    path: outPdf, format: 'A4', printBackground: true,
    displayHeaderFooter: true,
    // thin running head + page number, like a journal preprint
    headerTemplate:
      '<div style="width:100%;font-size:6.6pt;color:#999;font-family:' +
      '"Bitstream Charter","Liberation Serif",serif;padding:0 20mm;' +
      'border-bottom:0.3pt solid #ddd;padding-bottom:1.5mm;">' +
      '<span>Reaktanz auf TikTok — Häufigkeit und Erkennungsgeschwindigkeit</span>' +
      '</div>',
    footerTemplate:
      '<div style="width:100%;font-size:7pt;color:#777;text-align:center;' +
      'font-family:"Bitstream Charter","Liberation Serif",serif;padding-top:3mm;">' +
      '<span class="pageNumber"></span></div>',
    margin: { top: '26mm', bottom: '16mm', left: '20mm', right: '20mm' },
  });
  await browser.close();
  console.log('wrote ' + outPdf);
})();
