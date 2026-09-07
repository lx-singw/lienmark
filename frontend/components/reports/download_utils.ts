/**
 * Lienmark Report Deliverable Download Utilities (Sprint 6.3)
 * Client-side Blob generators and serializers for PDF, CSV, and JSON deliverables.
 * Authored strictly under Google AntiGravity: files <= 250 lines, functions <= 40 lines, zero any.
 */

import {
  CueSheetResponse,
  WrapChecklistResponse,
  ExceptionsScheduleData,
} from './types';

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function generateJsonBlob(data: unknown): Blob {
  const serialized = JSON.stringify(data, null, 2);
  return new Blob([serialized], { type: 'application/json;charset=utf-8;' });
}

export function generateCsvBlob(csvContent: string): Blob {
  return new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
}

function escapeCsvCell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '""';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return `"${str}"`;
}

export function generateCueSheetCsv(cueSheet: CueSheetResponse): string {
  const headers = [
    'CUE_NUMBER',
    'TITLE_OF_WORK',
    'USAGE',
    'TIMECODE_IN',
    'TIMECODE_OUT',
    'DURATION_SECONDS',
    'SCENE',
    'COMPOSERS',
    'PUBLISHERS',
    'PRO_WORK_ID',
    'RECORD_LABEL',
    'STATUS',
    'LINEAGE_KEY',
  ];

  const rows = cueSheet.cues.map((c) => {
    const compStr = c.composers
      .map((comp) => `${comp.name} (${comp.pro} ${comp.split_percentage}%)`)
      .join('; ');
    const pubStr = c.publishers
      .map((pub) => `${pub.name} (${pub.pro} ${pub.split_percentage}%)`)
      .join('; ');

    return [
      escapeCsvCell(c.cue_number),
      escapeCsvCell(c.title),
      escapeCsvCell(c.usage),
      escapeCsvCell(c.timecode_in),
      escapeCsvCell(c.timecode_out),
      escapeCsvCell(c.duration_seconds),
      escapeCsvCell(c.scene ?? ''),
      escapeCsvCell(compStr),
      escapeCsvCell(pubStr),
      escapeCsvCell(c.pro_work_id ?? ''),
      escapeCsvCell(c.record_label ?? ''),
      escapeCsvCell(c.status),
      escapeCsvCell(c.lineage_key),
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\r\n');
}

export function generateWrapChecklistCsv(wrap: WrapChecklistResponse): string {
  const headers = [
    'ITEM_ID',
    'CATEGORY',
    'TITLE',
    'DESCRIPTION',
    'STATUS',
    'BLOCKING_REASON',
    'LINEAGE_KEY',
  ];

  const rows = wrap.items.map((item) => {
    return [
      escapeCsvCell(item.item_id),
      escapeCsvCell(item.category),
      escapeCsvCell(item.title),
      escapeCsvCell(item.description),
      escapeCsvCell(item.status),
      escapeCsvCell(item.blocking_reason ?? ''),
      escapeCsvCell(item.lineage_key ?? ''),
    ].join(',');
  });

  return [headers.join(','), ...rows].join('\r\n');
}

export function generateExceptionsScheduleCsv(data: ExceptionsScheduleData): string {
  const headers = ['RECORD_TYPE', 'CLAIM_ID', 'TITLE', 'CATEGORY', 'STATUS_OR_RISK', 'DETAILS'];
  const clearedRows = data.cleared_claims.map((c) =>
    [
      escapeCsvCell('CLEARED'),
      escapeCsvCell(c.id),
      escapeCsvCell(c.title),
      escapeCsvCell(c.category),
      escapeCsvCell(c.status),
      escapeCsvCell(c.counsel_note ?? ''),
    ].join(',')
  );
  const exceptionRows = data.exception_claims.map((e) =>
    [
      escapeCsvCell('EXCEPTION'),
      escapeCsvCell(e.id),
      escapeCsvCell(e.title),
      escapeCsvCell(e.category),
      escapeCsvCell(e.risk_level),
      escapeCsvCell(`${e.reason} [Rule: ${e.policy_rule ?? 'None'}]`),
    ].join(',')
  );

  return [headers.join(','), ...clearedRows, ...exceptionRows].join('\r\n');
}

interface PdfSection {
  readonly title: string;
  readonly lines: ReadonlyArray<string>;
}

export function generateClientPdfBlob(
  documentTitle: string,
  sections: ReadonlyArray<PdfSection>
): Blob {
  const sanitize = (text: string) => text.replace(/[()\\]/g, '');
  let streamText = `BT /F1 16 Tf 50 750 Td (${sanitize(documentTitle)}) Tj ET\n`;
  let yPos = 720;

  for (const section of sections) {
    if (yPos < 80) break;
    streamText += `BT /F1 12 Tf 50 ${yPos} Td (${sanitize(section.title)}) Tj ET\n`;
    yPos -= 18;

    for (const line of section.lines) {
      if (yPos < 60) break;
      streamText += `BT /F1 9 Tf 60 ${yPos} Td (${sanitize(line)}) Tj ET\n`;
      yPos -= 14;
    }
    yPos -= 8;
  }

  const streamLen = streamText.length;
  const pdfBody = `%PDF-1.4
1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj
2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj
3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>> endobj
4 0 obj <</Length ${streamLen}>>
stream
${streamText}endstream
endobj
5 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000000300 00000 n 
trailer <</Size 6 /Root 1 0 R>>
startxref
380
%%EOF`;

  return new Blob([pdfBody], { type: 'application/pdf' });
}
