import re
import os

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/src/components/PortfolioDashboard.jsx'))
with open(path, 'r', encoding='utf-8') as f:
    code = f.read()

old_corrupted = '''          </div>
    const list = Array.isArray(recommendations) ? recommendations : [];
    const activeRecs = list.filter((rec) => rec && (rec.id || rec.action) && !dismissedRecommendations.includes(rec.id));
        </div>
      </div>
    );
  }
          <span className="text-xs text-gray-400 font-mono">{activeRecs.length} recommendations available</span>
  function renderRecommendations() {
    return (
          {activeRecs.map((rec, idx) => (
            <RecommendationCard
              key={rec.id || idx}
              rec={rec}
              onDismiss={() => rec.id && setDismissedRecommendations((current) => [...current, rec.id])}
            />
          ))}
          <span className="text-xs text-gray-500">{recommendations.length} recommendations generated</span>
        {activeRecs.length === 0 && (
        <div className="space-y-4">
          {recommendations.filter((rec) => !dismissedRecommendations.includes(rec.id)).map((rec) => (
            <p className="text-gray-300 font-medium">No immediate recommendations requiring review.</p>
            <p className="text-xs text-gray-500 mt-1">Your portfolio risk allocation and signal alignment appear optimal.</p>
          ))}
        </div>
        {recommendations.length === 0 && (
          <div className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-8 text-center">
            <Brain className="w-10 h-10 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No recommendations generated. Portfolio appears well-balanced.</p>
          </div>
        )}
      </div>
    );
  }'''

new_clean = '''        </div>
      </div>
    );
  }

  function renderRecommendations() {
    const list = Array.isArray(recommendations) ? recommendations : [];
    const activeRecs = list.filter((rec) => rec && (rec.id || rec.action || rec.title) && !dismissedRecommendations.includes(rec.id));

    return (
      <div className="space-y-6">
        <div className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-6">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-semibold text-white">Portfolio Recommendations</h3>
              <p className="text-xs text-gray-400 mt-1">Evidence-backed quantitative suggestions for your portfolio.</p>
            </div>
            <span className="text-xs text-gray-400 font-mono">{activeRecs.length} available</span>
          </div>

          {activeRecs.length > 0 ? (
            <div className="space-y-4">
              {activeRecs.map((rec, idx) => (
                <RecommendationCard
                  key={rec.id || idx}
                  rec={rec}
                  onDismiss={() => rec.id && setDismissedRecommendations((current) => [...current, rec.id])}
                />
              ))}
            </div>
          ) : (
            <div className="bg-gray-800/30 border border-gray-700/30 rounded-xl p-8 text-center">
              <Brain className="w-10 h-10 text-gray-500 mx-auto mb-3" />
              <p className="text-gray-300 font-medium">No immediate recommendations requiring review.</p>
              <p className="text-xs text-gray-500 mt-1">Your portfolio risk allocation and signal alignment appear optimal.</p>
            </div>
          )}
        </div>
      </div>
    );
  }'''

if old_corrupted in code:
    code = code.replace(old_corrupted, new_clean)
else:
    code = re.sub(r'const list = Array\.isArray\(recommendations\)[\s\S]*?function renderRecommendations\(\)\s*\{[\s\S]*?\n  \}', new_clean.replace('        </div>\n      </div>\n    );\n  }\n\n  ', ''), code)

new_rec_card = '''const RecommendationCard = ({ rec, onDismiss }) => {
  if (!rec) return null;
  const confidence = String(rec.confidence || rec.priority || 'medium').toLowerCase();
  const severityColors = {
    high: 'border-rose-500 bg-rose-500/5',
    medium: 'border-amber-500 bg-amber-500/5',
    low: 'border-blue-500 bg-blue-500/5',
    experimental: 'border-purple-500 bg-purple-500/5',
  };
  const colorClass = severityColors[confidence] || 'border-gray-500 bg-gray-500/5';

  const actionLabel = rec.action ? String(rec.action).replace(/_/g, ' ') : 'REVIEW';
  const assetLabel = rec.asset || rec.ticker || '';
  const descriptionText = rec.reason || rec.description || rec.summary || 'Review this portfolio insight.';

  return (
    <div className={`border-l-2 rounded-xl p-4 ${colorClass}`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="text-xs font-bold uppercase text-gray-400">{actionLabel}</span>
          {assetLabel && <span className="text-sm font-bold text-white ml-2">{assetLabel}</span>}
        </div>
        <span className={`text-[10px] uppercase font-bold px-2 py-1 rounded ${
          confidence === 'high' ? 'text-rose-300 bg-rose-500/10' :
          confidence === 'medium' ? 'text-amber-300 bg-amber-500/10' :
          'text-blue-300 bg-blue-500/10'
        }`}>{confidence}</span>
      </div>
      {rec.title && <h4 className="text-sm font-semibold text-white mb-1">{rec.title}</h4>}
      <p className="text-sm text-gray-300 mb-2">{descriptionText}</p>
      {rec.expected_impact && (
        <p className="text-xs text-indigo-300 mb-2 font-medium">Expected Impact: {rec.expected_impact}</p>
      )}
      {rec.supporting_metrics && Object.keys(rec.supporting_metrics).length > 0 && (
        <div className="text-xs text-gray-500 mb-2 flex flex-wrap gap-x-3 gap-y-1">
          <span className="font-medium text-gray-400">Metrics:</span>
          {Object.entries(rec.supporting_metrics).map(([k, v]) => (
            <span key={k} className="text-gray-400">
              {k}: {typeof v === 'number' ? (v > 1 ? v.toFixed(2) : v.toFixed(4)) : String(v)}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mt-3">
        {onDismiss && (
          <button type="button" onClick={onDismiss} className="text-xs px-3 py-1.5 bg-gray-800/60 text-gray-400 rounded-lg hover:text-white transition-colors">
            Dismiss
          </button>
        )}
        {rec.supporting_models && (
          <span className="text-[10px] text-gray-600 ml-auto">
            Models: {Array.isArray(rec.supporting_models) ? rec.supporting_models.join(', ') : rec.supporting_models}
          </span>
        )}
      </div>
    </div>
  );
};'''

code = re.sub(r'const RecommendationCard = \(\{[\s\S]*?\n\};', new_rec_card, code)

with open(path, 'w', encoding='utf-8') as f:
    f.write(code)

print("Successfully fixed PortfolioDashboard.jsx")