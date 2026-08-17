import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import type { RuleListItem } from "../model";

interface WithdrawApprovalDialogProps {
  open: boolean;
  item: RuleListItem | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => void;
}

export function WithdrawApprovalDialog({ open, item, error, loading, onClose, onSubmit }: WithdrawApprovalDialogProps) {
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  return (
    <Dialog
      aria-labelledby="withdraw-dialog-title"
      maxWidth="sm"
      onClose={() => { if (!loading) onClose(); }}
      open={open}
      fullWidth
    >
      <DialogTitle id="withdraw-dialog-title">Onayı Geri Çek — {item?.name}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "grid", gap: 3, pt: 2 }}>
          <Typography>
            Bu onay isteğini geri çekmek istediğinize emin misiniz? Kural taslak durumunda kalacaktır.
          </Typography>
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
        <Button disabled={loading} onClick={() => onSubmit(reason)} variant="contained">
          {loading ? "Geri Çekiliyor..." : "Geri Çek"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
