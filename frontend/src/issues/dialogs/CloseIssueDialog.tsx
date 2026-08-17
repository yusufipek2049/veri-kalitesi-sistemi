import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";
import type { IssueActionFeedback } from "../labels";
import type { IssueListItem } from "../model";

export function CloseIssueDialog({
  item,
  pendingIssueId,
  onCloseIssue,
  onNotify,
  setPendingIssueId,
  onClose,
}: {
  item?: IssueListItem;
  pendingIssueId?: string;
  onCloseIssue?: (item: IssueListItem) => Promise<void>;
  onNotify: (feedback: IssueActionFeedback | undefined) => void;
  setPendingIssueId: (id: string | undefined) => void;
  onClose: () => void;
}) {
  const submit = async () => {
    if (!item || !onCloseIssue || pendingIssueId) return;
    setPendingIssueId(item.id);
    onNotify(undefined);
    try {
      await onCloseIssue(item);
      onNotify({
        severity: "success",
        message: `${item.issueNo} kapatıldı.`,
      });
      onClose();
    } catch (error) {
      onNotify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Kapatma tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };

  return (
    <Dialog
      aria-describedby="close-dialog-description"
      fullWidth
      maxWidth="sm"
      onClose={onClose}
      open={Boolean(item)}
    >
      <DialogTitle>Sorunu kapat</DialogTitle>
      <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
        <Typography color="text.secondary" id="close-dialog-description">
          {item?.issueNo} sorununu kapatıyorsunuz. Kapatma işlemi geri alınamaz.
        </Typography>
        <Typography color="text.secondary" variant="caption">
          Kapatıldığında sorun Kapatıldı durumuna geçer ve değişiklik geçmişe yazılır.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Vazgeç</Button>
        <Button
          disabled={pendingIssueId === item?.id}
          onClick={() => void submit()}
          variant="contained"
        >
          {pendingIssueId === item?.id ? "Kapatılıyor" : "Kapat"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
