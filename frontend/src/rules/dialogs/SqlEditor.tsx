import { Box, Skeleton, TextField, Typography } from "@mui/material";
import type { SqlEditorValues } from "../sqlValidation";

const sqlHelperText = "SELECT ile başlamalı; DROP, DELETE, INSERT, UPDATE içermemelidir.";

interface SqlEditorProps {
  values: SqlEditorValues;
  error: string | null;
  loading?: boolean;
  introText?: string;
  onChange: (patch: Partial<SqlEditorValues>) => void;
  onErrorCleared: () => void;
}

export function SqlEditor({ values, error, loading = false, introText, onChange, onErrorCleared }: SqlEditorProps) {
  return (
    <Box sx={{ display: "grid", gap: 2 }}>
      {introText ? (
        <Typography color="text.secondary" variant="body2">
          {introText}
        </Typography>
      ) : null}
      {loading ? (
        <Skeleton height={120} />
      ) : (
        <TextField
          fullWidth
          label="SQL Sorgusu"
          multiline
          minRows={6}
          maxRows={16}
          onChange={(e) => { onChange({ text: e.target.value }); onErrorCleared(); }}
          placeholder="SELECT ... -- Salt okunur SQL sorgusunu giriniz"
          required
          error={!!error}
          helperText={error ?? sqlHelperText}
          sx={{ "& .MuiInputBase-input": { fontFamily: "monospace", fontSize: 13 } }}
          value={values.text}
        />
      )}
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "1fr 1fr" }}>
        <TextField
          fullWidth
          label="Zaman Aşımı (sn)"
          onChange={(e) => onChange({ timeout: Number(e.target.value) })}
          type="number"
          value={values.timeout}
        />
        <TextField
          fullWidth
          label="Satır Limiti"
          onChange={(e) => onChange({ rowLimit: Number(e.target.value) })}
          type="number"
          value={values.rowLimit}
        />
      </Box>
    </Box>
  );
}
