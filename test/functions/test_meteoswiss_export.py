from phenoback.functions import meteoswiss_export


def test_main(mocker, data, context):
    process_mock = mocker.patch("phenoback.functions.meteoswiss_export.process")
    meteoswiss_export.main(data, context)
    process_mock.assert_called()


def test_process__nodata(phenoyear, caperrors):  # pylint: disable=unused-argument
    meteoswiss_export.process()
    assert len(caperrors.records) == 1  # no data received
