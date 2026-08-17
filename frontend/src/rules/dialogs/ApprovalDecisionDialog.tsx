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
import type { RuleListItem } from "../model";

interface ApprovalDecisionDialogProps {
  open: boolean;
  item: RuleListItem | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (decision: "APPROVE" | "REJECT", reason: string) => void;
}

export function ApprovalDecisionDialog({ open, item, error, loading, onClose, onSubmit }: ApprovalDecisionDialogProps) {
  const [decision, setDecision] = useState<"APPROVE" | "REJECT">("APPROVE");
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) {
      setDecision("APPROVE");
      setReason("");
    }
  }, [open]);

  return (
    <Dialog
      aria-labelledby="decision-dialog-title"
      maxWidth="sm"
      onClose={() => { if (!loading) onClose(); }}
      open={open}
      fullWidth
    >
      <DialogTitle id="decision-dialog-title">Onay Kararı — {item?.name}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
          <FormControl fullWidth>
            <InputLabel id="decision-label">Karar</InputLabel>
            <Select
              label="Karar"
              labelId="decision-label"
              onChange={(e) => setDecision(e.target.value as "APPROVE" | "REJECT")}
              value={decision}
            >
              <MenuItem value="APPROVE">Onayla</MenuItem>
              <MenuItem value="REJECT">Reddet</MenuItem>
            </Select>
          </FormControl>
          <TextField
            autoFocus
            fullWidth
            label="Gerekçe Kodu"
            onChange={(e) => setReason(e.target.value)}
            required
            value={reason}
          />
          {error ? <Alert severity="error">{error}</Alert> : null}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button disabled={loading} onClick={onClose}>İptal</Button>
        <Button disabled={loading} onClick={() => onSubmit(decision, reason)} variant="contained">
          {loading ? "Kaydediliyor..." : "Kararı Kaydet"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
