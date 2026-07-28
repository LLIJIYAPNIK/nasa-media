from domain.digest.size_comparison import compare_to_familiar_object


def test_below_first_threshold():
    assert compare_to_familiar_object(5) == "примерно с городской автобус"


def test_exactly_on_threshold():
    assert compare_to_familiar_object(110) == "примерно с футбольное поле"


def test_just_below_threshold():
    assert compare_to_familiar_object(109) == "примерно с футбольное поле"


def test_just_above_threshold():
    assert compare_to_familiar_object(111) == "примерно с Эйфелеву башню"


def test_above_last_threshold():
    assert compare_to_familiar_object(1000) == "крупнее, чем с Останкинскую башню в три раза"
