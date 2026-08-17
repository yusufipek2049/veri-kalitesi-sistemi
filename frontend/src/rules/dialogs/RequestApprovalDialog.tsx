import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";
import type { RuleListItem } from "../model";

interface RequestApprovalDialogProps {
  open: boolean;
  item: RuleListItem | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function RequestApprovalDialog({ open, item, error, loading, onClose, onConfirm }: RequestApprovalDialogProps) {
  return (
    <Dialog
      aria-labelledby="approval-request-dialog-title"
      maxWidth="sm"
      onClose={() => { if (!loading) onClose(); }}
      open={open}
      fullWidth
    >
      <DialogTitle id="approval-request-dialog-title">Onay İsteği Gönder</DialogTitle>
      <DialogContent>
        <Typography sx={{ pt: 2 }}>
          <strong>{item?.name}</strong> kuralı için onay isteği gönderilecek. Bu işlem kuralı onay sürecine alır.
        </Typography>
        {error ? <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert> : null}
      </DialogContent>
      <DialogActions>
        <Button disabled={loading} onClick={onClose}>İptal</Button>
        <Button disabled={loading} onClick={onConfirm} variant="contained">
          {loading ? "Gönderiliyor..." : "Onaya Gönder"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
