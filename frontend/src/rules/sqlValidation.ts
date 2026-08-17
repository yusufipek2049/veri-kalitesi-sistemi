const forbiddenSqlKeywords = [
  "DROP",
  "DELETE",
  "INSERT",
  "UPDATE",
  "ALTER",
  "TRUNCATE",
  "CREATE",
];

export function validateSql(sql: string): string | null {
  const trimmed = sql.trim();
  if (!trimmed) return "SQL sorgusu zorunludur.";
  const upper = trimmed.toUpperCase();
  if (!upper.startsWith("SELECT")) return "SQL sorgusu SELECT ile başlamalıdır.";
  for (const keyword of forbiddenSqlKeywords) {
    if (upper.includes(`${keyword} `)) return `SQL sorgusu ${keyword} içermemelidir.`;
  }
  return null;
}

export interface SqlEditorValues {
  text: string;
  timeout: number;
  rowLimit: number;
}

export const initialSqlEditorValues: SqlEditorValues = {
  text: "",
  timeout: 30,
  rowLimit: 1000,
};

export function sqlParameters(values: SqlEditorValues): Record<string, unknown> {
  return {
    sql: values.text.trim(),
    timeout_seconds: values.timeout,
    row_limit: values.rowLimit,
  };
}
