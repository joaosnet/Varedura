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


def test_video_android_player_priority_and_commands(monkeypatch):
    from rtsp import video

    monkeypatch.setattr(video, "is_android", lambda: True)
    monkeypatch.setattr(video.Path, "exists", lambda _self: False)

    bins = {
        "am": "/system/bin/am",
        "termux-open": "/data/data/com.termux/files/usr/bin/termux-open",
        "mpv": "/data/data/com.termux/files/usr/bin/mpv",
    }
    monkeypatch.setattr(video.shutil, "which", lambda name: bins.get(name))
    assert video.detectar_player() == ("vlc-android", "/system/bin/am")

    bins.pop("am")
    assert video.detectar_player() == (
        "termux-open",
        "/data/data/com.termux/files/usr/bin/termux-open",
    )

    bins.pop("termux-open")
    assert video.detectar_player() == (
        "mpv-tct",
        "/data/data/com.termux/files/usr/bin/mpv",
    )

    url = "rtsp://cam/stream"
    assert video._montar_comando("vlc-android", "/system/bin/am", url, None, 960, 540) == [
        "/system/bin/am",
        "start",
        "-a",
        "android.intent.action.VIEW",
        "-d",
        url,
        "-p",
        "org.videolan.vlc",
    ]
    assert video._montar_comando("termux-open", "/bin/termux-open", url, None, 960, 540) == [
        "/bin/termux-open",
        url,
    ]
    assert video._montar_comando("mpv-tct", "/bin/mpv", url, None, 960, 540) == [
        "/bin/mpv",
        "--vo=tct",
        "--rtsp-transport=tcp",
        "--profile=low-latency",
        url,
    ]
    assert video.comando_mpv_terminal(url) == [
        "/data/data/com.termux/files/usr/bin/mpv",
        "--vo=tct",
        "--rtsp-transport=tcp",
        "--profile=low-latency",
        url,
    ]


def test_video_erro_se_morreu_and_capturar_e_abrir_snapshot(monkeypatch, tmp_path):
    import types
    from rtsp import video

    class OkIntentProc:
        returncode = 0
        stderr = None

        def wait(self, timeout=None):
            return 0

    assert video.erro_se_morreu(OkIntentProc()) is None

    class FailProc:
        returncode = 1
        stderr = types.SimpleNamespace(read=lambda: "line 1\nfatal stream error\n")

        def wait(self, timeout=None):
            return 1

    assert video.erro_se_morreu(FailProc()) == "fatal stream error"

    monkeypatch.setattr(video.shutil, "which", lambda _name: None)
    ok, msg = video.capturar_e_abrir_snapshot("rtsp://cam/1", str(tmp_path / "s.jpg"))
    assert ok is False
    assert "ffmpeg" in msg.lower()

    opened = []
    monkeypatch.setattr(video.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setattr(video, "salvar_snapshot", lambda url, destino, timeout=10.0: True)
    monkeypatch.setattr(video, "open_file_or_url", lambda target: (opened.append(target), True)[1])
    dest = str(tmp_path / "sub" / "snap.jpg")
    ok2, msg2 = video.capturar_e_abrir_snapshot("rtsp://cam/1", dest)
    assert ok2 is True
    assert dest in msg2
    assert opened == [dest]


def _monta_url_teste(ip: str, caminho: str, user: str, pwd: str) -> str:
    cred = f"{user}:{pwd}@" if user or pwd else ""
    return f"rtsp://{cred}{ip}:554{caminho}"


def _setup_resolver(monkeypatch, tmp_path, fake_validar):
    import rtsp.credenciais as cred
    import rtsp.video as video

    monkeypatch.setattr(cred, "ARQUIVO_CONHECIDOS", tmp_path / "ips_conhecidos.json")
    monkeypatch.setattr(cred, "validar_stream", fake_validar)
    monkeypatch.setattr(video, "validar_stream", fake_validar)
    return cred, video


def test_resolver_ip_lembrado_ok_faz_uma_tentativa(monkeypatch, tmp_path):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        return video.InfoStream(url, True, codec="h264", largura=1920, altura=1080)

    cred, video = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    conhecidos = {
        "192.168.18.82": cred.CredencialIP(
            usuario="admin",
            senha="boa",
            caminho="/stream1",
            url="rtsp://admin:boa@192.168.18.82:554/stream1",
        )
    }
    diag: dict = {}
    res = cred.resolver_ip(
        "192.168.18.82",
        ["/", "/live", "/stream1"],
        [cred.Par("admin", "outra")],
        conhecidos,
        _monta_url_teste,
        intervalo_auth=0,
        diagnostico=diag,
    )
    assert res is not None
    assert len(chamadas) == 1
    assert diag["erro_tipo"] is None
    assert diag["limite_atingido"] is False


def test_resolver_ip_401_com_cofre_grande_limita_tentativas_e_evita_bloqueio(
    monkeypatch, tmp_path
):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        return video.InfoStream(
            url, False, mensagem="401 Unauthorized", erro_tipo=video.ERRO_AUTH
        )

    cred, video = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    conhecidos = {
        "192.168.18.82": cred.CredencialIP(
            usuario="admin",
            senha="salva",
            caminho="/stream1",
            url="rtsp://admin:salva@192.168.18.82:554/stream1",
        )
    }
    vault = [cred.Par("admin", "salva")] + [
        cred.Par(f"user{i}", f"pass{i}") for i in range(10)
    ]
    candidatos = [f"/path{i}" for i in range(39)] + ["/stream1"]
    diag: dict = {}
    res = cred.resolver_ip(
        "192.168.18.82",
        candidatos,
        vault,
        conhecidos,
        _monta_url_teste,
        intervalo_auth=0,
        diagnostico=diag,
    )
    assert res is None
    assert len(chamadas) == cred.DEFAULT_MAX_FALHAS_AUTH
    assert all(url.endswith("/stream1") for url in chamadas)
    assert sum("admin:salva@" in u for u in chamadas) == 1
    assert diag["limite_atingido"] is True
    assert diag["falhas_auth"] == cred.DEFAULT_MAX_FALHAS_AUTH
    assert diag["erro_tipo"] == video.ERRO_AUTH


def test_resolver_ip_401_encontra_nova_credencial_no_caminho_lembrado(
    monkeypatch, tmp_path
):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        if "admin:nova@" in url and url.endswith("/stream1"):
            return video.InfoStream(url, True, codec="h264", largura=1920, altura=1080)
        return video.InfoStream(
            url, False, mensagem="401 Unauthorized", erro_tipo=video.ERRO_AUTH
        )

    cred, video = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    conhecidos = {
        "192.168.18.82": cred.CredencialIP(
            usuario="admin",
            senha="antiga",
            caminho="/stream1",
            url="rtsp://admin:antiga@192.168.18.82:554/stream1",
        )
    }
    res = cred.resolver_ip(
        "192.168.18.82",
        ["/", "/live", "/stream1"],
        [cred.Par("admin", "antiga"), cred.Par("admin", "nova")],
        conhecidos,
        _monta_url_teste,
        intervalo_auth=0,
    )
    assert res is not None
    info, par, caminho = res
    assert len(chamadas) == 2
    assert (par.usuario, par.senha, caminho) == ("admin", "nova", "/stream1")
    assert conhecidos["192.168.18.82"].senha == "nova"


def test_resolver_ip_lembrado_404_testa_outros_caminhos_com_credencial_salva(
    monkeypatch, tmp_path
):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        if "admin:boa@" in url and url.endswith("/stream2"):
            return video.InfoStream(url, True, codec="h264", largura=1280, altura=720)
        return video.InfoStream(
            url, False, mensagem="404 Not Found", erro_tipo=video.ERRO_CAMINHO
        )

    cred, video = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    conhecidos = {
        "192.168.18.82": cred.CredencialIP(
            usuario="admin",
            senha="boa",
            caminho="/stream1",
            url="rtsp://admin:boa@192.168.18.82:554/stream1",
        )
    }
    diag: dict = {}
    res = cred.resolver_ip(
        "192.168.18.82",
        ["/stream1", "/live", "/stream2"],
        [cred.Par("outro", "errada")],
        conhecidos,
        _monta_url_teste,
        intervalo_auth=0,
        diagnostico=diag,
    )
    assert res is not None
    assert len(chamadas) == 3
    assert all("admin:boa@" in u for u in chamadas)
    assert diag["falhas_auth"] == 0
    assert conhecidos["192.168.18.82"].caminho == "/stream2"


@pytest.mark.parametrize("erro_tipo_nome", ["ERRO_FERRAMENTA", "ERRO_BLOQUEIO", "ERRO_REDE"])
def test_resolver_ip_lembrado_erro_fatal_aborta_sem_forca_bruta(
    monkeypatch, tmp_path, erro_tipo_nome
):
    chamadas: list[str] = []
    import rtsp.video as video_mod

    erro_tipo = getattr(video_mod, erro_tipo_nome)

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        return video_mod.InfoStream(
            url, False, mensagem="falha fatal", erro_tipo=erro_tipo
        )

    cred, _ = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    conhecidos = {
        "192.168.18.82": cred.CredencialIP(
            usuario="admin",
            senha="boa",
            caminho="/stream1",
            url="rtsp://admin:boa@192.168.18.82:554/stream1",
        )
    }
    diag: dict = {}
    res = cred.resolver_ip(
        "192.168.18.82",
        ["/", "/live", "/stream1"],
        [cred.Par("user1", "pass1"), cred.Par("user2", "pass2")],
        conhecidos,
        _monta_url_teste,
        intervalo_auth=0,
        diagnostico=diag,
    )
    assert res is None
    assert len(chamadas) == 1
    assert diag["erro_tipo"] == erro_tipo


def test_resolver_ip_novo_promove_caminho_path_first_para_proximo_par(
    monkeypatch, tmp_path
):
    chamadas: list[str] = []

    def fake_validar(url, timeout=6.0):
        chamadas.append(url)
        if not url.endswith("/stream1"):
            return video.InfoStream(
                url, False, mensagem="404 Not Found", erro_tipo=video.ERRO_CAMINHO
            )
        if "admin:certa@" in url:
            return video.InfoStream(url, True, codec="h264", largura=1920, altura=1080)
        return video.InfoStream(
            url, False, mensagem="401 Unauthorized", erro_tipo=video.ERRO_AUTH
        )

    cred, video = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    res = cred.resolver_ip(
        "192.168.18.82",
        ["/", "/live", "/stream1", "/stream2"],
        [cred.Par("admin", "errada"), cred.Par("admin", "certa")],
        {},
        _monta_url_teste,
        intervalo_auth=0,
    )
    assert res is not None
    # 1º par: / (404), /live (404), /stream1 (401 -> promove /stream1)
    # 2º par: /stream1 direto (200 OK) -> sem retestar / e /live
    assert len(chamadas) == 4
    assert chamadas[-1] == "rtsp://admin:certa@192.168.18.82:554/stream1"


def test_resolver_ip_faz_pausa_entre_falhas_de_auth(monkeypatch, tmp_path):
    sleeps: list[float] = []

    def fake_validar(url, timeout=6.0):
        return video.InfoStream(
            url, False, mensagem="401 Unauthorized", erro_tipo=video.ERRO_AUTH
        )

    cred, video = _setup_resolver(monkeypatch, tmp_path, fake_validar)
    monkeypatch.setattr(cred.time, "sleep", lambda s: sleeps.append(s))
    cred.resolver_ip(
        "192.168.18.82",
        ["/stream1"],
        [cred.Par("u1", "p1"), cred.Par("u2", "p2"), cred.Par("u3", "p3")],
        {},
        _monta_url_teste,
        intervalo_auth=0.25,
    )
    assert sleeps == [0.25, 0.25]
