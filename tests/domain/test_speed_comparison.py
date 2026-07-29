from domain.digest.speed_comparison import compare_speed_to_familiar_reference


def test_below_first_threshold():
    assert compare_speed_to_familiar_reference(0.1) == "быстрее, чем звук в воздухе"


def test_exactly_on_threshold():
    assert compare_speed_to_familiar_reference(7.9) == "быстрее, чем МКС на орбите"


def test_just_below_threshold():
    assert compare_speed_to_familiar_reference(7.8) == "быстрее, чем винтовочную пулю"


def test_just_above_threshold():
    assert compare_speed_to_familiar_reference(8.0) == "быстрее, чем МКС на орбите"


def test_above_last_threshold():
    assert compare_speed_to_familiar_reference(40.0) == "быстрее, чем орбитальную скорость Земли вокруг Солнца"
