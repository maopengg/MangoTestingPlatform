export const effectivenessPrintStyle = `
        @page { size: A4 landscape; margin: 0; }
        html, body {
          width: 297mm !important;
          min-width: 297mm !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: visible !important;
          background: var(--m-surface) !important;
        }
        #mango-effectiveness-report-image {
          display: flex !important;
          width: 297mm !important;
          max-width: 297mm !important;
          min-width: 297mm !important;
          margin: 0 !important;
          padding: 9mm 10mm 8mm !important;
          box-sizing: border-box !important;
          overflow: visible !important;
          flex-direction: column !important;
          gap: var(--m-page-gap, 8px) !important;
          border: 0 !important;
          background: var(--m-surface) !important;
          box-shadow: none !important;
          print-color-adjust: exact !important;
          -webkit-print-color-adjust: exact !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-paper-page,
        #mango-effectiveness-report-image .mango-effectiveness-module-quality__list,
        #mango-effectiveness-report-image .mango-effectiveness-module-quality__loading,
        #mango-effectiveness-report-image .arco-spin,
        #mango-effectiveness-report-image .mango-panel-spin__content {
          width: 100% !important;
          max-width: none !important;
          min-width: 0 !important;
          height: auto !important;
          max-height: none !important;
          overflow: visible !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-paper-page {
          margin: 0 !important;
          padding: 0 !important;
          gap: var(--m-page-gap, 8px) !important;
          break-inside: auto !important;
          page-break-inside: auto !important;
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-task-health__list,
        #mango-effectiveness-report-image .mango-effectiveness-case-health__list {
          min-height: 0 !important;
          flex: 1 1 auto !important;
          max-height: none !important;
          overflow: visible !important;
          scrollbar-gutter: auto !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-task-health__list article .arco-btn,
        #mango-effectiveness-report-image .mango-effectiveness-case-health__list article .arco-btn {
          display: none !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-grid--health {
          align-items: start !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-grid--health > .mango-effectiveness-panel {
          height: auto !important;
          max-height: none !important;
          box-sizing: border-box !important;
          overflow: visible !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-grid--module-analysis > .mango-effectiveness-panel:last-child:nth-child(odd) {
          grid-column: 1 / -1 !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-card {
          min-height: 116px !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-card__comparison,
        #mango-effectiveness-report-image .mango-effectiveness-card__footer small {
          overflow: visible !important;
          text-overflow: clip !important;
          white-space: normal !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title {
          display: grid !important;
          min-height: 68px !important;
          grid-template-columns: minmax(0, 1fr) !important;
          padding: 6px 0 !important;
          align-content: center !important;
          gap: 2px !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title strong {
          white-space: nowrap !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-grid--diagnostics .mango-effectiveness-panel-title > small {
          max-width: 100% !important;
          justify-self: start !important;
          white-space: normal !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-insight,
        #mango-effectiveness-report-image .mango-effectiveness-card,
        #mango-effectiveness-report-image .mango-section-card,
        #mango-effectiveness-report-image .mango-effectiveness-report-header {
          break-inside: avoid !important;
          page-break-inside: avoid !important;
          box-shadow: none !important;
        }
        #mango-effectiveness-report-image .mango-effectiveness-ai-card__action,
        #mango-effectiveness-report-image .mango-effectiveness-ai-unavailable .arco-btn {
          display: none !important;
        }
      `

export function reportFileName(title: string, extension: string): string {
  const safeTitle = title.replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, ' ').trim()
  return `${safeTitle || '自动化质量效能报告'}.${extension}`
}
