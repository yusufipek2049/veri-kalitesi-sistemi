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

interface PassivateRuleDialogProps {
  open: boolean;
  item: RuleListItem | null;
  error: string | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function PassivateRuleDialog({ open, item, error, loading, onClose, onConfirm }: PassivateRuleDialogProps) {
  return (
    <Dialog
      aria-labelledby="passivate-dialog-title"
      maxWidth="sm"
      onClose={() => { if (!loading) onClose(); }}
      open={open}
      fullWidth
    >
      <DialogTitle id="passivate-dialog-title">Kuralı Pasifleştir</DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mt: 1 }}>
          <Typography sx={{ fontWeight: 700 }}>
            Bu işlem geri alınamaz — pasifleştirilen kural yeni çalıştırmalara dahil edilmez.
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            <strong>{item?.name}</strong> kuralını pasifleştirmek istediğinize emin misiniz?
            Geçmiş sonuçlar korunur, ancak kural yeni execution'larda çalıştırılmaz.
          </Typography>
        </Alert>
        {error ? <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert> : null}
      </DialogContent>
      <DialogActions>
        <Button disabled={loading} onClick={onClose}>Vazgeç</Button>
        <Button disabled={loading} onClick={onConfirm} variant="contained" color="error">
          {loading ? "Pasifleştiriliyor..." : "Pasifleştir"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
