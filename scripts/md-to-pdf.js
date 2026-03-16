#!/usr/bin/env node
/**
 * Convert Markdown to styled PDF using pdfkit (no browser needed).
 * Usage: node md-to-pdf.js <input.md> [output.pdf]
 */

const fs = require('fs');
const { marked } = require('marked');
const PDFDocument = require('pdfkit');

const inputFile = process.argv[2];
if (!inputFile) {
  console.error('Usage: node md-to-pdf.js <input.md> [output.pdf]');
  process.exit(1);
}

const outputFile = process.argv[3] || inputFile.replace(/\.md$/, '.pdf');
const md = fs.readFileSync(inputFile, 'utf8');
const tokens = marked.lexer(md);

const doc = new PDFDocument({
  size: 'A4',
  margins: { top: 50, bottom: 50, left: 45, right: 45 },
  bufferPages: true,
  info: {
    Title: 'mRNA Therapeutics Weekly Report',
    Author: 'OpenClaw Scientific Assistant'
  }
});

doc.pipe(fs.createWriteStream(outputFile));

const PAGE_WIDTH = 595.28 - 90; // A4 width minus margins
const COLORS = {
  heading1: '#1a1a2e',
  heading2: '#16537e',
  heading3: '#1e40af',
  body: '#2d2d2d',
  link: '#2563eb',
  accent: '#e74c3c',
  muted: '#777777',
  line: '#cccccc',
  star: '#f59e0b'
};

function cleanText(text) {
  return (text || '')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#x[0-9a-fA-F]+;/g, ' ')
    .replace(/<\/?[^>]+>/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function ensureSpace(needed = 60) {
  if (doc.y + needed > doc.page.height - doc.page.margins.bottom) {
    doc.addPage();
  }
}

function renderInlineText(text, baseOptions = {}) {
  // Process bold, italic, links, code spans
  const segments = [];
  let remaining = text;
  
  // Simple regex-based inline parsing
  const patterns = [
    { regex: /\*\*(.+?)\*\*/g, style: { bold: true } },
    { regex: /\*(.+?)\*/g, style: { italic: true } },
    { regex: /`(.+?)`/g, style: { code: true } },
    { regex: /\[([^\]]+)\]\(([^)]+)\)/g, style: { link: true } },
  ];
  
  // For simplicity, strip markdown formatting and render as plain styled text
  let clean = remaining
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`(.+?)`/g, '$1');
  
  clean = cleanText(clean);
  
  if (clean) {
    doc.fontSize(baseOptions.fontSize || 10)
       .fillColor(baseOptions.color || COLORS.body)
       .font(baseOptions.bold ? 'Helvetica-Bold' : baseOptions.italic ? 'Helvetica-Oblique' : 'Helvetica')
       .text(clean, {
         width: baseOptions.width || PAGE_WIDTH,
         align: baseOptions.align || 'left',
         indent: baseOptions.indent || 0,
         lineGap: 3
       });
  }
}

function renderTokens(tokens) {
  for (const token of tokens) {
    switch (token.type) {
      case 'heading': {
        const text = cleanText(token.text);
        ensureSpace(token.depth <= 2 ? 50 : 35);
        
        if (token.depth === 1) {
          doc.moveDown(0.5);
          doc.fontSize(22).font('Helvetica-Bold').fillColor(COLORS.heading1).text(text, { width: PAGE_WIDTH });
          doc.moveDown(0.2);
          doc.moveTo(doc.page.margins.left, doc.y)
             .lineTo(doc.page.margins.left + PAGE_WIDTH, doc.y)
             .lineWidth(1.5).strokeColor(COLORS.heading2).stroke();
          doc.moveDown(0.5);
        } else if (token.depth === 2) {
          doc.moveDown(0.8);
          // Emoji prefix detection
          const emoji = text.match(/^[^\w\s]/u)?.[0] || '';
          doc.fontSize(16).font('Helvetica-Bold').fillColor(COLORS.heading2).text(text, { width: PAGE_WIDTH });
          doc.moveDown(0.1);
          doc.moveTo(doc.page.margins.left, doc.y)
             .lineTo(doc.page.margins.left + PAGE_WIDTH, doc.y)
             .lineWidth(0.5).strokeColor(COLORS.line).stroke();
          doc.moveDown(0.4);
        } else if (token.depth === 3) {
          doc.moveDown(0.5);
          doc.fontSize(12.5).font('Helvetica-Bold').fillColor(COLORS.heading3).text(text, { width: PAGE_WIDTH });
          doc.moveDown(0.3);
        } else {
          doc.moveDown(0.3);
          doc.fontSize(11).font('Helvetica-Bold').fillColor(COLORS.body).text(text, { width: PAGE_WIDTH });
          doc.moveDown(0.2);
        }
        break;
      }

      case 'paragraph': {
        const text = cleanText(token.text || token.raw || '');
        if (!text) break;
        ensureSpace(30);
        renderInlineText(token.text || token.raw, { fontSize: 10, color: COLORS.body });
        doc.moveDown(0.4);
        break;
      }

      case 'list': {
        for (const item of token.items) {
          ensureSpace(25);
          const text = cleanText(item.text || item.raw || '');
          if (!text) continue;
          const bulletX = doc.page.margins.left;
          const textX = doc.page.margins.left + 15;
          
          doc.fontSize(10).font('Helvetica').fillColor(COLORS.body)
             .text('•', bulletX, doc.y, { continued: false });
          doc.moveUp();
          doc.text(text, textX, doc.y, { width: PAGE_WIDTH - 15, lineGap: 3 });
          doc.moveDown(0.2);
        }
        doc.moveDown(0.3);
        break;
      }

      case 'blockquote': {
        ensureSpace(30);
        const startY = doc.y;
        const text = token.tokens ? 
          token.tokens.map(t => cleanText(t.text || t.raw || '')).join(' ') :
          cleanText(token.text || '');
        
        doc.fontSize(9.5).font('Helvetica-Oblique').fillColor(COLORS.muted)
           .text(text, doc.page.margins.left + 12, doc.y, { width: PAGE_WIDTH - 12, lineGap: 2 });
        
        // Left border
        const endY = doc.y;
        doc.moveTo(doc.page.margins.left + 4, startY)
           .lineTo(doc.page.margins.left + 4, endY)
           .lineWidth(2).strokeColor(COLORS.heading2).stroke();
        doc.moveDown(0.4);
        break;
      }

      case 'hr': {
        doc.moveDown(0.3);
        doc.moveTo(doc.page.margins.left, doc.y)
           .lineTo(doc.page.margins.left + PAGE_WIDTH, doc.y)
           .lineWidth(1).strokeColor(COLORS.line).stroke();
        doc.moveDown(0.5);
        break;
      }

      case 'space':
        doc.moveDown(0.3);
        break;
    }
  }
}

// Render
renderTokens(tokens);

// Footer on each page
const pages = doc.bufferedPageRange();
for (let i = 0; i < pages.count; i++) {
  doc.switchToPage(i);
  doc.fontSize(8).font('Helvetica').fillColor(COLORS.muted)
     .text(
       `mRNA Therapeutics Weekly Report — Page ${i + 1} of ${pages.count}`,
       doc.page.margins.left,
       doc.page.height - 35,
       { width: PAGE_WIDTH, align: 'center' }
     );
}

doc.end();
console.log(`PDF generated: ${outputFile}`);
