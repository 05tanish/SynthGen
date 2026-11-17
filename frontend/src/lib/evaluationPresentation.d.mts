export function metricText(value: unknown): string;
export function qualityDecisionText(evaluationStatus: string | undefined, accepted: boolean | null | undefined): string;
export function evaluationSummary(report?: Record<string, any>): {
  available: boolean;
  legacy?: boolean;
  items: Array<{ label: string; value: string; detail: string }>;
};
