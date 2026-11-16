import os, re

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/src/components/PortfolioDashboard.jsx'))
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

new_render_rec = '''  function renderRecommendations() {
    const list = Array.isArray(recommendations) ? recommendations : [];
    const activeRecs = list.filter((rec) => rec && (rec.id || rec.action) && !dismissedRecommendations.includes(rec.id));
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-white">Evidence-Backed Recommendations</h3>
          <span className="text-xs text-gray-500">{activeRecs.length} recommendations available</span>
        </div>
        <div className="space-y-4">
          {activeRecs.map((rec, idx) => (
            <RecommendationCard
              key={rec.id || idx}
              rec={rec}
              onDismiss={() => setDismissedRecommendations((current) => [...current, rec.id || idx])}
            />
          ))}
        </div>
        {activeRecs.length === 0 && (
          <div className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-8 text-center">
            <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No recommendations generated or all dismissed. Portfolio appears well-balanced.</p>
          </div>
        )}
      </div>
    );
  }'''

new_card = '''const RecommendationCard = ({ rec, onDismiss }) => {
  if (!rec) return null;
  const priority = String(rec.priority || rec.confidence || 'medium').toLowerCase();
  const severityColors = {
    high: 'border-rose-500 bg-rose-500/5',
    medium: 'border-amber-500 bg-amber-500/5',
    low: 'border-blue-500 bg-blue-500/5',
    experimental: 'border-purple-500 bg-purple-500/5',
  };
  const colorClass = severityColors[priority] || 'border-indigo-500 bg-indigo-500/5';
  const actionLabel = String(rec.action || rec.type || 'Notice').replace(/_/g, ' ');
  const assetName = rec.asset || rec.target || rec.ticker || '';
  const summaryText = rec.summary || rec.reason || rec.rationale || 'Review portfolio position for optimal allocation.';
  const metricsObj = rec.supporting_metrics || rec.evidence || rec.impact || {};
  const modelsList = rec.supporting_models || rec.models || [];

  const formatVal = (v) => {
    if (v == null) return 'N/A';
    if (typeof v === 'number') {
      return Number.isInteger(v) ? String(v) : v.toFixed(Math.abs(v) >= 1 ? 2 : 4);
    }
    if (typeof v === 'object') {
      try { return JSON.stringify(v); } catch { return '[Object]'; }
    }
    return String(v);
  };

  return (
    <div className={`border-l-2 rounded-xl p-4 ${colorClass}`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">{actionLabel}</span>
          {assetName && <span className="text-sm font-bold text-white ml-2">{assetName}</span>}
        </div>
        <span className={`text-[10px] uppercase font-bold px-2 py-1 rounded ${
          priority === 'high' ? 'text-rose-300 bg-rose-500/10' :
          priority === 'medium' ? 'text-amber-300 bg-amber-500/10' :
          'text-blue-300 bg-blue-500/10'
        }`}>{priority}</span>
      </div>
      <p className="text-sm text-gray-300 mb-2">{summaryText}</p>
      {typeof metricsObj === 'object' && metricsObj !== null && Object.keys(metricsObj).length > 0 && (
        <div className="text-xs text-gray-400 mb-2 flex flex-wrap gap-x-3 gap-y-1 bg-gray-900/40 p-2.5 rounded-lg border border-gray-800/40">
          <span className="font-semibold text-gray-300 w-full mb-0.5">Supporting Metrics:</span>
          {Object.entries(metricsObj).map(([k, v]) => (
            <span key={k} className="text-gray-400">
              <span className="text-gray-500">{k.replace(/_/g, ' ')}:</span>{' '}
              <span className="text-gray-200 font-mono">{formatVal(v)}</span>
            </span>
          ))}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2 mt-3 pt-2 border-t border-gray-800/40">
        {onDismiss && (
          <button type="button" onClick={onDismiss} className="text-xs px-3 py-1 bg-gray-800/60 text-gray-400 rounded-lg hover:text-white hover:bg-gray-800 transition-colors">
            Dismiss
          </button>
        )}
        {Array.isArray(modelsList) && modelsList.length > 0 && (
          <span className="text-[10px] text-gray-500 ml-auto">
            Models: {modelsList.join(', ')}
          </span>
        )}
      </div>
    </div>
  );
};'''

code = re.sub(r'function renderRecommendations\(\)\s*\{[\s\S]*?\n  \}', new_render_rec, code)
code = re.sub(r'const RecommendationCard = \(\{[\s\S]*?\n\};', new_card, code)

with open(path, 'w', encoding='utf-8') as f:
    f.write(code)

print("Fix applied successfully to PortfolioDashboard.jsx")