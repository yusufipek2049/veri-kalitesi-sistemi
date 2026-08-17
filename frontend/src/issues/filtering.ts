import type { IssueListItem } from "./model";

export interface IssueFilterState {
  query: string;
  status: string;
  priority: string;
  period: string;
}

export const initialIssueFilters: IssueFilterState = {
  query: "",
  status: "ALL",
  priority: "ALL",
  period: "ALL",
};

export function newestUpdatedTime(items: IssueListItem[]): number {
  return items.length
    ? Math.max(...items.map((item) => new Date(item.updatedAt).getTime()))
    : 0;
}

export function filterIssues(
  items: IssueListItem[],
  filters: IssueFilterState,
  newestTime: number,
): IssueListItem[] {
  const query = filters.query.toLocaleLowerCase("tr-TR");
  return items.filter((item) => {
    const searchable = `${item.issueNo} ${item.scopeId}`.toLocaleLowerCase("tr-TR");
    const ageDays = (newestTime - new Date(item.updatedAt).getTime()) / 86_400_000;
    return searchable.includes(query)
      && (filters.status === "ALL" || item.status === filters.status)
      && (filters.priority === "ALL" || item.priority === filters.priority)
      && (filters.period === "ALL" || (filters.period === "LATEST_DAY" ? ageDays < 1 : ageDays <= 7));
  });
}
