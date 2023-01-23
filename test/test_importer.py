from unittest.mock import Mock, patch

import pytest

from importer import run_import


@pytest.mark.xfail
def test_run_import():
    mock_classroom_service = Mock()
    periods = [1, 2]

    with patch('importer._get_emails_to_grades', return_value={'email1': {'hw1': 10, 'hw2': None},
                                                               'email2': {'hw1': 9, 'hw2': 4},
                                                               'email3': {'hw5': 10}}) as mock_get_emails_to_grades:
        assert run_import(classroom_service=mock_classroom_service,
                          periods=periods,
                          aeries_cookie='aeries-cookie') == {'email1': {'hw1': 10, 'hw2': None},
                                                             'email2': {'hw1': 9, 'hw2': 4},
                                                             'email3': {'hw5': 10}}
        mock_get_emails_to_grades.assert_called_once_with(classroom_service=mock_classroom_service,
                                                          periods=periods)
