from backend.brokers.symbols import extract_root, normalize


def test_tradovate_native_symbol():
    ns = normalize("MNQM5")
    assert ns.root == "MNQ"
    assert ns.month_code == "M"
    assert ns.year_short == "5"


def test_projectx_contract_id():
    ns = normalize("CON.F.US.MNQ.M25")
    assert ns.root == "MNQ"
    assert ns.month_code == "M"
    assert ns.year_short == "25"


def test_bare_root():
    assert normalize("MNQ").root == "MNQ"


def test_extract_root_shortcut():
    assert extract_root("MESM5") == "MES"
    assert extract_root("CON.F.US.ES.H25") == "ES"
    assert extract_root("GCZ5") == "GC"
