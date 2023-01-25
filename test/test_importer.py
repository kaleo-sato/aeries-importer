from unittest.mock import Mock, patch

import pytest
from pytest import raises

from aeries_utils import AeriesAssignmentData
from google_classroom_utils import GoogleClassroomAssignment
from importer import run_import, _join_google_classroom_and_aeries_data, AssignmentPatchData


@pytest.mark.xfail
def test_run_import():
    mock_classroom_service = Mock()
    periods = [1, 2]

    with patch('importer._get_emails_to_grades', return_value={'email1': {'hw1': 10, 'hw2': None},
                                                               'email2': {'hw1': 9, 'hw2': 4},
                                                               'email3': {'hw5': 10}}) as mock_get_emails_to_grades:
        assert run_import(classroom_service=mock_classroom_service,
                          periods=periods,
                          s_cookie='aeries-cookie') == {'email1': {'hw1': 10, 'hw2': None},
                                                        'email2': {'hw1': 9, 'hw2': 4},
                                                        'email3': {'hw5': 10}}
        mock_get_emails_to_grades.assert_called_once_with(classroom_service=mock_classroom_service,
                                                          periods=periods)


def test_join_google_classroom_and_aeries_data():
    periods_to_assignment_data = {
        1: [GoogleClassroomAssignment(submissions={1: 10, 2: None},
                                      assignment_name='hw1',
                                      point_total=10,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                      assignment_name='hw2',
                                      point_total=5,
                                      category='Practice')],
        2: [GoogleClassroomAssignment(submissions={1: 10, 2: None},
                                      assignment_name='hw1',
                                      point_total=10,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                      assignment_name='hw3',
                                      point_total=5,
                                      category='Practice')]
    }

    periods_to_gradebook_ids = {
        1: '12345/S',
        2: '6789/F'
    }

    periods_to_student_ids_to_student_nums = {
        1: {
            1: 1000,
            2: 2000,
            3: 3000
        },
        2: {
            1: 5000,
            2: 6000,
            3: 7000
        }
    }

    periods_to_assignment_name_to_aeries_assignments = {
        1: {'hw1': AeriesAssignmentData(id=80, point_total=10),
            'hw2': AeriesAssignmentData(id=81, point_total=5)},
        2: {'hw1': AeriesAssignmentData(id=90, point_total=10)}
    }

    with patch('importer.create_aeries_assignment',
               return_value=AeriesAssignmentData(id=91, point_total=5)) as mock_create_aeries_assignment:
        assert _join_google_classroom_and_aeries_data(
            periods_to_assignment_data=periods_to_assignment_data,
            periods_to_gradebook_ids=periods_to_gradebook_ids,
            periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
            periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
            s_cookie='s_cookie',
            request_verification_token='request_verification_token'
        ) == {
            '12345/S': {
                AssignmentPatchData(student_num=1000,
                                    assignment_number=80,
                                    grade=10),
                AssignmentPatchData(student_num=2000,
                                    assignment_number=80,
                                    grade=None),
                AssignmentPatchData(student_num=1000,
                                    assignment_number=81,
                                    grade=3),
                AssignmentPatchData(student_num=2000,
                                    assignment_number=81,
                                    grade=4),
                AssignmentPatchData(student_num=3000,
                                    assignment_number=81,
                                    grade=1)
            },
            '6789/F': {
                AssignmentPatchData(student_num=5000,
                                    assignment_number=90,
                                    grade=10),
                AssignmentPatchData(student_num=6000,
                                    assignment_number=90,
                                    grade=None),
                AssignmentPatchData(student_num=5000,
                                    assignment_number=91,
                                    grade=3),
                AssignmentPatchData(student_num=6000,
                                    assignment_number=91,
                                    grade=4),
                AssignmentPatchData(student_num=7000,
                                    assignment_number=91,
                                    grade=1)
            }
        }

        mock_create_aeries_assignment.assert_called_once_with(gradebook_number='6789',
                                                              assignment_id=91,
                                                              assignment_name='hw3',
                                                              point_total=5,
                                                              category='Practice',
                                                              s_cookie='s_cookie',
                                                              request_verification_token='request_verification_token')


def test_join_google_classroom_and_aeries_data():
    periods_to_assignment_data = {
        1: [GoogleClassroomAssignment(submissions={1: 10, 2: None},
                                      assignment_name='hw1',
                                      point_total=10,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                      assignment_name='hw2',
                                      point_total=5,
                                      category='Practice')],
        2: [GoogleClassroomAssignment(submissions={1: 10, 2: None},
                                      assignment_name='hw1',
                                      point_total=10,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                      assignment_name='hw3',
                                      point_total=5,
                                      category='Practice')]
    }

    periods_to_gradebook_ids = {
        1: '12345/S',
        2: 'Bad Format/F'
    }

    periods_to_student_ids_to_student_nums = {
        1: {
            1: 1000,
            2: 2000,
            3: 3000
        },
        2: {
            1: 5000,
            2: 6000,
            3: 7000
        }
    }

    periods_to_assignment_name_to_aeries_assignments = {
        1: {'hw1': AeriesAssignmentData(id=80, point_total=10),
            'hw2': AeriesAssignmentData(id=81, point_total=5)},
        2: {'hw1': AeriesAssignmentData(id=90, point_total=10)}
    }

    with raises(ValueError, match='Expected gradebook number to be of pattern <number>/<S or F>, '
                                  f'but was Bad Format/F'):
        _join_google_classroom_and_aeries_data(
            periods_to_assignment_data=periods_to_assignment_data,
            periods_to_gradebook_ids=periods_to_gradebook_ids,
            periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
            periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
            s_cookie='s_cookie',
            request_verification_token='request_verification_token'
        )
