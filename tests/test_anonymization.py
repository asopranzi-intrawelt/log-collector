"""Il controllo privacy distingue le chiavi OData dagli indirizzi reali."""

import importlib.util

from conftest import ROOT


def test_chiave_redfish_e_email_reale_sulla_stessa_riga(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "test_anonymization_tool", ROOT / "tools" / "Test-Anonymization.py"
    )
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)

    real_mail = "utente" + "@" + "azienda.test"
    similar_mail = "Members" + "@" + "odata.com"
    sample = tmp_path / "sample.txt"
    sample.write_text(f"Members@odata.nextLink {real_mail} {similar_mail}\n", encoding="utf-8")
    patterns = {
        "reti_documentali_ammesse": [],
        "ip_ammessi": [],
        "prefissi_reali": [],
        "mac_ammessi_prefissi": [],
        "email_ammesse": [],
        "nomi_propri": [],
    }

    found, skipped = scanner.analizza(patterns, [(str(sample), "tracciato")])

    assert skipped == []
    assert [hit[2] for hit in found["EMAIL PERSONALE"]] == [real_mail, similar_mail]
