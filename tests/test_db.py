from erdospy.db import ErdosDB


def test_statistics_have_expected_shape():
    with ErdosDB() as db:
        stats = db.get_statistics()
    assert stats["total"] > 1000
    assert "open" in stats["by_status"]


def test_get_problem_returns_known_problem():
    with ErdosDB() as db:
        problem = db.get_problem("1")
    assert problem is not None
    assert problem.number == "1"


def test_search_by_status_returns_matching_rows():
    with ErdosDB() as db:
        problems = db.search(status="open", limit=5)
    assert problems
    assert all(problem.status == "open" for problem in problems)
