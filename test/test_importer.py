from unittest.mock import Mock, patch

from pytest import raises

from aeries_utils import AeriesAssignmentData, AeriesCategory
from google_classroom_utils import GoogleClassroomAssignment
from importer import run_import, _join_google_classroom_and_aeries_data, AssignmentPatchData


def test_run_import():
    mock_classroom_service = Mock()
    periods = [1, 2]

    submissions = {
        1: [GoogleClassroomAssignment(submissions={5120784: 100,
                                                   34523: 23,
                                                   45634: None},
                                      assignment_name='Essay',
                                      point_total=100,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={9999: 55,
                                                   5120784: 0,
                                                   848: None},
                                      assignment_name='Busywork',
                                      point_total=10,
                                      category='Practice')],
        2: [GoogleClassroomAssignment(submissions={33: 100,
                                                   44: 23,
                                                   55: None},
                                      assignment_name='Art Project',
                                      point_total=100,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={77: 55,
                                                   88: 0,
                                                   99: None},
                                      assignment_name='Raising Hand',
                                      point_total=10,
                                      category='Participation')
            ]
    }

    student_ids_to_student_nums = {
        1: {
            5120784: 1,
            34523: 2,
            45634: 3,
            9999: 9,
            848: 8
        },
        2: {
            33: 10,
            44: 11,
            55: 12,
            77: 13,
            88: 14,
            99: 15
        }
    }

    aeries_assignment_data = {
        1: {
            'Essay': AeriesAssignmentData(id=100,
                                          point_total=100),
        }
    }

    assignment_patch_data = {
        '111/S': [AssignmentPatchData(student_num=1,
                                      assignment_number=100,
                                      grade=100),
                  AssignmentPatchData(student_num=2,
                                      assignment_number=100,
                                      grade=23),
                  AssignmentPatchData(student_num=3,
                                      assignment_number=100,
                                      grade=None),
                  AssignmentPatchData(student_num=9,
                                      assignment_number=101,
                                      grade=5),
                  AssignmentPatchData(student_num=1,
                                      assignment_number=101,
                                      grade=0),
                  AssignmentPatchData(student_num=8,
                                      assignment_number=101,
                                      grade=None)
                  ],
        '222/F': [AssignmentPatchData(student_num=10,
                                      assignment_number=1,
                                      grade=100),
                  AssignmentPatchData(student_num=11,
                                      assignment_number=1,
                                      grade=23),
                  AssignmentPatchData(student_num=12,
                                      assignment_number=1,
                                      grade=None),
                  AssignmentPatchData(student_num=13,
                                      assignment_number=2,
                                      grade=55),
                  AssignmentPatchData(student_num=14,
                                      assignment_number=2,
                                      grade=0),
                  AssignmentPatchData(student_num=15,
                                      assignment_number=2,
                                      grade=None)
                  ]
    }

    periods_to_categories = {
        1: {'Practice': AeriesCategory(id=1,
                                       name='Practice',
                                       weight=1.0)},
        2: {'Practice': AeriesCategory(id=1,
                                       name='Practice',
                                       weight=0.5),
            'Performance': AeriesCategory(id=2,
                                          name='Performance',
                                          weight=0.5)
            }
    }

    with patch('importer.get_submissions', return_value=submissions) as mock_submissions:
        with patch('importer.extract_gradebook_ids_from_html',
                   return_value={1: '111/S', 2: '222/F'}) as mock_gradebook_ids:
            with patch('importer.extract_student_ids_to_student_nums_from_html',
                       return_value=student_ids_to_student_nums) as mock_student_ids_to_student_nums:
                with patch('importer.extract_assignment_information_from_html',
                           return_value=aeries_assignment_data) as mock_extract_assignment_information:
                    with patch('importer.extract_category_information',
                               return_value=periods_to_categories) as mock_category_information:
                        with patch('importer._join_google_classroom_and_aeries_data',
                                   return_value=assignment_patch_data) as mock_patch_data:
                            with patch('importer.update_grades_in_aeries',
                                       return_value=assignment_patch_data) as mock_update_grades_in_aeries:
                                run_import(classroom_service=mock_classroom_service,
                                           periods=periods,
                                           s_cookie='s_cookie',
                                           request_verification_token='token')

                                mock_submissions.assert_called_once_with(classroom_service=mock_classroom_service,
                                                                         periods=periods)
                                mock_gradebook_ids.assert_called_once_with(periods=periods,
                                                                           s_cookie='s_cookie')
                                mock_student_ids_to_student_nums.assert_called_once_with(
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    s_cookie='s_cookie'
                                )
                                mock_extract_assignment_information.assert_called_once_with(
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    s_cookie='s_cookie'
                                )
                                mock_category_information.assert_called_once_with(
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    s_cookie='s_cookie'
                                )
                                mock_patch_data.assert_called_once_with(
                                    periods_to_assignment_data=submissions,
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    periods_to_student_ids_to_student_nums=student_ids_to_student_nums,
                                    periods_to_assignment_name_to_aeries_assignments=aeries_assignment_data,
                                    periods_to_categories=periods_to_categories,
                                    s_cookie='s_cookie',
                                    request_verification_token='token'
                                )
                                mock_update_grades_in_aeries.assert_called_once_with(
                                    assignment_patch_data=assignment_patch_data,
                                    s_cookie='s_cookie'
                                )


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

    periods_to_categories = {
        1: {'Practice': AeriesCategory(id=1,
                                       name='Practice',
                                       weight=1.0)},
        2: {'Practice': AeriesCategory(id=1,
                                       name='Practice',
                                       weight=0.5),
            'Performance': AeriesCategory(id=2,
                                          name='Performance',
                                          weight=0.5)
            }
    }

    with patch('importer.create_aeries_assignment',
               return_value=AeriesAssignmentData(id=91, point_total=5)) as mock_create_aeries_assignment:
        assert _join_google_classroom_and_aeries_data(
            periods_to_assignment_data=periods_to_assignment_data,
            periods_to_gradebook_ids=periods_to_gradebook_ids,
            periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
            periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
            periods_to_categories=periods_to_categories,
            s_cookie='s_cookie',
            request_verification_token='request_verification_token'
        ) == {
            '12345/S': [
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
            ],
            '6789/F': [
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
            ]
        }

        mock_create_aeries_assignment.assert_called_once_with(gradebook_number='6789',
                                                              assignment_id=91,
                                                              assignment_name='hw3',
                                                              point_total=5,
                                                              category=AeriesCategory(id=1,
                                                                                      name='Practice',
                                                                                      weight=0.5),
                                                              s_cookie='s_cookie',
                                                              request_verification_token='request_verification_token')


def test_join_google_classroom_and_aeries_data_exception():
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

    periods_to_categories = {
        1: {'Practice': AeriesCategory(id=1,
                                       name='Practice',
                                       weight=1.0)},
        2: {'Practice': AeriesCategory(id=1,
                                       name='Practice',
                                       weight=0.5),
            'Performance': AeriesCategory(id=2,
                                          name='Performance',
                                          weight=0.5)
            }
    }

    with raises(ValueError, match='Expected gradebook number to be of pattern <number>/<S or F>, '
                                  f'but was Bad Format/F'):
        _join_google_classroom_and_aeries_data(
            periods_to_assignment_data=periods_to_assignment_data,
            periods_to_gradebook_ids=periods_to_gradebook_ids,
            periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
            periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
            periods_to_categories=periods_to_categories,
            s_cookie='s_cookie',
            request_verification_token='request_verification_token'
        )
