export function CompareResultsTable({ results, bestStrategy }) {
  if (!results?.length) return null;

  return (
    <div className="dashboard-panel">
      <div className="dashboard-header">
        <h3>Strategy comparison</h3>
        {bestStrategy && (
          <p className="dashboard-meta">
            Best: <span className="text-success">{bestStrategy}</span>
          </p>
        )}
      </div>
      <div className="table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Strategy</th>
              <th>Confidence</th>
              <th>Latency</th>
              <th>Answer (preview)</th>
            </tr>
          </thead>
          <tbody>
            {results.map((row, idx) => (
              <tr key={row.strategy} className={idx === 0 ? 'row-best' : ''}>
                <td>{idx + 1}</td>
                <td>
                  {idx === 0 && <span className="best-dot" title="Highest confidence" />}
                  {row.strategy}
                </td>
                <td>
                  <span
                    className={`badge ${
                      row.confidence >= 0.8
                        ? 'badge-success'
                        : row.confidence >= 0.5
                          ? 'badge-warn'
                          : 'badge-danger'
                    }`}
                  >
                    {Math.round((row.confidence || 0) * 100)}%
                  </span>
                </td>
                <td>{(row.latency || 0).toFixed(1)}s</td>
                <td className="answer-preview">{row.answer}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function BenchmarkResultsTable({ benchmark }) {
  if (!benchmark?.results) return null;

  const { summary, results, needleFact, totalLatency } = benchmark;

  return (
    <div className="dashboard-panel">
      <div className="dashboard-header">
        <h3>Needle-in-haystack benchmark</h3>
        {needleFact && <p className="dashboard-meta needle-fact">{needleFact}</p>}
      </div>

      {summary && (
        <div className="benchmark-summary-grid">
          <div className="stat-card stat-danger">
            <p className="stat-value">{summary.baselineAccuracy}%</p>
            <p className="stat-label">Baseline</p>
          </div>
          <div className="stat-card stat-success">
            <p className="stat-value">{summary.combinedAccuracy}%</p>
            <p className="stat-label">Combined</p>
          </div>
          <div className="stat-card stat-purple">
            <p className="stat-value">+{summary.improvement}%</p>
            <p className="stat-label">Improvement</p>
          </div>
        </div>
      )}

      <div className="table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th>Position</th>
              <th>Zone</th>
              <th>Baseline</th>
              <th>Combined</th>
              <th>Recovery</th>
            </tr>
          </thead>
          <tbody>
            {results.map((row) => (
              <tr
                key={row.positionPercent}
                className={row.positionZone === 'middle' ? 'row-middle' : ''}
              >
                <td className="mono">{row.positionPercent}%</td>
                <td>
                  <span
                    className={`zone-tag ${
                      row.positionZone === 'middle' ? 'zone-middle' : ''
                    }`}
                  >
                    {row.positionZone}
                  </span>
                </td>
                <td className={row.baselineFound ? 'text-success' : 'text-danger'}>
                  {row.baselineFound ? '✓' : '✗'}
                </td>
                <td className={row.combinedFound ? 'text-success' : 'text-danger'}>
                  {row.combinedFound ? '✓' : '✗'}
                </td>
                <td>
                  {row.recoverySuccess ? (
                    <span className="text-purple">Recovered</span>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {summary?.deadZonePositions?.length > 0 && (
        <p className="dead-zone-note">
          Dead zone recovery at: {summary.deadZonePositions.join('%, ')}%
        </p>
      )}

      {totalLatency != null && (
        <p className="dashboard-meta">Total latency: {totalLatency.toFixed(1)}s</p>
      )}
    </div>
  );
}

export default function Dashboard({ compareResults, benchmarkResults }) {
  if (!compareResults && !benchmarkResults) {
    return (
      <div className="dashboard-empty">
        <p>Run a strategy comparison or benchmark to see results here.</p>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {compareResults && (
        <CompareResultsTable
          results={compareResults.comparison}
          bestStrategy={compareResults.bestStrategy}
        />
      )}
      {benchmarkResults && (
        <BenchmarkResultsTable benchmark={benchmarkResults} />
      )}
    </div>
  );
}
