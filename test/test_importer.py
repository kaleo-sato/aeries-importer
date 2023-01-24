from unittest.mock import Mock, patch

import pytest

from google_classroom_utils import GoogleClassroomAssignment
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


def test_join_google_classroom_and_aeries_data():
    pass
    # periods_to_assignment_name_to_submissions = {
    #     1: {
    #         'hw1': GoogleClassroomAssignment(submissions={1: 10, 2: None},
    #                                          point_total=10,
    #                                          category='Performance'),
    #         'hw2': GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
    #                                          point_total=5,
    #                                          category='Practice')
    #     },
    #     2: {
    #         'hw1': GoogleClassroomAssignment(submissions={1: 10, 2: None},
    #                                          point_total=10,
    #                                          category='Performance'),
    #         'hw3': GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
    #                                          point_total=5,
    #                                          category='Practice')
    #     }
    # }

