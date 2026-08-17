import type { RuleListItem } from "./model";

export interface RuleFilterValues {
  query: string;
  status: string;
  dimension: string;
  criticality: string;
}

export const initialRuleFilters: RuleFilterValues = {
  query: "",
  status: "ALL",
  dimension: "ALL",
  criticality: "ALL",
};

export function filterRules(
  items: RuleListItem[],
  filters: RuleFilterValues,
): RuleListItem[] {
  const needle = filters.query.toLocaleLowerCase("tr-TR");
  return items.filter((item) => {
    const searchable = `${item.name} ${item.code} ${item.datasetId} ${item.ruleType}`;
    return searchable.toLocaleLowerCase("tr-TR").includes(needle)
      && (filters.status === "ALL" || item.status === filters.status)
      && (filters.dimension === "ALL" || item.dimension === filters.dimension)
      && (filters.criticality === "ALL" || item.criticality === filters.criticality);
  });
}

export function longContentItems(items: RuleListItem[]): RuleListItem[] {
  return Array.from({ length: 4 }, (_, group) => items.map((item) => ({
    ...item,
    id: `${item.id}-${group + 1}`,
    name: `${item.name} ${group + 1}`,
  }))).flat();
}
