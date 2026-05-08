def _chat_pkg():
    """供测试通过 src.routers.chat 上的 monkeypatch 生效（逻辑在 logic 子模块）。"""
    import src.routers.chat as pkg

    return pkg
