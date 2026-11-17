import { Card, CardContent } from '../ui/Card';
import { evaluationSummary, metricText, qualityDecisionText } from '../../lib/evaluationPresentation.mjs';

type JsonRecord = Record<string, any>;

interface EvaluationReportViewProps {
  report: JsonRecord;
}

export default function EvaluationReportView({ report }: EvaluationReportViewProps) {
  const summary = evaluationSummary(report);
  const status = report.evaluation_status;
  const generator = report.execution_metadata?.generator || {};

  if (!summary.available) {
    const failed = status === 'FAILED';
    const incomplete = status === 'INCOMPLETE';
    return (
      <Card>
        <CardContent style={{ padding: '1rem' }}>
          <strong>{failed ? 'Evaluation failed' : incomplete ? 'Evaluation incomplete' : 'Evaluation unavailable'}</strong>
          <p style={{ margin: '0.45rem 0 0', color: 'var(--text-secondary)' }}>
            {failed
              ? 'The generated data is available, but its quality was not evaluated successfully.'
              : incomplete
                ? 'There are not enough completed evaluation results to show a summary.'
                : 'No measured evaluation results are available for this generation.'}
          </p>
          {report.error_message && <p style={{ marginBottom: 0, color: 'var(--error-color)' }}>{report.error_message}</p>}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.8rem' }}>
          <div>
            <strong>Latest evaluation</strong>
            {status && status !== 'UNKNOWN' && <span style={{ marginLeft: '0.65rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{status}</span>}
            {status && status !== 'UNKNOWN' && <span style={{ marginLeft: '0.65rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{qualityDecisionText(status, report.quality_accepted ?? report.passed)}</span>}
          </div>
          {(generator.actual_generator || generator.requested_generator) && (
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
              Generator: {metricText(generator.actual_generator || generator.requested_generator)}
              {generator.requested_generator && generator.actual_generator && generator.requested_generator !== generator.actual_generator
                ? ` (requested ${generator.requested_generator})`
                : ''}
            </span>
          )}
        </div>
        {summary.legacy && <p style={{ margin: '0 0 0.65rem', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Showing scores saved by the previous evaluator; these historical scores are not recalculated.</p>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(155px, 1fr))', gap: '0.65rem' }}>
          {summary.items.map((item) => (
            <div key={item.label} style={{ padding: '0.75rem', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.68rem', textTransform: 'uppercase' }}>{item.label}</div>
              <div style={{ color: 'var(--text-primary)', fontWeight: 600, margin: '0.25rem 0' }}>{item.value}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.72rem' }}>{item.detail}</div>
            </div>
          ))}
        </div>
        <p style={{ margin: '0.7rem 0 0', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
          Raw indicators only. Privacy measurements do not establish anonymity or differential privacy.
        </p>
        {report.error_message && <p style={{ color: 'var(--error-color)', marginBottom: 0 }}>{report.error_message}</p>}
      </CardContent>
    </Card>
  );
}
