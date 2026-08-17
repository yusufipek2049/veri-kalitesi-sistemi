import { useCallback, useEffect, useState } from "react";
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
  Skeleton,
  Typography,
} from "@mui/material";
import { priorityLabels, type IssueActionFeedback } from "../labels";
import type { IssueAssigneeOption, IssueListItem, IssuePriority } from "../model";
import { DiscardConfirmDialog } from "./DiscardConfirmDialog";

type OptionsState = "idle" | "loading" | "ready" | "error";

interface AssignmentDialogProps {
  item?: IssueListItem;
  pendingIssueId?: string;
  onLoadAssignmentOptions?: (item: IssueListItem) => Promise<IssueAssigneeOption[]>;
  onReassign?: (
    item: IssueListItem,
    assigneeUserId: string,
    priority: IssuePriority,
  ) => Promise<void>;
  onNotify: (feedback: IssueActionFeedback | undefined) => void;
  setPendingIssueId: (id: string | undefined) => void;
  onClose: () => void;
}

function useAssignmentForm({
  item,
  pendingIssueId,
  onLoadAssignmentOptions,
  onReassign,
  onNotify,
  setPendingIssueId,
  onClose,
}: AssignmentDialogProps) {
  const [options, setOptions] = useState<IssueAssigneeOption[]>([]);
  const [optionsState, setOptionsState] = useState<OptionsState>("idle");
  const [selectedAssigneeId, setSelectedAssigneeId] = useState("");
  const [selectedPriority, setSelectedPriority] = useState<IssuePriority>("MEDIUM");
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const loadOptions = useCallback(async (target: IssueListItem) => {
    if (!onLoadAssignmentOptions) return;
    setOptionsState("loading");
    try {
      const loaded = await onLoadAssignmentOptions(target);
      setOptions(loaded);
      setOptionsState("ready");
    } catch (error) {
      setOptions([]);
      setOptionsState("error");
      onNotify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Atama seçenekleri yüklenemedi. Yeniden deneyin.",
      });
    }
  }, [onLoadAssignmentOptions, onNotify]);
  useEffect(() => {
    if (!item) return;
    setSelectedAssigneeId("");
    setSelectedPriority(item.priority);
    setConfirmDiscard(false);
    void loadOptions(item);
  }, [item, loadOptions]);
  const requestClose = () => {
    if (
      item
      && (selectedAssigneeId || selectedPriority !== item.priority)
    ) {
      setConfirmDiscard(true);
      return;
    }
    setConfirmDiscard(false);
    onClose();
  };
  const submit = async () => {
    if (!item || !selectedAssigneeId || !onReassign || pendingIssueId) return;
    setPendingIssueId(item.id);
    onNotify(undefined);
    try {
      await onReassign(item, selectedAssigneeId, selectedPriority);
      onNotify({
        severity: "success",
        message: `${item.issueNo} yeniden atandı.`,
      });
      onClose();
    } catch (error) {
      onNotify({
        severity: "error",
        message: error instanceof Error
          ? error.message
          : "Atama tamamlanamadı. Sorunu yenileyip yeniden deneyin.",
      });
    } finally {
      setPendingIssueId(undefined);
    }
  };
  return {
    confirmDiscard,
    loadOptions,
    options,
    optionsState,
    requestClose,
    selectedAssigneeId,
    selectedPriority,
    setSelectedAssigneeId,
    setSelectedPriority,
    setConfirmDiscard,
    submit,
  };
}

function AssignmentOptionsSection({
  options,
  optionsState,
  selectedAssigneeId,
  selectedPriority,
  onSelectAssignee,
  onSelectPriority,
  onRetry,
}: {
  options: IssueAssigneeOption[];
  optionsState: OptionsState;
  selectedAssigneeId: string;
  selectedPriority: IssuePriority;
  onSelectAssignee: (value: string) => void;
  onSelectPriority: (value: IssuePriority) => void;
  onRetry: () => void;
}) {
  if (optionsState === "loading") {
    return (
      <Box aria-label="Atama seçenekleri yükleniyor" sx={{ display: "grid", gap: 2 }}>
        <Skeleton height={56} />
        <Skeleton height={56} />
      </Box>
    );
  }
  if (optionsState === "error") {
    return (
      <Alert
        action={<Button color="inherit" onClick={onRetry}>Yeniden dene</Button>}
        severity="error"
      >
        Atama seçenekleri yüklenemedi.
      </Alert>
    );
  }
  if (optionsState !== "ready") return null;
  return (
    <>
      {options.length ? (
        <FormControl>
          <InputLabel id="assignment-user-label">Yeni sorumlu</InputLabel>
          <Select
            label="Yeni sorumlu"
            labelId="assignment-user-label"
            onChange={(event) => onSelectAssignee(event.target.value)}
            value={selectedAssigneeId}
          >
            {options.map((option) => (
              <MenuItem key={option.userId} value={option.userId}>
                {option.displayName}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : (
        <Alert severity="info">
          Bu kapsam için atanabilir kullanıcı bulunamadı.
        </Alert>
      )}
      <FormControl>
        <InputLabel id="assignment-priority-label">Öncelik</InputLabel>
        <Select
          label="Öncelik"
          labelId="assignment-priority-label"
          onChange={(event) => onSelectPriority(event.target.value as IssuePriority)}
          value={selectedPriority}
        >
          {Object.entries(priorityLabels).map(([value, label]) => (
            <MenuItem key={value} value={value}>{label}</MenuItem>
          ))}
        </Select>
      </FormControl>
    </>
  );
}

export function AssignmentDialog(props: AssignmentDialogProps) {
  const { item, pendingIssueId, onClose } = props;
  const form = useAssignmentForm(props);
  return (
    <>
      <Dialog
        aria-describedby="assignment-dialog-description"
        fullWidth
        maxWidth="sm"
        onClose={form.requestClose}
        open={Boolean(item) && !form.confirmDiscard}
      >
        <DialogTitle>Sorunu yeniden ata</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 4, pt: 2 }}>
          <Typography color="text.secondary" id="assignment-dialog-description">
            {item?.issueNo} için yeni sorumlu ve öncelik seçin.
          </Typography>
          <Typography color="text.secondary" variant="caption">
            Kaydedildiğinde sorun Atandı durumuna döner ve değişiklik geçmişe yazılır.
          </Typography>
          <AssignmentOptionsSection
            onSelectAssignee={form.setSelectedAssigneeId}
            onSelectPriority={form.setSelectedPriority}
            onRetry={() => { if (item) void form.loadOptions(item); }}
            options={form.options}
            optionsState={form.optionsState}
            selectedAssigneeId={form.selectedAssigneeId}
            selectedPriority={form.selectedPriority}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={form.requestClose}>Vazgeç</Button>
          <Button
            disabled={
              form.optionsState !== "ready"
              || !form.selectedAssigneeId
              || pendingIssueId === item?.id
            }
            onClick={() => void form.submit()}
            variant="contained"
          >
            {pendingIssueId === item?.id ? "Kaydediliyor" : "Kaydet"}
          </Button>
        </DialogActions>
      </Dialog>
      <DiscardConfirmDialog
        description="Kaydedilmemiş atama değişikliklerinden vazgeçilsin mi?"
        descriptionId="discard-assignment-description"
        onDiscard={() => {
          form.setConfirmDiscard(false);
          onClose();
        }}
        onStay={() => form.setConfirmDiscard(false)}
        open={form.confirmDiscard}
      />
    </>
  );
}
