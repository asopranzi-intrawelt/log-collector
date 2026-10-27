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
    code, dest = run(tmp_path, params(tmp_path, params_text, '["ads_a", "ads_b"]'))
    assert code == 0
    conf = (dest / "fluent-bit.conf").read_text(encoding="utf-8")
    query = next(line.split(None, 1)[1] for line in conf.splitlines() if "Event_Query" in line)
    selects = ElementTree.fromstring(query).findall(".//Select")
    assert len(selects) == 3
    assert all("TargetUserName" in (item.text or "") for item in selects[:2])
    assert "ads_a" in selects[0].text
    assert "ads_b" in selects[1].text
    assert "1102" in selects[2].text
    assert "TargetUserName" not in selects[2].text
    assert "tls.verify_hostname       on" in conf
    assert "storage.total_limit_size" not in conf
    assert (dest / "ads.lua").read_bytes() == (render.SOURCE / "ads.lua").read_bytes()


def test_account_che_inietta_xpath_viene_rifiutato(tmp_path, params_text):
    bad = '["ads_a\u0027 or 1=1"]'
    code, dest = run(tmp_path, params(tmp_path, params_text, bad))
    assert code == 1
    assert not dest.exists()


def test_account_duplicato_viene_rifiutato(tmp_path, params_text):
    code, dest = run(tmp_path, params(tmp_path, params_text, '["ads_a", "ADS_A"]'))
    assert code == 1
    assert not dest.exists()


def test_destinazione_tracciabile_viene_rifiutata(tmp_path, params_text):
    path = params(tmp_path, params_text, '["ads_a"]')
    dest = render.ROOT / "config" / "windows-pilota" / "bundle-reale"
    code = render.main(
        ["--parametri", str(path), "--computer-name", "PILOT-01", "--destinazione", str(dest)]
    )
    assert code == 1
    assert not dest.exists()
