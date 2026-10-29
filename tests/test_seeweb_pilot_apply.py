"""Prove del cambio mirato Seeweb, con file e servizi simulati."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "bin/ads-seeweb-pilot-apply.py"
SPEC = importlib.util.spec_from_file_location("ads_seeweb_pilot_apply", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PilotApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.targets = {
            "candidate-10-ads.conf": self.root / "10-ads.conf",
            "candidate-nftables.conf": self.root / "nftables.conf",
        }
        self.old = {
            "candidate-10-ads.conf": b"rsyslog baseline\n",
            "candidate-nftables.conf": b"nftables baseline\n",
        }
        self.new = {
            "candidate-10-ads.conf": b"rsyslog 127.0.0.2 candidato\n",
            "candidate-nftables.conf": b"nftables 127.0.0.2 candidato\n",
        }
        for name, target in self.targets.items():
            target.write_bytes(self.old[name])
            (self.bundle / name).write_bytes(self.new[name])
        manifest = {
            "source": "127.0.0.2",
            "destination": "127.0.0.1",
            "nft_active_baseline_sha256": "0" * 64,
            "files": {
                name: {
                    "sha256": hashlib.sha256(self.new[name]).hexdigest(),
                    "live_sha256": hashlib.sha256(self.old[name]).hexdigest(),
                }
                for name in self.targets
            },
        }
        (self.bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.calls: list[tuple[str, ...]] = []
        self.destination_patch = patch.object(MODULE, "check_local_destination")
        self.tables_patch = patch.object(MODULE, "check_nft_tables")
        self.ruleset_patch = patch.object(MODULE, "check_nft_ruleset")
        self.destination_patch.start()
        self.tables_patch.start()
        self.ruleset_mock = self.ruleset_patch.start()
        self.addCleanup(self.destination_patch.stop)
        self.addCleanup(self.tables_patch.stop)
        self.addCleanup(self.ruleset_patch.stop)

    def fake_run(self, *command: str) -> None:
        self.calls.append(command)

    def assert_old(self) -> None:
        for name, target in self.targets.items():
            self.assertEqual(target.read_bytes(), self.old[name])

    def test_check_verifica_due_impronte_e_sintassi(self) -> None:
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            MODULE.check(self.bundle, self.targets)
        self.ruleset_mock.assert_called_once_with("0" * 64)
        self.assertEqual(
            [call[0] for call in self.calls], ["nft", "rsyslogd", "systemctl", "systemctl"]
        )
        self.assert_old()

    def test_check_rifiuta_candidato_alterato(self) -> None:
        (self.bundle / "candidate-nftables.conf").write_bytes(b"alterato\n")
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            with self.assertRaisesRegex(MODULE.PilotError, "impronta candidata diversa"):
                MODULE.check(self.bundle, self.targets)
        self.assertEqual(self.calls, [])
        self.assert_old()

    def test_check_rifiuta_live_cambiato(self) -> None:
        self.targets["candidate-10-ads.conf"].write_bytes(b"live cambiato\n")
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            with self.assertRaisesRegex(MODULE.PilotError, "impronta live diversa"):
                MODULE.check(self.bundle, self.targets)
        self.assertEqual(self.calls, [])

    def test_check_rifiuta_mittente_mancante_anche_con_hash_valido(self) -> None:
        name = "candidate-10-ads.conf"
        candidate = b"rsyslog senza mittente\n"
        (self.bundle / name).write_bytes(candidate)
        manifest = json.loads((self.bundle / "manifest.json").read_text(encoding="utf-8"))
        manifest["files"][name]["sha256"] = hashlib.sha256(candidate).hexdigest()
        (self.bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(MODULE.PilotError, "mittente assente"):
            MODULE.load_bundle(self.bundle, self.targets)

    def test_apply_conserva_backup_e_installa_due_candidati(self) -> None:
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            backup = MODULE.apply(self.bundle, self.targets, self.root / "backups")
        for name, target in self.targets.items():
            self.assertEqual(target.read_bytes(), self.new[name])
            self.assertEqual((backup / name).read_bytes(), self.old[name])
        self.assertIn(("nft", "-f", str(self.targets["candidate-nftables.conf"])), self.calls)
        self.assertIn(("systemctl", "restart", "rsyslog"), self.calls)

    def test_rollback_ripristina_entrambi_dopo_pilota_riuscito(self) -> None:
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            backup = MODULE.apply(self.bundle, self.targets, self.root / "backups")
            MODULE.rollback(self.root / "backups", backup.name, self.targets)
        self.assert_old()
        self.assertTrue((backup / "metadata.json").is_file())

    def test_rollback_rifiuta_live_successivamente_alterato(self) -> None:
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            backup = MODULE.apply(self.bundle, self.targets, self.root / "backups")
        name = "candidate-10-ads.conf"
        self.targets[name].write_bytes(b"terza versione\n")
        with self.assertRaisesRegex(MODULE.PilotError, "live diverso dal pilota"):
            MODULE.rollback(self.root / "backups", backup.name, self.targets)
        self.assertEqual(self.targets[name].read_bytes(), b"terza versione\n")
        self.assertEqual(
            self.targets["candidate-nftables.conf"].read_bytes(),
            self.new["candidate-nftables.conf"],
        )

    def test_rollback_fallito_reintegra_il_pilota(self) -> None:
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            backup = MODULE.apply(self.bundle, self.targets, self.root / "backups")
        nft_apply = ("nft", "-f", str(self.targets["candidate-nftables.conf"]))
        count = 0

        def fail_first_nft(*command: str) -> None:
            nonlocal count
            if command == nft_apply:
                count += 1
                if count == 1:
                    raise MODULE.PilotError("nft simulato")

        with patch.object(MODULE, "run", side_effect=fail_first_nft):
            with self.assertRaisesRegex(MODULE.PilotError, "pilota reintegrato"):
                MODULE.rollback(self.root / "backups", backup.name, self.targets)
        for name, target in self.targets.items():
            self.assertEqual(target.read_bytes(), self.new[name])

    def test_apply_ripristina_se_restart_rsyslog_fallisce(self) -> None:
        def fail_restart(*command: str) -> None:
            self.calls.append(command)
            if command == ("systemctl", "restart", "rsyslog") and self.calls.count(command) == 1:
                raise MODULE.PilotError("restart simulato")

        with patch.object(MODULE, "run", side_effect=fail_restart):
            with self.assertRaisesRegex(MODULE.PilotError, "ripristino eseguito"):
                MODULE.apply(self.bundle, self.targets, self.root / "backups")
        self.assert_old()
        self.assertEqual(self.calls.count(("systemctl", "restart", "rsyslog")), 2)

    def test_apply_ripristina_entrambi_se_nft_fallisce(self) -> None:
        nft_apply = ("nft", "-f", str(self.targets["candidate-nftables.conf"]))

        def fail_nft(*command: str) -> None:
            self.calls.append(command)
            if command == nft_apply and self.calls.count(command) == 1:
                raise MODULE.PilotError("nft simulato")

        with patch.object(MODULE, "run", side_effect=fail_nft):
            with self.assertRaisesRegex(MODULE.PilotError, "ripristino eseguito"):
                MODULE.apply(self.bundle, self.targets, self.root / "backups")
        self.assert_old()
        self.assertEqual(self.calls.count(nft_apply), 2)

    def test_apply_rifiuta_candidato_cambiato_dopo_check(self) -> None:
        def mutate_at_check(*command: str) -> None:
            self.calls.append(command)
            if command[:2] == ("systemctl", "is-active") and command[-1] == "nftables":
                (self.bundle / "candidate-10-ads.conf").write_bytes(b"cambiato dopo check\n")

        with patch.object(MODULE, "run", side_effect=mutate_at_check):
            with self.assertRaisesRegex(MODULE.PilotError, "ripristino eseguito"):
                MODULE.apply(self.bundle, self.targets, self.root / "backups")
        self.assert_old()

    def test_apply_ripristina_rsyslog_se_cambia_il_ruleset_attivo(self) -> None:
        self.ruleset_mock.side_effect = [None, MODULE.PilotError("drift ruleset simulato")]
        with patch.object(MODULE, "run", side_effect=self.fake_run):
            with self.assertRaisesRegex(MODULE.PilotError, "ripristino eseguito"):
                MODULE.apply(self.bundle, self.targets, self.root / "backups")
        self.assert_old()
        self.assertEqual(self.ruleset_mock.call_count, 2)

    def test_destinazione_deve_essere_assegnata_alla_vm(self) -> None:
        self.destination_patch.stop()
        response = SimpleNamespace(returncode=0, stdout=b'[{"addr_info": []}]')
        with patch.object(MODULE.subprocess, "run", return_value=response):
            with self.assertRaisesRegex(MODULE.PilotError, "destinazione"):
                MODULE.check_local_destination("127.0.0.1")

    def test_tabelle_estranee_fermano_il_pilota(self) -> None:
        self.tables_patch.stop()
        listing = {"nftables": [
            {"table": {"family": "inet", "name": "filter"}},
            {"table": {"family": "ip", "name": "other"}},
        ]}
        response = SimpleNamespace(returncode=0, stdout=json.dumps(listing).encode())
        with patch.object(MODULE.subprocess, "run", return_value=response):
            with self.assertRaisesRegex(MODULE.PilotError, "tabelle nftables diverse"):
                MODULE.check_nft_tables()

    def test_impronta_ruleset_ignora_handle_ma_rileva_regola_diversa(self) -> None:
        first = {"nftables": [
            {"metainfo": {"version": "a"}},
            {"table": {"family": "inet", "name": "filter"}},
            {"rule": {"family": "inet", "table": "filter", "chain": "input",
                      "handle": 3, "expr": [{"accept": None}]}},
        ]}
        second = json.loads(json.dumps(first))
        second["nftables"][0]["metainfo"]["version"] = "b"
        second["nftables"][2]["rule"]["handle"] = 99
        self.assertEqual(
            MODULE.nft_ruleset_digest(json.dumps(first).encode()),
            MODULE.nft_ruleset_digest(json.dumps(second).encode()),
        )
        second["nftables"][2]["rule"]["expr"] = [{"drop": None}]
        self.assertNotEqual(
            MODULE.nft_ruleset_digest(json.dumps(first).encode()),
            MODULE.nft_ruleset_digest(json.dumps(second).encode()),
        )

    def test_ruleset_attivo_diverso_ferma_il_pilota(self) -> None:
        self.ruleset_patch.stop()
        response = SimpleNamespace(returncode=0, stdout=b'{"nftables": []}')
        with patch.object(MODULE.subprocess, "run", return_value=response):
            with self.assertRaisesRegex(MODULE.PilotError, "ruleset nftables attivo diverso"):
                MODULE.check_nft_ruleset("0" * 64)

    def test_lock_simbolico_rifiutato_senza_cambiare_il_bersaglio(self) -> None:
        victim = self.root / "victim"
        victim.write_text("contenuto intatto\n", encoding="utf-8")
        victim.chmod(0o644)
        lock = self.root / "lock"
        lock.symlink_to(victim)
        with (
            patch.object(MODULE, "LOCK", lock),
            patch.object(MODULE.os, "geteuid", return_value=0),
            patch.object(MODULE, "check", return_value={}),
            patch.object(MODULE.sys, "argv", ["pilot", "--bundle", str(self.bundle), "--check"]),
        ):
            with self.assertRaisesRegex(MODULE.PilotError, "lock"):
                MODULE.main()
        self.assertEqual(victim.stat().st_mode & 0o777, 0o644)
        self.assertEqual(victim.read_text(encoding="utf-8"), "contenuto intatto\n")

    @unittest.skipUnless(os.geteuid() == 0, "il pilot richiede root")
    def test_lock_regolare_root_consente_il_controllo(self) -> None:
        lock = self.root / "lock"
        with (
            patch.object(MODULE, "LOCK", lock),
            patch.object(MODULE, "check", return_value={}),
            patch.object(MODULE.sys, "argv", ["pilot", "--bundle", str(self.bundle), "--check"]),
        ):
            self.assertEqual(MODULE.main(), 0)
        self.assertEqual(lock.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
