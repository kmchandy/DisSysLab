from pricing import discount


def test_small_order_pays_full_price():
    assert discount(50) == 50


def test_large_order_gets_ten_percent_off():
    assert discount(200) == 180


def test_order_of_exactly_100_gets_the_discount():
    assert discount(100) == 90


def test_loyalty_order_of_100():
    assert discount(100) == 80
