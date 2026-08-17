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

interface ActivateRuleDialogProps {
  open: boolean;
  item: RuleListItem | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function ActivateRuleDialog({ open, item, error, loading, onClose, onConfirm }: ActivateRuleDialogProps) {
  return (
    <Dialog
      aria-labelledby="activate-dialog-title"
      maxWidth="sm"
      onClose={() => { if (!loading) onClose(); }}
      open={open}
      fullWidth
    >
      <DialogTitle id="activate-dialog-title">Kuralı Aktifleştir</DialogTitle>
      <DialogContent>
        <Typography sx={{ pt: 2 }}>
          <strong>{item?.name}</strong> kuralını aktifleştirmek istediğinize emin misiniz?
          {item?.criticality === "CRITICAL" && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              Kritik kural aktivasyonu onay gerektirebilir. Lütfen "Onaya Gönder" eylemini kullanın.
            </Alert>
          )}
        </Typography>
        {error ? <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert> : null}
      </DialogContent>
      <DialogActions>
        <Button disabled={loading} onClick={onClose}>İptal</Button>
        <Button disabled={loading} onClick={onConfirm} variant="contained">
          {loading ? "Aktifleştiriliyor..." : "Aktifleştir"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
