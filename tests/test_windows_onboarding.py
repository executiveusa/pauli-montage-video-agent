from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsOnboardingContractTests(unittest.TestCase):
    def test_setup_keeps_runtime_and_media_on_e_drive_by_default(self):
        setup = (ROOT / "scripts" / "setup_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('E:\\MONTAGE_MEDIA', setup)
        self.assertIn('E:\\MONTAGE_RUNTIME', setup)
        self.assertIn('faster-whisper', setup)
        self.assertIn('Gyan.FFmpeg', setup)
        self.assertIn('Start-Montage.cmd', setup)

    def test_setup_uses_isolated_target_packages_instead_of_windows_venv(self):
        setup = (ROOT / "scripts" / "setup_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('$Packages = Join-Path $RuntimeRoot "python-packages"', setup)
        self.assertIn('python-executable.txt', setup)
        self.assertIn('"--target", $Packages, "faster-whisper"', setup)
        self.assertIn('Removing obsolete/broken Montage .venv only.', setup)
        self.assertIn('Refreshing Montage-only Python packages.', setup)

    def test_setup_selects_clean_python_outside_activated_agent_venvs(self):
        setup = (ROOT / "scripts" / "setup_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('function Find-CleanPython', setup)
        self.assertIn('uv python find 3.11', setup)
        self.assertIn('$RuntimePython -match \'\\\\hermes\\\\\'', setup)
        self.assertIn('$RuntimePython -match \'\\\\venv\\\\\'', setup)
        self.assertIn('$env:PYTHONNOUSERSITE = "1"', setup)

    def test_whisper_model_is_downloaded_to_explicit_local_directory(self):
        prewarm = (ROOT / "scripts" / "prewarm_whisper.py").read_text(encoding="utf-8")
        start = (ROOT / "scripts" / "start_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('download_model(args.model, output_dir=str(model_dir))', prewarm)
        self.assertIn('Set-Location $ModelCache', start)
        self.assertIn('HF_HOME', start)

    def test_launcher_stays_loopback_only_and_supports_isolated_runtime(self):
        start = (ROOT / "scripts" / "start_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('127.0.0.1', start)
        self.assertIn('pauli-montage-video-agent.vercel.app/studio', start)
        self.assertIn('MONTAGE_LOCAL_WORKSPACE', start)
        self.assertIn('MONTAGE_MODEL_CACHE', start)
        self.assertIn('python-executable.txt', start)
        self.assertIn('PYTHONPATH', start)

    def test_quickstart_names_real_asc3nd_source_and_zero_credit_acceptance(self):
        quickstart = (ROOT / "docs" / "ASC3ND_LOCAL_FOOTAGE_QUICKSTART.md").read_text(encoding="utf-8")
        self.assertIn('vc(1).mp4', quickstart)
        self.assertIn('Why We Started', quickstart)
        self.assertIn('$0 paid editor/Descript AI credits', quickstart)


if __name__ == "__main__":
    unittest.main()
