import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
} from "@mui/material";
import { Search } from "lucide-react";
import { type IssueFilterState } from "./filtering";
import { priorityLabels, statusLabels } from "./labels";

export function IssuesFilters({
  filters,
  onChange,
  onReset,
}: {
  filters: IssueFilterState;
  onChange: (patch: Partial<IssueFilterState>) => void;
  onReset: () => void;
}) {
  return (
    <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
      <Box aria-label="Sorun filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(180px, 1fr))", lg: "minmax(230px, 1.35fr) repeat(4, minmax(145px, .7fr))" } }}>
        <TextField label="Sorun ara" onChange={(event) => onChange({ query: event.target.value })} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={filters.query} />
        <FormControl><InputLabel id="issue-status-label">Durum</InputLabel><Select label="Durum" labelId="issue-status-label" onChange={(event) => onChange({ status: event.target.value })} value={filters.status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
        <FormControl><InputLabel id="issue-priority-label">Öncelik</InputLabel><Select label="Öncelik" labelId="issue-priority-label" onChange={(event) => onChange({ priority: event.target.value })} value={filters.priority}><MenuItem value="ALL">Tüm öncelikler</MenuItem>{Object.entries(priorityLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
        <FormControl><InputLabel id="issue-period-label">Tarih</InputLabel><Select label="Tarih" labelId="issue-period-label" onChange={(event) => onChange({ period: event.target.value })} value={filters.period}><MenuItem value="ALL">Tüm tarihler</MenuItem><MenuItem value="LATEST_DAY">Son güncellenen gün</MenuItem><MenuItem value="LAST_7_DAYS">Son 7 gün</MenuItem></Select></FormControl>
        <FormControl><InputLabel id="issue-scope-label">Kapsam</InputLabel><Select disabled label="Kapsam" labelId="issue-scope-label" value="AUTHORIZED"><MenuItem value="AUTHORIZED">Yetkili kapsam</MenuItem></Select></FormControl>
      </Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
        <Button onClick={onReset} size="small">Filtreleri temizle</Button>
      </Box>
    </Paper>
  );
}
