def test_smoke_imports():
    import testbed
    import shift
    import bench
    assert testbed is not None
    assert shift is not None
    assert bench is not None
