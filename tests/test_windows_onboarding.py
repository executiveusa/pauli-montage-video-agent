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

    def test_setup_recovers_when_windows_venv_ensurepip_fails(self):
        setup = (ROOT / "scripts" / "setup_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('Remove-Item -Recurse -Force $Venv', setup)
        self.assertIn('$FallbackPackages', setup)
        self.assertIn('python-executable.txt', setup)
        self.assertIn('"--target", $FallbackPackages, "faster-whisper"', setup)

    def test_whisper_cache_avoids_windows_symlink_requirement(self):
        setup = (ROOT / "scripts" / "setup_montage_windows.ps1").read_text(encoding="utf-8")
        start = (ROOT / "scripts" / "start_montage_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('HF_HUB_DISABLE_SYMLINKS', setup)
        self.assertIn('HF_HUB_DISABLE_SYMLINKS', start)
        self.assertIn('HF_HOME', setup)
        self.assertIn('HF_HOME', start)

    def test_launcher_stays_loopback_only_and_supports_fallback_runtime(self):
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
