"""Tests for the pure logic of the integrated RTSP scanner (rtsp/ package)."""

import pytest

from rtsp.scanner import hosts_da_faixa, normalizar_faixa


def test_normalizar_faixa_prefixo_curto():
    assert normalizar_faixa("192.168.1") == "192.168.1"


def test_normalizar_faixa_cidr_24_vira_curto():
    assert normalizar_faixa("10.0.0.0/24") == "10.0.0"


def test_normalizar_faixa_cidr_22_canonico():
    assert normalizar_faixa("10.0.0.0/22") == "10.0.0.0/22"


def test_normalizar_faixa_rejeita_ipv6():
    with pytest.raises(ValueError):
        normalizar_faixa("fe80::/64")


def test_normalizar_faixa_rejeita_grande_demais():
    with pytest.raises(ValueError):
        normalizar_faixa("10.0.0.0/8")


def test_normalizar_faixa_rejeita_lixo():
    with pytest.raises(ValueError):
        normalizar_faixa("nao-e-uma-faixa")


def test_hosts_da_faixa_24_tem_254():
    assert len(hosts_da_faixa("192.168.1")) == 254


def test_regioes_round_trip(monkeypatch, tmp_path):
    import rtsp.regioes as reg

    monkeypatch.setattr(reg, "ARQUIVO_REGIOES", tmp_path / "regioes.json")
    regioes = []
    assert reg.adicionar_regiao(regioes, "Casa", reg.TIPO_CAMERA, "cam.ddns.net", 554)
    assert not reg.adicionar_regiao(regioes, "Casa", reg.TIPO_CAMERA, "cam.ddns.net", 554)
    reg.salvar_regioes(regioes)
    recarregadas = reg.carregar_regioes()
    assert len(recarregadas) == 1
    assert recarregadas[0].endereco == "cam.ddns.net"


def test_credenciais_round_trip(monkeypatch, tmp_path):
    import rtsp.credenciais as cred

    monkeypatch.setattr(cred, "ARQUIVO_VAULT", tmp_path / "credenciais.json")
    pares = []
    assert cred.adicionar_par(pares, "admin", "1234")
    assert not cred.adicionar_par(pares, "admin", "1234")  # duplicado
    cred.salvar_vault(pares)
    assert len(cred.carregar_vault()) == 1


def test_carregar_lista_ignora_branco_e_comentarios(tmp_path):
    from rtsp.credenciais import carregar_lista

    arq = tmp_path / "lista.txt"
    arq.write_text("admin\n\n# comentário\nroot\nadmin\n  user  \n", encoding="utf-8")
    assert carregar_lista(arq) == ["admin", "root", "user"]


def test_carregar_lista_arquivo_ausente(tmp_path):
    from rtsp.credenciais import carregar_lista

    assert carregar_lista(tmp_path / "nao-existe.txt") == []


def test_combinar_credenciais_produto():
    from rtsp.credenciais import combinar_credenciais

    pares = combinar_credenciais(["admin", "root"], ["1234", "senha"])
    chaves = {(p.usuario, p.senha) for p in pares}
    assert chaves == {
        ("admin", "1234"),
        ("admin", "senha"),
        ("root", "1234"),
        ("root", "senha"),
    }


def test_combinar_credenciais_apenas_uma_lista():
    from rtsp.credenciais import combinar_credenciais

    assert [(p.usuario, p.senha) for p in combinar_credenciais(["admin"], [])] == [("admin", "")]
    assert [(p.usuario, p.senha) for p in combinar_credenciais([], ["1234"])] == [("", "1234")]
    assert combinar_credenciais([], []) == []
