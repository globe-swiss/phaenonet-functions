from phenoback.utils import gsecrets


def test_reset(mocker):
    pw_mock = mocker.patch("phenoback.utils.gsecrets.get_mailer_pw")
    user_mock = mocker.patch("phenoback.utils.gsecrets.get_mailer_user")
    gsecrets.reset()
    pw_mock.cache_clear.assert_called()
    user_mock.cache_clear.assert_called()
