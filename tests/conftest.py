import pytest


@pytest.fixture
def sample_idea():
    return "A SaaS platform for automated code review using AI"


@pytest.fixture
def sample_topics():
    return ["robotics", "embodied AI", "computer vision"]


@pytest.fixture
def sample_routines():
    return ["email management", "code review", "meeting scheduling", "report generation"]
