"""
Background training jobs for the analytics API.
Only one job runs at a time to avoid memory contention.
"""
import os
import threading
import datetime
from typing import Optional

from config.ticker_universe import all_symbols
from training.train_all import train_ticker
from training.train_universal import run_training

PRESETS = {
    'quick': {'lstm_epochs': 15, 'ppo_timesteps': 10_000, 'period': '3y', 'portfolio_rl_steps': 40_000},
    'standard': {'lstm_epochs': 50, 'ppo_timesteps': 50_000, 'period': '5y', 'portfolio_rl_steps': 120_000},
}

_lock = threading.Lock()
_state = {
    'status': 'idle',
    'job_type': None,
    'preset': None,
    'started_at': None,
    'finished_at': None,
    'progress': {'current': 0, 'total': 0, 'current_ticker': '', 'message': ''},
    'results': {},
    'error': None,
}


def _models_dir():
    return os.path.join(os.path.dirname(__file__), '..', 'models')


def get_status():
    with _lock:
        return dict(_state)


def is_running():
    with _lock:
        return _state['status'] == 'running'


def _set_progress(current, total, ticker='', message=''):
    with _lock:
        _state['progress'] = {
            'current': current,
            'total': total,
            'current_ticker': ticker,
            'message': message,
        }


def _finish(status, error=None):
    with _lock:
        _state['status'] = status
        _state['finished_at'] = datetime.datetime.utcnow().isoformat()
        _state['error'] = error
        _state['progress']['message'] = error or ('Completed' if status == 'completed' else '')


def _run_tickers(tickers, preset_name, train_universal_after=False):
    cfg = PRESETS.get(preset_name, PRESETS['quick'])
    save_dir = _models_dir()
    results = {}
    total = len(tickers) + (1 if train_universal_after else 0)
    _set_progress(0, max(total, 1), '', 'Starting...')

    for i, t in enumerate(tickers):
        _set_progress(i, total, t, f'Training {t}...')
        try:
            ok = train_ticker(
                t,
                period=cfg['period'],
                interval='1d',
                lstm_epochs=cfg['lstm_epochs'],
                ppo_timesteps=cfg['ppo_timesteps'],
                save_dir=save_dir,
            )
            results[t] = 'OK' if ok else 'FAILED (no data)'
        except Exception as e:
            results[t] = f'ERROR: {e}'

        with _lock:
            _state['results'][t] = results[t]

        _invalidate_ticker_cache(t)

    if train_universal_after:
        _set_progress(total, total, '', 'Training universal hybrid models...')
        try:
            run_training(
                tickers=tickers,
                period=cfg['period'],
                interval='1d',
                save_dir=save_dir,
                lstm_epochs=min(cfg['lstm_epochs'], 30),
                rf_estimators=300,
            )
            results['_universal'] = 'OK'
        except Exception as e:
            results['_universal'] = f'ERROR: {e}'
        with _lock:
            _state['results']['_universal'] = results['_universal']

    with _lock:
        _state['results'] = results
    _set_progress(total, total, '', 'Done')
    return results


def _invalidate_ticker_cache(ticker: str):
    try:
        import api as api_mod
        api_mod.engine_cache.pop(ticker.upper(), None)
        api_mod.engine_status.pop(ticker.upper(), None)
        api_mod.engine_errors.pop(ticker.upper(), None)
    except Exception:
        pass


def _worker(job_type: str, preset: str, ticker: Optional[str], tickers: Optional[list]):
    try:
        if job_type == 'ticker':
            if not ticker:
                raise ValueError('ticker is required')
            _run_tickers([ticker.upper()], preset, train_universal_after=False)
        elif job_type == 'universe':
            _run_tickers(all_symbols(), preset, train_universal_after=True)
        elif job_type == 'universal':
            cfg = PRESETS.get(preset, PRESETS['quick'])
            _set_progress(0, 1, '', 'Training universal models...')
            run_training(
                tickers=all_symbols(),
                period=cfg['period'],
                interval='1d',
                save_dir=_models_dir(),
                lstm_epochs=min(cfg['lstm_epochs'], 30),
                rf_estimators=300,
            )
            with _lock:
                _state['results'] = {'_universal': 'OK'}
            _set_progress(1, 1, '', 'Done')
        elif job_type == 'portfolio':
            if not tickers:
                raise ValueError('tickers list is required')
            syms = [str(t).upper().strip() for t in tickers if str(t).strip()]
            _run_tickers(syms, preset, train_universal_after=False)
        elif job_type == 'portfolio_rl':
            cfg = PRESETS.get(preset, PRESETS['quick'])
            _set_progress(0, 1, '', 'Training portfolio allocation PPO (full universe)...')
            from training.train_portfolio_rl import run_training as run_portfolio_rl
            result = run_portfolio_rl(
                tickers=all_symbols(),
                timesteps=cfg.get('portfolio_rl_steps', 40_000),
                period_years=5 if cfg['period'] == '5y' else 3,
                save_dir=_models_dir(),
            )
            with _lock:
                _state['results'] = {
                    '_portfolio_rl': 'OK',
                    'symbols': result.get('tickers', 0),
                }
            _set_progress(1, 1, '', 'Done')
            try:
                import api as api_mod
                api_mod.analyze_cache.clear()
            except Exception:
                pass
        else:
            raise ValueError(f'Unknown job_type: {job_type}')
        _finish('completed')
    except Exception as e:
        _finish('failed', str(e))


def start_job(job_type: str, preset: str = 'quick', ticker: Optional[str] = None, tickers: Optional[list] = None):
    preset = preset if preset in PRESETS else 'quick'
    with _lock:
        if _state['status'] == 'running':
            return False, 'A training job is already running'
        _state['status'] = 'running'
        _state['job_type'] = job_type
        _state['preset'] = preset
        _state['started_at'] = datetime.datetime.utcnow().isoformat()
        _state['finished_at'] = None
        _state['results'] = {}
        _state['error'] = None
        _state['progress'] = {'current': 0, 'total': 0, 'current_ticker': '', 'message': 'Starting...'}

    thread = threading.Thread(
        target=_worker,
        args=(job_type, preset, ticker, tickers),
        daemon=True,
    )
    thread.start()
    return True, 'Training started'
