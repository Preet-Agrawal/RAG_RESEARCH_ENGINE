import { STRATEGIES } from '../constants/strategies.js';

export default function StrategySelector({ value, onChange, disabled }) {
  return (
    <div className="strategy-selector">
      <label htmlFor="strategy-select" className="strategy-label">
        Recovery strategy
      </label>
      <select
        id="strategy-select"
        className="strategy-select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
      >
        {STRATEGIES.map((s) => (
          <option key={s.id} value={s.id}>
            {s.recommended ? `★ ${s.name}` : s.name}
          </option>
        ))}
      </select>
      <p className="strategy-hint">
        {STRATEGIES.find((s) => s.id === value)?.description || ''}
      </p>
    </div>
  );
}
