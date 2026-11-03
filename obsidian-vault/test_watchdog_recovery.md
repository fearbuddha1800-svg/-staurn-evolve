---
slug: test_watchdog_recovery
type: note
graph: gitnexus
---

"""Supervisor regressions. All processes mocked; no engine is launched."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

PATH = Path.home() / '.hermes/scripts/signal-relay-watchdog.py'
spec = spec_from_file_location('recovery_watchdog', PATH)
wd = module_from_spec(spec)
spec.loader.exec_module(wd)


@pytest.mark.parametrize('marker', ['MAINTENANCE', 'STOP'])
def test_hold_prevents_launches(tmp_path, marker):
    (tmp_path / marker).write_text('hold')
    with patch.object(wd, 'BASE', str(tmp_path)), patch.object(wd, '_run_components') as run:
        wd.main()
    run.assert_not_called()


def test_invalid_config_prevents_launches(tmp_path):
    (tmp_path / 'SYSTEM_AUTOSTART_ALLOWED').write_text('1')
    (tmp_path / 'config.json').write_text('{invalid')
    with patch.object(wd, 'BASE', str(tmp_path)), patch.object(wd, '_run_components') as run:
        with pytest.raises(json.JSONDecodeError):
            wd.main()
    run.assert_not_called()


def test_supervisor_is_single_flight(tmp_path):
    with patch.object(wd, 'BASE', str(tmp_path)):
        first = wd._acquire_supervisor_lock()
        assert first is not None
        try:
            assert wd._acquire_supervisor_lock() is None
        finally:
            first.close()
        second = wd._acquire_supervisor_lock()
        assert second is not None
        second.close()


def process(cmdline, cwd, name='python.exe'):
    return SimpleNamespace(info={'pid': 123, 'name': name, 'cmdline': cmdline, 'cwd': str(cwd)})


def test_process_identity_exact_checkout(tmp_path):
    fake = process(['python.exe', 'daemon.py'], tmp_path)
    with patch.object(wd, 'BASE', str(tmp_path)), patch.object(wd.psutil, 'process_iter', return_value=[fake]):
        assert wd._running('daemon.py')
        assert not wd._running('manage.py')


def test_similar_basename_not_a_match(tmp_path):
    fake = process(['python.exe', 'not_daemon.py'], tmp_path)
    with patch.object(wd, 'BASE', str(tmp_path)), patch.object(wd.psutil, 'process_iter', return_value=[fake]):
        assert not wd._running('daemon.py')


def test_other_checkout_not_a_match(tmp_path):
    fake = process(['python.exe', 'daemon.py'], tmp_path / 'other')
    with patch.object(wd, 'BASE', str(tmp_path)), patch.object(wd.psutil, 'process_iter', return_value=[fake]):
        assert not wd._running('daemon.py')


def test_invalid_python_never_launches(tmp_path):
    (tmp_path / 'cockpit.py').write_text('<style> broken')
    with patch.object(wd, 'BASE', str(tmp_path)), patch.object(wd.subprocess, 'Popen') as popen:
        with pytest.raises(SyntaxError):
            wd._start('cockpit.py')
    popen.assert_not_called()


def test_launch_strips_shadow_pythonpath(tmp_path):
    (tmp_path / 'cockpit.py').write_text('print(1)')
    with patch.object(wd, 'BASE', str(tmp_path)), patch.dict(wd.os.environ, {'PYTHONPATH': 'broken'}), patch.object(wd.subprocess, 'Popen') as popen:
        wd._start('cockpit.py')
    assert 'PYTHONPATH' not in popen.call_args.kwargs['env']
    assert popen.call_args.args[0] == [wd.PY, '-u', 'cockpit.py']


def test_one_component_failure_does_not_kill_others():
    seen = []
    def launch(name, args=()):
        seen.append(name)
        if name == 'daemon.py':
            raise SyntaxError('broken dependency')
    with patch.object(wd, '_running', return_value=False), patch.object(wd, '_start', side_effect=launch), patch.object(wd, '_refresh_news'), patch.object(wd.subprocess, 'run'):
        wd._run_components()
    assert 'manage.py' in seen
    assert 'cockpit.py' in seen
    assert len(seen) == 7

