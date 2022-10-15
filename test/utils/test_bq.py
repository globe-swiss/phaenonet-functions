from phenoback.utils import bq


def test_client(mocker):
    task_mock = mocker.patch("phenoback.utils.bq.client")

    bq.client()

    task_mock.assert_called()


def test_insert_data__dict(mocker, caperrors):
    table = "some_table"
    data_dict = {"foo": "bar"}
    client_mock = mocker.patch("phenoback.utils.bq.client")
    client_mock.return_value.insert_rows_json.return_value = []

    bq.insert_data(table, data_dict)

    client_mock.return_value.insert_rows_json.assert_called_with(table, [data_dict])
    assert len(caperrors.records) == 0


def test_insert_data__array(mocker, caperrors):
    table = "some_table"
    data_array = [{"foo1": "bar1"}, {"foo2": "bar2"}]
    client_mock = mocker.patch("phenoback.utils.bq.client")
    client_mock.return_value.insert_rows_json.return_value = []

    bq.insert_data(table, data_array)

    client_mock.return_value.insert_rows_json.assert_called_with(table, data_array)
    assert len(caperrors.records) == 0


def test_insert_data__error(mocker, caperrors):
    table = "some_table"
    data_dict = {}
    client_mock = mocker.patch("phenoback.utils.bq.client")
    client_mock.return_value.insert_rows_json.return_value = [{"error": "value"}]

    bq.insert_data(table, data_dict)

    assert len(caperrors.records) == 1
