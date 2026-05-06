function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export async function exportReportPdf(report) {
  const { jsPDF } = await import("jspdf");
  const pdf = new jsPDF();
  pdf.setFontSize(18);
  pdf.text(report.title, 16, 20);
  pdf.setFontSize(11);
  pdf.text(report.summary, 16, 34, { maxWidth: 180 });
  pdf.text(`${report.metricLabel}: ${report.metric}`, 16, 52);
  pdf.text(`${report.priorityLabel}: ${report.priority}`, 16, 60);
  pdf.text(`${report.recommendationLabel}: ${report.recommendation}`, 16, 68, { maxWidth: 180 });
  pdf.save(`${report.slug}.pdf`);
}

export async function exportReportExcel(report) {
  const XLSX = await import("xlsx");
  const worksheet = XLSX.utils.json_to_sheet([
    {
      title: report.title,
      summary: report.summary,
      [report.metricLabel]: report.metric,
      [report.priorityLabel]: report.priority,
      [report.recommendationLabel]: report.recommendation,
    },
  ]);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Report");
  const content = XLSX.write(workbook, { bookType: "xlsx", type: "array" });
  downloadBlob(
    new Blob([content], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }),
    `${report.slug}.xlsx`,
  );
}