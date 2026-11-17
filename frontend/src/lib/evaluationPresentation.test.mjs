import test from 'node:test';
import assert from 'node:assert/strict';

import { evaluationSummary, metricText, qualityDecisionText } from './evaluationPresentation.mjs';

test('zero remains a measured zero and missing values remain unavailable', () => {
  assert.equal(metricText(0), '0');
  assert.equal(metricText(null), 'Unavailable');
  assert.equal(metricText(undefined), 'Unavailable');
});

test('failed and incomplete evaluations cannot appear accepted', () => {
  assert.equal(qualityDecisionText('FAILED', true), 'Not evaluated (failed)');
  assert.equal(qualityDecisionText('INCOMPLETE', true), 'Incomplete');
  assert.equal(qualityDecisionText('COMPLETED', null), 'No decision');
});

test('completed decisions preserve explicit true and false states', () => {
  assert.equal(qualityDecisionText('COMPLETED', true), 'Accepted');
  assert.equal(qualityDecisionText('COMPLETED', false), 'Not accepted');
});

test('empty legacy report has no fabricated summary metrics', () => {
  const summary = evaluationSummary({ evaluation_status: 'UNKNOWN' });
  assert.equal(summary.available, false);
  assert.equal(summary.items.length, 4);
  assert.ok(summary.items.every((item) => item.value === 'Unavailable'));
});

test('summary preserves measured zeroes and raw TSTR versus TRTR metrics', () => {
  const summary = evaluationSummary({
    evaluation_status: 'COMPLETED',
    schema_details: { valid: true, issues: [] },
    statistical_details: { columns: { balance: { status: 'COMPLETED' } } },
    privacy_details: { metrics: { exact_match: { synthetic_rows_with_real_match: 0 } } },
    ml_utility_details: {
      status: 'COMPLETED',
      task: 'classification',
      metrics: { TRTR: { f1_weighted: 0.8 }, TSTR: { f1_weighted: 0 } },
    },
  });
  assert.equal(summary.available, true);
  assert.equal(summary.items[0].value, 'Valid');
  assert.equal(summary.items[1].value, '1 / 1 columns');
  assert.equal(summary.items[2].value, '0');
  assert.equal(summary.items[3].value, '0 / 0.8');
});

test('historical scores are shown only when actually stored', () => {
  const summary = evaluationSummary({ report: {
    statistical_score: 0,
    privacy_score: 0.72,
    ml_utility_score: null,
    overall_score: 0.4,
  } });
  assert.equal(summary.available, true);
  assert.equal(summary.legacy, true);
  assert.deepEqual(summary.items.map(({ label, value }) => [label, value]), [
    ['Statistical score', '0'],
    ['Privacy score', '0.72'],
    ['Overall score', '0.4'],
  ]);
});
