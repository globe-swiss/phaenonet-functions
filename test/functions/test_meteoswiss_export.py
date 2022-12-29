import pytest

from phenoback.functions import meteoswiss_export


@pytest.mark.parametrize("data, expected", [({"year": 2020}, 2020), ({}, None)])
def test_meteoswiss_export(mocker, data, context, expected):
    export_mock = mocker.patch("phenoback.functions.meteoswiss_export.process")
    meteoswiss_export.main(data, context)
    export_mock.assert_called_once_with(expected)
