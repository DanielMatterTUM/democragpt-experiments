const fs = require('fs');
const puppeteer = require('/home/hermes/tmp/verify-browser/node_modules/puppeteer');

const [inMd, outPdf] = process.argv.slice(2);
if (!inMd || !outPdf) { console.error('usage: node md2pdf.js in.md out.pdf'); process.exit(1); }

const md = fs.readFileSync(inMd, 'utf8');

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Minimal but table-aware markdown -> HTML (enough for our reports).
function convert(src) {
  const lines = src.split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

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
      let h = '<table><thead><tr>' + head.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr></thead><tbody>';
      for (const r of rows) h += '<tr>' + r.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>';
      h += '</tbody></table>';
      out.push(h);
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
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return s;
}

const css = `
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
body {
  font-family: "DejaVu Sans", Helvetica, Arial, sans-serif;
  font-size: 9.4pt; line-height: 1.45; color: #1a1a1a; margin: 0;
}
h1 { font-size: 17pt; margin: 0 0 2mm 0; color: #14304f; border-bottom: 2px solid #14304f; padding-bottom: 2mm; }
h2 { font-size: 12.5pt; margin: 7mm 0 2mm 0; color: #14304f; page-break-after: avoid; }
h3 { font-size: 10.5pt; margin: 5mm 0 1.5mm 0; color: #2c5578; page-break-after: avoid; }
p { margin: 0 0 2.4mm 0; text-align: justify; }
ul, ol { margin: 0 0 2.6mm 0; padding-left: 5.5mm; }
li { margin-bottom: 1.1mm; }
table {
  border-collapse: collapse; width: 100%; margin: 2.5mm 0 4mm 0;
  font-size: 8.2pt; page-break-inside: avoid;
}
th { background: #14304f; color: #fff; text-align: left; padding: 1.5mm 1.8mm; font-weight: 600; }
td { padding: 1.3mm 1.8mm; border-bottom: 0.4pt solid #ccd6e0; }
tr:nth-child(even) td { background: #f4f7fa; }
code {
  font-family: "DejaVu Sans Mono", monospace; font-size: 8pt;
  background: #eef2f6; padding: 0.4mm 1mm; border-radius: 1.5pt;
}
pre {
  background: #f4f7fa; border-left: 2.5pt solid #14304f; padding: 2.4mm 3mm;
  white-space: pre-wrap; word-break: break-word; font-size: 7.4pt;
  page-break-inside: avoid; margin: 2mm 0 3mm 0;
}
blockquote { border-left: 2.5pt solid #b8c6d4; margin: 2mm 0; padding: 1.5mm 0 1.5mm 3mm; color: #444; }
hr { border: none; border-top: 0.5pt solid #ccd6e0; margin: 5mm 0; }
a { color: #14304f; }
.small { font-size: 8pt; color: #555; }
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
    headerTemplate: '<div></div>',
    footerTemplate:
      '<div style="width:100%;font-size:7pt;color:#888;text-align:center;' +
      'font-family:DejaVu Sans,Arial;padding-top:3mm;">' +
      '<span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: { top: '14mm', bottom: '16mm', left: '14mm', right: '14mm' },
  });
  await browser.close();
  console.log('wrote ' + outPdf);
})();
