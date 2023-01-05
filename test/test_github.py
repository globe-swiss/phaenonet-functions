from inspect import getmembers, isfunction

import pytest

import main


@pytest.fixture
def main_functions():
    return [f[0] for f in getmembers(main, isfunction)]


@pytest.fixture
def github_entrypoints(matrix_includes):
    return [matrix_include["entrypoint"].data for matrix_include in matrix_includes]


@pytest.fixture
def github_deploy_options(deploy_yaml):
    return deploy_yaml["on"]["workflow_dispatch"]["inputs"]["function"]["options"].data


def test_entrypoints(main_functions, github_entrypoints):
    assert set(github_entrypoints).issubset(
        main_functions
    ), f"Entrypoints not found in main: {set(github_entrypoints) - set(main_functions)}"


def test_function_names(gcf_names, github_deploy_options):
    deploy_option_set = set(github_deploy_options)
    assert "all" in deploy_option_set
    deploy_option_set.discard("all")
    assert set(gcf_names) == deploy_option_set


def test_container__consistency(main_yaml):
    assert (
        main_yaml["jobs"]["test"]["container"]
        == main_yaml["jobs"]["test-updated"]["container"]
    )
