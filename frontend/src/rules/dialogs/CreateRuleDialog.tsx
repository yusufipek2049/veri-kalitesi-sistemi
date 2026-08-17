import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
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
import { criticalityLabels, dimensionLabels, ruleTypeLabels } from "../labels";
import type { RuleCreateRequest } from "../model";
import { initialSqlEditorValues, sqlParameters, validateSql, type SqlEditorValues } from "../sqlValidation";
import { SqlEditor } from "./SqlEditor";

const initialCreateForm: RuleCreateRequest = {
  code: "",
  name: "",
  dataset_id: "",
  rule_type: "REQUIRED",
  primary_dimension: "COMPLETENESS",
  threshold: 100,
  weight: 1,
  criticality: "MEDIUM",
  owner_user_id: "",
  parameters: {},
};

const singleFieldRuleTypes = ["REQUIRED", "RANGE", "REGEX", "FRESHNESS"];

function buildCreateParameters(
  formData: RuleCreateRequest,
  selectedFieldIds: string[],
  sql: SqlEditorValues,
): Record<string, unknown> {
  const parameters: Record<string, unknown> = { ...formData.parameters };
  if (selectedFieldIds.length > 0) {
    // Single-field rule types use field_id, multi-field use field_ids
    if (singleFieldRuleTypes.includes(formData.rule_type) && selectedFieldIds.length === 1) {
      parameters.field_id = selectedFieldIds[0];
    } else {
      parameters.field_ids = selectedFieldIds;
    }
  }
  if (formData.rule_type === "CUSTOM_SQL") {
    Object.assign(parameters, sqlParameters(sql));
  }
  return parameters;
}

interface FieldMultiSelectProps {
  fields: { id: string; name: string; datasetId: string }[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
}

function FieldMultiSelect({ fields, selectedIds, onChange }: FieldMultiSelectProps) {
  return (
    <FormControl fullWidth>
      <InputLabel id="field-select-label">Alanlar</InputLabel>
      <Select
        fullWidth
        label="Alanlar"
        labelId="field-select-label"
        multiple
        onChange={(e) => {
          const val = e.target.value;
          onChange(typeof val === "string" ? val.split(",") : val);
        }}
        renderValue={(selected) => (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {(selected as string[]).map((id) => {
              const f = fields.find((fd) => fd.id === id);
              return <Chip key={id} label={f?.name ?? id} size="small" />;
            })}
          </Box>
        )}
        value={selectedIds}
      >
        {fields.map((f) => (
          <MenuItem key={f.id} value={f.id}>
            {f.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

interface CreateRuleFormFieldsProps {
  formData: RuleCreateRequest;
  onPatch: (patch: Partial<RuleCreateRequest>) => void;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
  onDatasetChange: (datasetId: string) => void;
}

function RuleIdentityFields({ formData, onPatch, catalogDatasets, onDatasetChange }: CreateRuleFormFieldsProps) {
  return (
    <>
      <TextField
        autoFocus
        fullWidth
        label="Kod"
        onChange={(e) => onPatch({ code: e.target.value })}
        required
        value={formData.code}
      />
      <TextField
        fullWidth
        label="Ad"
        onChange={(e) => onPatch({ name: e.target.value })}
        required
        value={formData.name}
      />
      <FormControl fullWidth>
        <InputLabel id="dataset-id-label">Dataset</InputLabel>
        <Select
          fullWidth
          label="Dataset"
          labelId="dataset-id-label"
          onChange={(e) => onDatasetChange(e.target.value)}
          required
          value={formData.dataset_id}
        >
          {(catalogDatasets ?? []).map((ds) => (
            <MenuItem key={ds.id} value={ds.id}>
              {ds.name} ({ds.namespace})
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </>
  );
}

function RuleTypeField({ formData, onPatch }: Pick<CreateRuleFormFieldsProps, "formData" | "onPatch">) {
  return (
    <FormControl fullWidth>
      <InputLabel id="rule-type-label">Kural Tipi</InputLabel>
      <Select
        label="Kural Tipi"
        labelId="rule-type-label"
        onChange={(e) => onPatch({ rule_type: e.target.value })}
        value={formData.rule_type}
      >
        {Object.entries(ruleTypeLabels).map(([value, label]) => (
          <MenuItem key={value} value={value}>{label}</MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

function RulePolicyFields({ formData, onPatch }: Pick<CreateRuleFormFieldsProps, "formData" | "onPatch">) {
  return (
    <>
      <FormControl fullWidth>
        <InputLabel id="dimension-label">Birincil Boyut</InputLabel>
        <Select
          label="Birincil Boyut"
          labelId="dimension-label"
          onChange={(e) => onPatch({ primary_dimension: e.target.value })}
          value={formData.primary_dimension}
        >
          {Object.entries(dimensionLabels).map(([value, label]) => (
            <MenuItem key={value} value={value}>{label}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        fullWidth
        label="Eşik Değeri (0-100)"
        onChange={(e) => onPatch({ threshold: Number(e.target.value) })}
        required
        type="number"
        value={formData.threshold}
      />
      <TextField
        fullWidth
        label="Ağırlık"
        onChange={(e) => onPatch({ weight: Number(e.target.value) })}
        required
        type="number"
        value={formData.weight}
      />
      <FormControl fullWidth>
        <InputLabel id="criticality-label">Kritiklik</InputLabel>
        <Select
          label="Kritiklik"
          labelId="criticality-label"
          onChange={(e) => onPatch({ criticality: e.target.value })}
          value={formData.criticality}
        >
          {Object.entries(criticalityLabels).map(([value, label]) => (
            <MenuItem key={value} value={value}>{label}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        fullWidth
        label="Sahip Kullanıcı ID"
        onChange={(e) => onPatch({ owner_user_id: e.target.value })}
        required
        value={formData.owner_user_id}
      />
    </>
  );
}

interface CreateRuleDialogProps {
  open: boolean;
  onClose: () => void;
  onCreateRule?: (payload: RuleCreateRequest) => Promise<void>;
  catalogDatasets?: { id: string; name: string; namespace: string }[];
  catalogFields?: { id: string; name: string; datasetId: string }[];
  onLoadFields?: (datasetId: string) => Promise<void>;
}

export function CreateRuleDialog({
  open,
  onClose,
  onCreateRule,
  catalogDatasets,
  catalogFields,
  onLoadFields,
}: CreateRuleDialogProps) {
  const [formData, setFormData] = useState<RuleCreateRequest>(initialCreateForm);
  const [selectedFieldIds, setSelectedFieldIds] = useState<string[]>([]);
  const [sql, setSql] = useState<SqlEditorValues>(initialSqlEditorValues);
  const [sqlError, setSqlError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) setCreateError(null);
  }, [open]);

  // Filter fields for the selected dataset
  const fieldsForDataset = useMemo(() => {
    if (!formData.dataset_id || !catalogFields) return [];
    return catalogFields.filter((f) => f.datasetId === formData.dataset_id);
  }, [formData.dataset_id, catalogFields]);

  // Load fields when dataset changes
  const handleDatasetChange = (datasetId: string) => {
    setFormData((prev) => ({ ...prev, dataset_id: datasetId }));
    setSelectedFieldIds([]);
    if (datasetId && onLoadFields) {
      void onLoadFields(datasetId);
    }
  };

  const handleClose = () => {
    if (!loading) onClose();
  };

  const handleSubmit = async () => {
    if (loading) return;
    // Validate SQL if CUSTOM_SQL
    if (formData.rule_type === "CUSTOM_SQL") {
      const err = validateSql(sql.text);
      if (err) {
        setSqlError(err);
        return;
      }
      setSqlError(null);
    }
    setLoading(true);
    setCreateError(null);
    try {
      if (onCreateRule) {
        const parameters = buildCreateParameters(formData, selectedFieldIds, sql);
        await onCreateRule({ ...formData, parameters });
      }
      onClose();
      setFormData(initialCreateForm);
      setSelectedFieldIds([]);
      setSql(initialSqlEditorValues);
      setSqlError(null);
    } catch {
      setCreateError("Kural oluşturulamadı. Lütfen bilgileri kontrol edin.");
    } finally {
      setLoading(false);
    }
  };

  const showFieldSelect = formData.dataset_id
    && fieldsForDataset.length > 0
    && formData.rule_type !== "CUSTOM_SQL";

  return (
    <Dialog
      aria-labelledby="create-rule-dialog-title"
      maxWidth="sm"
      onClose={handleClose}
      open={open}
      fullWidth
    >
      <DialogTitle id="create-rule-dialog-title">Kural Oluştur</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
          <RuleIdentityFields
            formData={formData}
            onPatch={(patch) => setFormData((prev) => ({ ...prev, ...patch }))}
            catalogDatasets={catalogDatasets}
            onDatasetChange={handleDatasetChange}
          />
          {showFieldSelect ? (
            <FieldMultiSelect
              fields={fieldsForDataset}
              selectedIds={selectedFieldIds}
              onChange={setSelectedFieldIds}
            />
          ) : null}
          <RuleTypeField
            formData={formData}
            onPatch={(patch) => setFormData((prev) => ({ ...prev, ...patch }))}
          />
          {formData.rule_type === "CUSTOM_SQL" ? (
            <SqlEditor
              values={sql}
              error={sqlError}
              onChange={(patch) => setSql((prev) => ({ ...prev, ...patch }))}
              onErrorCleared={() => setSqlError(null)}
            />
          ) : null}
          <RulePolicyFields
            formData={formData}
            onPatch={(patch) => setFormData((prev) => ({ ...prev, ...patch }))}
          />
          {createError ? (
            <Alert severity="error" sx={{ mb: 1 }}>{createError}</Alert>
          ) : null}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button disabled={loading} onClick={handleClose}>İptal</Button>
        <Button disabled={loading} onClick={handleSubmit} variant="contained">{loading ? "Oluşturuluyor..." : "Oluştur"}</Button>
      </DialogActions>
    </Dialog>
  );
}
