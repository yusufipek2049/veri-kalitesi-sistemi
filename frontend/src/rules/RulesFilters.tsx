import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
} from "@mui/material";
import { Search } from "lucide-react";
import type { RuleFilterValues } from "./filtering";
import { criticalityLabels, dimensionLabels, statusLabels } from "./labels";

interface RulesFiltersProps {
  filters: RuleFilterValues;
  onChange: (patch: Partial<RuleFilterValues>) => void;
}

export function RulesFilters({ filters, onChange }: RulesFiltersProps) {
  return (
    <Paper component="section" sx={{ borderRadius: 1.5, p: 4 }} variant="outlined">
      <Box aria-label="Kural filtreleri" sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", md: "minmax(240px, 1.4fr) repeat(3, minmax(150px, .7fr))" } }}>
        <TextField label="Kural ara" onChange={(event) => onChange({ query: event.target.value })} slotProps={{ input: { startAdornment: <Search aria-hidden="true" size={16} /> } }} value={filters.query} />
        <FormControl><InputLabel id="rule-status-label">Durum</InputLabel><Select label="Durum" labelId="rule-status-label" onChange={(event) => onChange({ status: event.target.value })} value={filters.status}><MenuItem value="ALL">Tüm durumlar</MenuItem>{Object.entries(statusLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
        <FormControl><InputLabel id="rule-dimension-label">Boyut</InputLabel><Select label="Boyut" labelId="rule-dimension-label" onChange={(event) => onChange({ dimension: event.target.value })} value={filters.dimension}><MenuItem value="ALL">Tüm boyutlar</MenuItem>{Object.entries(dimensionLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
        <FormControl><InputLabel id="rule-criticality-label">Kritiklik</InputLabel><Select label="Kritiklik" labelId="rule-criticality-label" onChange={(event) => onChange({ criticality: event.target.value })} value={filters.criticality}><MenuItem value="ALL">Tüm seviyeler</MenuItem>{Object.entries(criticalityLabels).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}</Select></FormControl>
      </Box>
    </Paper>
  );
}
