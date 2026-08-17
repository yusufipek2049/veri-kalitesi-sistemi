import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";

export function DiscardConfirmDialog({
  open,
  descriptionId,
  description,
  onStay,
  onDiscard,
}: {
  open: boolean;
  descriptionId: string;
  description: string;
  onStay: () => void;
  onDiscard: () => void;
}) {
  return (
    <Dialog
      aria-describedby={descriptionId}
      onClose={onStay}
      open={open}
    >
      <DialogTitle>Değişiklikler kaydedilmedi</DialogTitle>
      <DialogContent>
        <Typography id={descriptionId}>
          {description}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onStay}>Forma dön</Button>
        <Button color="error" onClick={onDiscard}>Değişiklikleri sil</Button>
      </DialogActions>
    </Dialog>
  );
}
