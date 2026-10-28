"""Guardie del bundle Windows prima di usarlo su un pilota autorizzato."""

from xml.etree import ElementTree

from conftest import load_script

render = load_script("ads-render-windows.py")


def params(tmp_path, source, accounts):
    path = tmp_path / "parametri.yaml"
    path.write_text(
        source.replace("elenco_approvato: []", f"elenco_approvato: {accounts}"),
        encoding="utf-8",
    )
    return path


def run(tmp_path, path, *extra):
    dest = tmp_path / "bundle"
    code = render.main(
        [
            "--parametri",
            str(path),
            "--computer-name",
            "PILOT-01",
            "--destinazione",
            str(dest),
            *extra,
        ]
    )
    return code, dest


def test_senza_elenco_approvato_non_produce_bundle(tmp_path, params_text):
    code, dest = run(tmp_path, params(tmp_path, params_text, "[]"))
    assert code == 1
    assert not dest.exists()


def test_query_per_account_e_controlli_globali(tmp_path, params_text):
    code, dest = run(tmp_path, params(tmp_path, params_text, '["PILOT-01/ads_a", "EXAMPLE/ads_a"]'))
    assert code == 0
    conf = (dest / "fluent-bit.conf").read_text(encoding="utf-8")
    assert (dest / "ads-windows-queue-health.ps1").is_file()
    assert (dest / "ads-windows-pilot-preflight.ps1").is_file()
    assert (dest / "ads-windows-service-state.ps1").read_bytes() == (
        render.ROOT / "bin/ads-windows-service-state.ps1"
    ).read_bytes()
    assert (dest / "ads-windows-security-probe.ps1").read_bytes() == (
        render.ROOT / "bin/ads-windows-security-probe.ps1"
    ).read_bytes()
    query = next(line.split(None, 1)[1] for line in conf.splitlines() if "Event_Query" in line)
    selects = ElementTree.fromstring(query).findall(".//Select")
    assert len(selects) == 3
    assert all("TargetUserName" in (item.text or "") for item in selects[:2])
    assert all("TargetDomainName" in (item.text or "") for item in selects[:2])
    assert all("SubjectUserName" in (item.text or "") for item in selects[:2])
    assert all("SubjectDomainName" in (item.text or "") for item in selects[:2])
    assert all("EventID=4672" in (item.text or "") for item in selects[:2])
    assert all("EventID=4648" in (item.text or "") for item in selects[:2])
    assert "ads_a" in selects[0].text
    assert "PILOT-01" in selects[0].text
    assert "ads_a" in selects[1].text
    assert "EXAMPLE" in selects[1].text
    for item, domain in zip(selects[:2], ("PILOT-01", "EXAMPLE"), strict=True):
        for role in ("Target", "Subject"):
            assert (
                f"Data[@Name='{role}UserName']='ads_a' and "
                f"Data[@Name='{role}DomainName']='{domain}'"
            ) in item.text
    assert "1102" in selects[2].text
    assert "TargetUserName" not in selects[2].text
    assert "tls.verify_hostname       on" in conf
    assert "storage.total_limit_size" not in conf
    assert (dest / "ads.lua").read_bytes() == (render.SOURCE / "ads.lua").read_bytes()


def test_account_che_inietta_xpath_viene_rifiutato(tmp_path, params_text):
    bad = '["PILOT-01/ads_a\u0027 or 1=1"]'
    code, dest = run(tmp_path, params(tmp_path, params_text, bad))
    assert code == 1
    assert not dest.exists()


def test_account_duplicato_viene_rifiutato(tmp_path, params_text):
    duplicate = '["PILOT-01/ads_a", "pilot-01/ADS_A"]'
    code, dest = run(tmp_path, params(tmp_path, params_text, duplicate))
    assert code == 1
    assert not dest.exists()


def test_account_senza_dominio_viene_rifiutato(tmp_path, params_text):
    code, dest = run(tmp_path, params(tmp_path, params_text, '["ads_a"]'))
    assert code == 1
    assert not dest.exists()


def test_destinazione_tracciabile_viene_rifiutata(tmp_path, params_text):
    path = params(tmp_path, params_text, '["PILOT-01/ads_a"]')
    dest = render.ROOT / "config" / "windows-pilota" / "bundle-reale"
    code = render.main(
        ["--parametri", str(path), "--computer-name", "PILOT-01", "--destinazione", str(dest)]
    )
    assert code == 1
    assert not dest.exists()
