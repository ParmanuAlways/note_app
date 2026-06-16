// Single date-display convention for the whole UI: DD MMM YYYY (NFR-5).
// No US MM/DD anywhere. v1 is single-zone, so local rendering is fine.

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function ddMMMyyyy(iso: string): string {
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, "0");
  return `${day} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}
