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
    // table: an optional caption line ("Table: ...") immediately above the
    // header row becomes a <caption>, as in a journal article.
    if (line.includes('|') && i + 1 < lines.length &&
        /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i + 1])) {
      const cells = (r) => r.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(c => c.trim());
      let cap = '';
      if (i > 0 && /^Table:\s*/.test(lines[i - 1].trim())) {
        cap = lines[i - 1].trim();
        i--;   // consume the caption line
      }
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
        rows.push(cells(lines[i])); i++;
      }
      let h = '<table>' +
        (cap ? '<caption>' + inline(cap.replace(/^Table:\s*/, 'Table ')) + '</caption>' : '') +
        '<thead><tr>' +
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
/* A4 article geometry: 210x297mm, margins as in a typical preprint template.
   The running head sits in the top margin, the page number in the bottom one. */
@page { size: A4; margin: 25mm 20mm 20mm 20mm; }
@page :first { margin: 22mm 20mm 20mm 20mm; }

body {
  font-family: "Nimbus Roman", "Liberation Serif", "Times New Roman", Times, serif;
  font-size: 10pt; line-height: 1.34; color: #000; margin: 0;
  text-align: justify; hyphens: auto; font-kerning: normal;
}
h1 {
  font-size: 15pt; font-weight: 700; margin: 0 0 2mm 0; color: #000;
  line-height: 1.2; letter-spacing: -0.005em; text-align: left;
}
.subtitle { font-size: 10pt; color: #333; margin: 0 0 1.5mm 0; font-style: italic;
            text-align: left; }
.authors { font-size: 9pt; color: #222; margin: 2.5mm 0 0 0; text-align: left;
           font-style: normal; }
h2 { font-size: 11pt; font-weight: 700; margin: 6mm 0 1.5mm 0; color: #000;
     text-align: left; page-break-after: avoid; }
h3 { font-size: 10pt; font-weight: 700; margin: 4.5mm 0 1mm 0; color: #000;
     text-align: left; page-break-after: avoid; }
h4 { font-size: 9.6pt; font-weight: 600; margin: 3.5mm 0 0.8mm 0; color: #222;
     text-align: left; page-break-after: avoid; }
p { margin: 0 0 0; text-align: justify; }
p + p { margin-top: 2mm; }
ul, ol { margin: 0 0 2.2mm 0; padding-left: 5mm; }
li { margin-bottom: 0.8mm; text-align: left; }
table {
  border-collapse: collapse; width: 100%; margin: 1.5mm 0 3mm 0;
  font-size: 7.8pt; page-break-inside: avoid; text-align: left;
}
caption { caption-side: top; font-size: 8.4pt; font-weight: 700; text-align: left;
          padding-bottom: 1mm; }
th {
  background: #ebebeb; color: #000; text-align: left; padding: 1.1mm 1.5mm;
  font-weight: 700; border-top: 0.8pt solid #333; border-bottom: 0.4pt solid #888;
}
td { padding: 0.9mm 1.5mm; border-bottom: 0.3pt solid #d0d0d0; }
td.num, th.num { text-align: right; }
tr:last-child td { border-bottom: 0.4pt solid #888; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 7.4pt;
       background: #f2f2f2; padding: 0.2mm 0.8mm; }
pre {
  background: #f7f7f7; border-left: 1.8pt solid #666; padding: 2mm 2.5mm;
  white-space: pre-wrap; word-break: break-word; font-size: 7pt;
  page-break-inside: avoid; margin: 1.5mm 0 2.5mm 0; line-height: 1.3;
}
blockquote { border-left: 1.8pt solid #bbb; margin: 1.5mm 0; padding: 1mm 0 1mm 2.4mm;
             color: #333; font-size: 9.4pt; text-align: left; }
figure { margin: 3mm 0 0 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 8pt; color: #222; text-align: left; margin: 1mm 0 3.5mm 0;
            line-height: 1.3; page-break-inside: avoid; }
hr { border: none; border-top: 0.4pt solid #bbb; margin: 4.5mm 0; }
a { color: #000; text-decoration: none; }
.small { font-size: 8pt; color: #444; }

/* front matter */
.abstract { margin: 4mm 0 0 0; font-size: 9.4pt; line-height: 1.36;
            text-align: justify; page-break-inside: avoid; }
.abstract h4 { margin: 0 0 1.2mm 0; font-size: 9.4pt; font-weight: 700; }
.keyword { font-size: 8.6pt; color: #222; font-style: italic; margin: 2mm 0 0 0;
           text-align: left; }
.rule { border-top: 0.8pt solid #000; margin: 3mm 0 2mm 0; }

/* references */
.refs { font-size: 8.6pt; line-height: 1.3; }
.refs div { margin-bottom: 1.2mm; text-align: left; padding-left: 5mm;
            text-indent: -5mm; }
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
