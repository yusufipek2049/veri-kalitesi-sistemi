import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
} from "@mui/material";
import { criticalityLabels } from "../labels";
import type { RuleListItem, RuleVersionCreateRequest } from "../model";
import { initialSqlEditorValues, sqlParameters, validateSql, type SqlEditorValues } from "../sqlValidation";
import type { VersionDialogSeed } from "../useRuleActions";
import { SqlEditor } from "./SqlEditor";

interface VersionFormFieldsProps {
  form: RuleVersionCreateRequest;
  onPatch: (patch: Partial<RuleVersionCreateRequest>) => void;
}

function VersionFormFields({ form, onPatch }: VersionFormFieldsProps) {
  return (
    <>
      <TextField
        autoFocus
        fullWidth
        label="Eşik Değeri (0-100)"
        onChange={(e) => onPatch({ threshold: Number(e.target.value) })}
        required
        type="number"
        value={form.threshold}
      />
      <TextField
        fullWidth
        label="Ağırlık"
        onChange={(e) => onPatch({ weight: Number(e.target.value) })}
        required
        type="number"
        value={form.weight}
      />
      <FormControl fullWidth>
        <InputLabel id="version-criticality-label">Kritiklik</InputLabel>
        <Select
          label="Kritiklik"
          labelId="version-criticality-label"
          onChange={(e) => onPatch({ criticality: e.target.value })}
          value={form.criticality}
        >
          {Object.entries(criticalityLabels).map(([value, label]) => (
            <MenuItem key={value} value={value}>{label}</MenuItem>
          ))}
        </Select>
      </FormControl>
    </>
  );
}

interface CreateVersionDialogProps {
  open: boolean;
  item: RuleListItem | null;
  seed: VersionDialogSeed;
  error: string | null;
  onClose: () => void;
  onError: (message: string | null) => void;
  onCreateVersion?: (rule: RuleListItem, data: RuleVersionCreateRequest) => Promise<void>;
}

export function CreateVersionDialog({
  open,
  item,
  seed,
  error,
  onClose,
  onError,
  onCreateVersion,
}: CreateVersionDialogProps) {
  const [form, setForm] = useState<RuleVersionCreateRequest>({
    threshold: 100,
    weight: 1,
    criticality: "MEDIUM",
    parameters: {},
  });
  const [sql, setSql] = useState<SqlEditorValues>(initialSqlEditorValues);
  const [sqlError, setSqlError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !item) return;
    setForm({ threshold: 100, weight: 1, criticality: item.criticality, parameters: {} });
    setSqlError(null);
    setLoading(false);
  }, [open, item]);

  useEffect(() => {
    if (open) setSql(seed.sql);
  }, [open, seed]);

  const handleClose = () => {
    if (!loading) onClose();
  };

  const handleSubmit = async () => {
    if (!item || !onCreateVersion || loading) return;
    // Validate SQL if CUSTOM_SQL
    if (item.ruleType === "CUSTOM_SQL") {
      const err = validateSql(sql.text);
      if (err) {
        setSqlError(err);
        return;
      }
      setSqlError(null);
    }
    setLoading(true);
    onError(null);
    try {
      const versionData = { ...form };
      if (item.ruleType === "CUSTOM_SQL") {
        versionData.parameters = { ...versionData.parameters, ...sqlParameters(sql) };
      }
      await onCreateVersion(item, versionData);
      onClose();
    } catch {
      onError("Sürüm oluşturulamadı.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      aria-labelledby="version-dialog-title"
      maxWidth="sm"
      onClose={handleClose}
      open={open}
      fullWidth
    >
      <DialogTitle id="version-dialog-title">
        Yeni Sürüm Oluştur — {item?.name}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
          <VersionFormFields
            form={form}
            onPatch={(patch) => setForm((prev) => ({ ...prev, ...patch }))}
          />
          {/* SQL editor for CUSTOM_SQL version */}
          {item?.ruleType === "CUSTOM_SQL" ? (
            <SqlEditor
              values={sql}
              error={sqlError}
              loading={seed.loading}
              introText="SQL sorgusunu düzenleyin ve yeni sürüm oluşturun."
              onChange={(patch) => setSql((prev) => ({ ...prev, ...patch }))}
              onErrorCleared={() => setSqlError(null)}
            />
          ) : null}
          {error ? (
            <Alert severity="error">{error}</Alert>
          ) : null}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button disabled={loading} onClick={onClose}>İptal</Button>
        <Button disabled={loading} onClick={handleSubmit} variant="contained">
          {loading ? "Oluşturuluyor..." : "Sürüm Oluştur"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
