from unittest.mock import Mock, patch

from click import BadOptionUsage
from click.testing import CliRunner
from pytest import mark, raises

from main import run_aeries_importer, _split_periods


@mark.parametrize('periods', ('1,2,3,', '', ',1,2,3', '7', '0', '-1', '1,7'))
def test_split_periods_invalid(periods: str):
    with raises(BadOptionUsage, match=r'Supply periods as comma\-separated list of valid period numbers \(1\-6\)\.'):
        _split_periods(periods=periods)


@mark.parametrize('periods,result', (('1,2,3', [1, 2, 3]),
                                     ('1', [1]),
                                     ('6', [6]),
                                     ('5,4', [5, 4])))
def test_split_periods(periods: str, result: list[int]):
    assert _split_periods(periods=periods) == result


def test_run_aeries_importer():
    mock_credentials = Mock()
    mock_classroom_service = Mock()

    with patch('main.authenticate', return_value=mock_credentials) as mock_authenticate:
        with patch('main.build', return_value=mock_classroom_service) as mock_build:
            with patch('main.run_import') as mock_run_import:
                CliRunner().invoke(run_aeries_importer,
                                   args=['--periods', '1,2,3',
                                         '--s-cookie', 'cookie'],
                                   catch_exceptions=False)
                mock_authenticate.assert_called_once()
                mock_build.assert_called_once_with(serviceName='classroom', version='v1', credentials=mock_credentials)
                mock_run_import.assert_called_once_with(classroom_service=mock_classroom_service,
                                                        s_cookie='cookie',
                                                        periods=[1, 2, 3])
