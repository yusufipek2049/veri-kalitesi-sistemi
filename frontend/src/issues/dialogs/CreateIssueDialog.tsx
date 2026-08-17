import { useEffect, useState } from "react";
import {
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
  Typography,
} from "@mui/material";
import { priorityLabels, type IssueActionFeedback } from "../labels";
import type { IssueCreateInput, IssuePriority } from "../model";

interface CreateIssueDialogProps {
  open: boolean;
  onCreateIssue?: (input: IssueCreateInput) => Promise<void>;
  onNotify: (feedback: IssueActionFeedback | undefined) => void;
  onClose: () => void;
}

export function CreateIssueDialog({
  open,
  onCreateIssue,
  onNotify,
  onClose,
}: CreateIssueDialogProps) {
  const [title, setTitle] = useState("");
  const [scopeType, setScopeType] = useState<"DATASET" | "SOURCE">("DATASET");
  const [scopeId, setScopeId] = useState("");
  const [priority, setPriority] = useState<IssuePriority>("MEDIUM");
  const [pending, setPending] = useState(false);
  useEffect(() => {
    if (!open) return;
    setTitle("");
    setScopeType("DATASET");
    setScopeId("");
    setPriority("MEDIUM");
  }, [open]);
  const submit = async () => {
    if (!onCreateIssue || pending) return;
    if (!title.trim() || !scopeId.trim()) return;
    setPending(true);
    onNotify(undefined);
    try {
      await onCreateIssue({
        title: title.trim(),
        scopeType,
        scopeId: scopeId.trim(),
        priority,
      });
      onNotify({
        severity: "success",
        message: "Yeni sorun oluşturuldu.",
      });
      onClose();
    } catch (error) {
      onNotify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Sorun oluşturulamadı. Yeniden deneyin.",
      });
    } finally {
      setPending(false);
    }
  };

  return (
    <Dialog
      aria-describedby="create-issue-dialog-description"
      fullWidth
      maxWidth="sm"
      onClose={onClose}
      open={open}
    >
      <DialogTitle>Yeni sorun oluştur</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
        <Typography color="text.secondary" id="create-issue-dialog-description">
          Manuel olarak yeni bir kalite sorunu oluşturun. Sorun, sahip zinciri doğrulandıktan sonra ilgili sorumluya atanır.
        </Typography>
        <TextField
          label="Başlık"
          onChange={(event) => setTitle(event.target.value)}
          required
          slotProps={{ htmlInput: { maxLength: 200 } }}
          value={title}
        />
        <FormControl>
          <InputLabel id="create-scope-type-label">Kapsam türü</InputLabel>
          <Select
            label="Kapsam türü"
            labelId="create-scope-type-label"
            onChange={(event) => setScopeType(event.target.value as "DATASET" | "SOURCE")}
            value={scopeType}
          >
            <MenuItem value="DATASET">Dataset</MenuItem>
            <MenuItem value="SOURCE">Veri kaynağı</MenuItem>
          </Select>
        </FormControl>
        <TextField
          label="Kapsam kimliği"
          onChange={(event) => setScopeId(event.target.value)}
          placeholder="dataset-customer veya source-risk-mart"
          required
          value={scopeId}
        />
        <FormControl>
          <InputLabel id="create-priority-label">Öncelik</InputLabel>
          <Select
            label="Öncelik"
            labelId="create-priority-label"
            onChange={(event) => setPriority(event.target.value as IssuePriority)}
            value={priority}
          >
            {Object.entries(priorityLabels).map(([value, label]) => (
              <MenuItem key={value} value={value}>{label}</MenuItem>
            ))}
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Vazgeç</Button>
        <Button
          disabled={
            !title.trim()
            || !scopeId.trim()
            || pending
          }
          onClick={() => void submit()}
          variant="contained"
        >
          {pending ? "Oluşturuluyor" : "Oluştur"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
