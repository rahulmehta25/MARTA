import type { ExportFormat } from '@/types';

export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  filename: string,
  columns?: (keyof T)[]
): void {
  if (data.length === 0) return;

  const keys = columns || (Object.keys(data[0]) as (keyof T)[]);

  const csvContent = [
    keys.join(','),
    ...data.map((row) =>
      keys
        .map((key) => {
          const value = row[key];
          if (value === null || value === undefined) return '';
          if (typeof value === 'string' && value.includes(',')) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return String(value);
        })
        .join(',')
    ),
  ].join('\n');

  downloadFile(csvContent, `${filename}.csv`, 'text/csv');
}

export function exportToJSON<T>(data: T[], filename: string): void {
  const jsonContent = JSON.stringify(data, null, 2);
  downloadFile(jsonContent, `${filename}.json`, 'application/json');
}

function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function formatDateForExport(date: Date): string {
  return date.toISOString().split('T')[0];
}

export function generateExportFilename(prefix: string, dateRange?: { start: Date; end: Date }): string {
  const timestamp = new Date().toISOString().slice(0, 10);
  if (dateRange) {
    return `${prefix}_${formatDateForExport(dateRange.start)}_to_${formatDateForExport(dateRange.end)}`;
  }
  return `${prefix}_${timestamp}`;
}
