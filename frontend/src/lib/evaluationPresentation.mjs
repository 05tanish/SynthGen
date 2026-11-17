export function metricText(value) {
  if (value === null || value === undefined) return 'Unavailable';
  if (typeof value === 'number') {
    return Number.isFinite(value) ? String(Number(value.toPrecision(5))) : 'Unavailable';
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.length ? value.map(String).join(', ') : 'None';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function qualityDecisionText(evaluationStatus, accepted) {
  if (evaluationStatus === 'FAILED') return 'Not evaluated (failed)';
  if (evaluationStatus === 'INCOMPLETE') return 'Incomplete';
  if (evaluationStatus !== 'COMPLETED') return 'Unavailable';
  if (accepted === null || accepted === undefined) return 'No decision';
  return accepted ? 'Accepted' : 'Not accepted';
}

// Four compact, raw indicators for the latest report. These are deliberately
// not combined into a score: the underlying measurements have different units.
/** @param {Record<string, any>} report
 * @returns {{available: boolean, items: Array<{label: string, value: string, detail: string}>}}
 */
export function evaluationSummary(report = {}) {
  // Some API responses and historical rows wrap the report one level deep.
  report = report.evaluation_report || report.report || report;
  const schema = report.schema_details || {};
  const statistical = report.statistical_details || {};
  const columns = statistical.columns || {};
  const privacy = report.privacy_details || {};
  const exact = privacy.metrics?.exact_match || {};
  const utility = report.ml_utility_details || {};
  const metrics = utility.metrics || {};
  const schemaAvailable = typeof schema.valid === 'boolean';
  const measuredColumns = Object.values(columns).filter((item) =>
    item && ['COMPLETED', 'INCOMPLETE'].includes(item.status)
  ).length;
  const statisticalAvailable = Object.keys(columns).length > 0;
  const privacyAvailable = typeof exact.synthetic_rows_with_real_match === 'number'
    && Number.isFinite(exact.synthetic_rows_with_real_match);
  const isClassification = utility.task === 'classification';
  const utilityMetric = isClassification ? 'f1_weighted' : 'r2';
  const trtrValue = metrics.TRTR?.[utilityMetric];
  const tstrValue = metrics.TSTR?.[utilityMetric];
  const utilityAvailable = utility.status === 'COMPLETED'
    && typeof trtrValue === 'number' && Number.isFinite(trtrValue)
    && typeof tstrValue === 'number' && Number.isFinite(tstrValue);
  const available = schemaAvailable || statisticalAvailable || privacyAvailable || utilityAvailable;

  // Keep compatibility with reports saved by the previous evaluator. These
  // values are shown only when they were actually persisted; they are never
  // recomputed or replaced with defaults.
  const legacyScores = [
    ['Statistical score', report.statistical_score],
    ['Privacy score', report.privacy_score],
    ['ML utility score', report.ml_utility_score],
    ['Overall score', report.overall_score],
  ].filter(([, value]) => typeof value === 'number' && Number.isFinite(value));

  if (!available && legacyScores.length) {
    return {
      available: true,
      legacy: true,
      items: legacyScores.map(([label, value]) => ({
        label,
        value: metricText(value),
        detail: 'Saved by the previous evaluator',
      })),
    };
  }

  return {
    available,
    legacy: false,
    items: [
      {
        label: 'Schema',
        value: schemaAvailable ? (schema.valid ? 'Valid' : 'Issues found') : 'Unavailable',
        detail: schemaAvailable
          ? `${Array.isArray(schema.issues) ? schema.issues.length : 0} reported issues`
          : 'No schema result was recorded',
      },
      {
        label: 'Statistical coverage',
        value: statisticalAvailable ? `${measuredColumns} / ${Object.keys(columns).length} columns` : 'Unavailable',
        detail: statisticalAvailable ? 'Columns with a reported comparison' : 'No column results were recorded',
      },
      {
        label: 'Exact row matches',
        value: privacyAvailable ? String(exact.synthetic_rows_with_real_match) : 'Unavailable',
        detail: privacyAvailable ? 'Synthetic rows matching a real row; empirical indicator only' : 'No exact-match result was recorded',
      },
      {
        label: utilityAvailable ? `TSTR vs TRTR ${utilityMetric}` : 'ML utility',
        value: utilityAvailable ? `${metricText(tstrValue)} / ${metricText(trtrValue)}` : 'Unavailable',
        detail: utilityAvailable
          ? (isClassification ? 'Synthetic-trained / real-trained; weighted F1' : 'Synthetic-trained / real-trained; R²')
          : 'No completed comparable ML result was recorded',
      },
    ],
  };
}
