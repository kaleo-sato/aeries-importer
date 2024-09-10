from unittest.mock import Mock, patch, call

from arrow import Arrow
from pytest import mark, raises

from aeries_utils import AeriesAssignmentData, AeriesCategory, AeriesClassroomData, AeriesData
from google_classroom_utils import GoogleClassroomAssignment, GoogleClassroomData
from importer import run_import, _join_google_classroom_and_aeries_data, AssignmentPatchData, \
    _generate_patch_data_for_assignment, _get_or_create_aeries_assignment


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
                                          point_total=100,
                                          category='Performance'),
        }
    }

    aeries_submission_data = {
        1: {
            100: {
                2: {
                    ''
                },
                3: {
                    '40'
                }
            }
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

    periods_to_classroom_data = {
        1: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=1.0)},
            end_term_dates={'F': Arrow(2022, 1, 22)}
        ),
        2: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=0.5),
                        'Performance': AeriesCategory(id=2,
                                                      name='Performance',
                                                      weight=0.5)},
            end_term_dates={'F': Arrow(2022, 1, 22), 'S': Arrow(2022, 6, 4)}
        )
    }

    with patch('importer.GoogleClassroomData') as mock_google_classroom_data:
        mock_google_classroom_data.return_value.periods_to_assignments = submissions

        with patch('importer.AeriesData') as mock_aeries_data:
            mock_aeries_data.return_value.periods_to_gradebook_ids = {1: '111/S', 2: '222/F'}
            mock_aeries_data.return_value.periods_to_student_ids_to_student_nums = student_ids_to_student_nums
            mock_aeries_data.return_value.periods_to_assignment_information = aeries_assignment_data
            mock_aeries_data.return_value.periods_to_assignment_submissions = aeries_submission_data
            mock_aeries_data.return_value.periods_to_gradebook_information = periods_to_classroom_data

            with patch('importer._join_google_classroom_and_aeries_data',
                       return_value=assignment_patch_data) as mock_patch_data:
                with patch.object(mock_aeries_data.return_value, 'update_grades_in_aeries') as mock_update_grades_in_aeries:
                    run_import(classroom_service=mock_classroom_service,
                               periods=periods,
                               s_cookie='s_cookie')
                    mock_google_classroom_data.assert_called_once_with(
                        periods=periods,
                        classroom_service=mock_classroom_service
                    )
                    mock_google_classroom_data.return_value.get_submissions.assert_called_once()
                    mock_aeries_data.return_value.extract_gradebook_ids_from_html.assert_called_once()
                    mock_aeries_data.return_value.extract_student_ids_to_student_nums_from_html.assert_called_once()
                    mock_aeries_data.return_value.extract_assignment_information_from_html.assert_called_once()
                    mock_aeries_data.return_value.extract_assignment_submissions_from_html.assert_called_once()
                    mock_aeries_data.return_value.extract_gradebook_information_from_html.assert_called_once()

                    mock_patch_data.assert_called_once_with(
                        google_classroom_data=mock_google_classroom_data.return_value,
                        aeries_data=mock_aeries_data.return_value
                    )
                    mock_update_grades_in_aeries.assert_called_once_with(assignment_patch_data=assignment_patch_data)


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
                                      category='Practice'),
            GoogleClassroomAssignment(submissions={},  # Do not process
                                      assignment_name='hw4',
                                      point_total=5,
                                      category='Practice'),
            GoogleClassroomAssignment(submissions={1: None, 2: None},  # Do not process
                                      assignment_name='hw2',
                                      point_total=5,
                                      category='Practice')]
    }

    mock_classroom_service = Mock()
    google_classroom_data = GoogleClassroomData(periods=[1, 2], classroom_service=mock_classroom_service)
    google_classroom_data.periods_to_assignments = periods_to_assignment_data

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
        1: {'hw1': AeriesAssignmentData(id=80, point_total=10, category='Performance'),
            'hw2': AeriesAssignmentData(id=81, point_total=12093810293801293812, category='Practice')},
        2: {'hw1': AeriesAssignmentData(id=90, point_total=10, category='Something else')}
    }

    aeries_submission_data = {
        1: {80: {1000: '', 2000: 'N/A', 3000: 'MI'},
            81: {3000: '3', 2000: '4'}},
        2: {90: {6000: '10'}}
    }

    periods_to_classroom_data = {
        1: AeriesClassroomData(
            categories={
                'Practice': AeriesCategory(id=1,
                                           name='Practice',
                                           weight=1.0)},
            end_term_dates={
                'F': Arrow(2022, 1, 22),
                'S': Arrow(2022, 6, 4)
            }
        ),
        2: AeriesClassroomData(
            categories={
                'Practice': AeriesCategory(id=1,
                                           name='Practice',
                                           weight=0.5),
                'Performance': AeriesCategory(id=2,
                                              name='Performance',
                                              weight=0.5)},
            end_term_dates={
                'F': Arrow(2022, 1, 22),
                'S': Arrow(2022, 6, 4)
            }
        )
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = periods_to_gradebook_ids
    aeries_data.periods_to_student_ids_to_student_nums = periods_to_student_ids_to_student_nums
    aeries_data.periods_to_assignment_information = periods_to_assignment_name_to_aeries_assignments
    aeries_data.periods_to_assignment_submissions = aeries_submission_data
    aeries_data.periods_to_gradebook_information = periods_to_classroom_data
    aeries_data.request_verification_token = 'request_verification_token'

    with patch('importer._get_or_create_aeries_assignment',
               side_effect=[
                   (AeriesAssignmentData(id=80,
                                         point_total=10,
                                         category='Practice'), 82),
                   (AeriesAssignmentData(id=81,
                                         point_total=5,
                                         category='Practice'), 82),
                   (AeriesAssignmentData(id=91,
                                         point_total=5,
                                         category='Practice'), 92),
                   (AeriesAssignmentData(id=90,
                                         point_total=10,
                                         category='Performance'), 92)
               ]) as mock_get_or_create_aeries_assignment:
        with patch('importer._generate_patch_data_for_assignment',
                   side_effect=[[
                       AssignmentPatchData(student_num=1000,
                                           assignment_number=80,
                                           grade=10),
                       AssignmentPatchData(student_num=2000,
                                           assignment_number=80,
                                           grade=None)
                   ], [
                       AssignmentPatchData(student_num=1000,
                                           assignment_number=81,
                                           grade=3),
                       AssignmentPatchData(student_num=2000,
                                           assignment_number=81,
                                           grade=4),
                       AssignmentPatchData(student_num=3000,
                                           assignment_number=81,
                                           grade=1)
                   ], [
                       AssignmentPatchData(student_num=5000,
                                           assignment_number=90,
                                           grade=10),
                       AssignmentPatchData(student_num=6000,
                                           assignment_number=90,
                                           grade=None)
                   ], [
                       AssignmentPatchData(student_num=5000,
                                           assignment_number=91,
                                           grade=3),
                       AssignmentPatchData(student_num=6000,
                                           assignment_number=91,
                                           grade=4),
                       AssignmentPatchData(student_num=7000,
                                           assignment_number=91,
                                           grade=1)
                   ]]) as mock_generate_patch_data_for_assignment:
            assert _join_google_classroom_and_aeries_data(
                google_classroom_data=google_classroom_data,
                aeries_data=aeries_data
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

            mock_get_or_create_aeries_assignment.assert_has_calls([
                call(google_classroom_assignment=google_classroom_data.periods_to_assignments[1][0],
                     aeries_data=aeries_data,
                     period=1,
                     next_assignment_id=82),
                call(google_classroom_assignment=google_classroom_data.periods_to_assignments[1][1],
                     aeries_data=aeries_data,
                     period=1,
                     next_assignment_id=82),
                call(google_classroom_assignment=google_classroom_data.periods_to_assignments[2][0],
                     aeries_data=aeries_data,
                     period=2,
                     next_assignment_id=91),
                call(google_classroom_assignment=google_classroom_data.periods_to_assignments[2][1],
                     aeries_data=aeries_data,
                     period=2,
                     next_assignment_id=92),
            ])

            mock_generate_patch_data_for_assignment.assert_has_calls([
                call(google_classroom_data=google_classroom_data,
                     google_classroom_submissions={1: 10, 2: None},
                     aeries_data=aeries_data,
                     aeries_assignment_id=80,
                     period=1),
                call(google_classroom_data=google_classroom_data,
                     google_classroom_submissions={1: 3, 2: 4, 3: 1},
                     aeries_data=aeries_data,
                     aeries_assignment_id=81,
                     period=1),
                call(google_classroom_data=google_classroom_data,
                     google_classroom_submissions={1: 10, 2: None},
                     aeries_data=aeries_data,
                     aeries_assignment_id=91,
                     period=2),
                call(google_classroom_data=google_classroom_data,
                     google_classroom_submissions={1: 3, 2: 4, 3: 1},
                     aeries_data=aeries_data,
                     aeries_assignment_id=90,
                     period=2)
            ])


def test_get_or_create_aeries_assignment_creation():
    periods_to_gradebook_ids = {
        1: '12345/F'
    }

    periods_to_student_ids_to_student_nums = {
        1: {
            1: 1000,
            2: 2000,
            3: 3000
        }
    }

    periods_to_assignment_name_to_aeries_assignments = {1: {}}
    aeries_submission_data = {1: {}}

    periods_to_classroom_data = {
        1: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=1.0)},
            end_term_dates={'F': Arrow(2022, 1, 22)}
        )
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = periods_to_gradebook_ids
    aeries_data.periods_to_student_ids_to_student_nums = periods_to_student_ids_to_student_nums
    aeries_data.periods_to_assignment_information = periods_to_assignment_name_to_aeries_assignments
    aeries_data.periods_to_assignment_submissions = aeries_submission_data
    aeries_data.periods_to_gradebook_information = periods_to_classroom_data
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, 'create_aeries_assignment',
                      return_value=AeriesAssignmentData(id=80,
                                                        point_total=10,
                                                        category='Practice')) as mock_create_aeries_assignment:
        assert _get_or_create_aeries_assignment(
            google_classroom_assignment=GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                                                  assignment_name='hw2',
                                                                  point_total=5,
                                                                  category='Practice'),
            aeries_data=aeries_data,
            period=1,
            next_assignment_id=80
        ) == (AeriesAssignmentData(id=80,
                                   point_total=10,
                                   category='Practice'), 81)

        mock_create_aeries_assignment.assert_has_calls([
            call(gradebook_number='12345',
                 assignment_id=80,
                 assignment_name='hw2',
                 point_total=5,
                 category=AeriesCategory(name='Practice', weight=1.0, id=1),
                 end_term_date=Arrow(2022, 1, 22))
        ])


def test_get_or_create_aeries_assignment_patch():
    periods_to_gradebook_ids = {
        1: '12345/F'
    }

    periods_to_student_ids_to_student_nums = {
        1: {
            1: 1000,
            2: 2000,
            3: 3000
        }
    }

    periods_to_assignment_name_to_aeries_assignments = {1: {'hw1': AeriesAssignmentData(id=80,
                                                                                        point_total=8,
                                                                                        category='Practice')}}
    aeries_submission_data = {1: {}}

    periods_to_classroom_data = {
        1: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=1.0)},
            end_term_dates={'F': Arrow(2022, 1, 22)}
        )
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = periods_to_gradebook_ids
    aeries_data.periods_to_student_ids_to_student_nums = periods_to_student_ids_to_student_nums
    aeries_data.periods_to_assignment_information = periods_to_assignment_name_to_aeries_assignments
    aeries_data.periods_to_assignment_submissions = aeries_submission_data
    aeries_data.periods_to_gradebook_information = periods_to_classroom_data
    aeries_data.request_verification_token = 'request_verification_token'

    with patch.object(aeries_data, 'patch_aeries_assignment',
                      return_value=AeriesAssignmentData(id=80,
                                                        point_total=10,
                                                        category='Practice')) as mock_patch_aeries_assignment:
        assert _get_or_create_aeries_assignment(
            google_classroom_assignment=GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                                                  assignment_name='hw1',
                                                                  point_total=5,
                                                                  category='Practice'),
            aeries_data=aeries_data,
            period=1,
            next_assignment_id=91
        ) == (AeriesAssignmentData(id=80,
                                   point_total=10,
                                   category='Practice'), 91)
        mock_patch_aeries_assignment.assert_has_calls([
            call(gradebook_number='12345',
                 assignment_id=80,
                 assignment_name='hw1',
                 point_total=5,
                 category=AeriesCategory(name='Practice', weight=1.0, id=1),
                 end_term_date=Arrow(2022, 1, 22))
        ])


def test_get_or_create_aeries_assignment_existing():
    periods_to_gradebook_ids = {
        1: '12345/F'
    }

    periods_to_student_ids_to_student_nums = {
        1: {
            1: 1000,
            2: 2000,
            3: 3000
        }
    }

    periods_to_assignment_name_to_aeries_assignments = {1: {'hw1': AeriesAssignmentData(id=80,
                                                                                        point_total=5,
                                                                                        category='Practice')}}
    aeries_submission_data = {1: {}}

    periods_to_classroom_data = {
        1: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=1.0)},
            end_term_dates={'F': Arrow(2022, 1, 22)}
        )
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = periods_to_gradebook_ids
    aeries_data.periods_to_student_ids_to_student_nums = periods_to_student_ids_to_student_nums
    aeries_data.periods_to_assignment_information = periods_to_assignment_name_to_aeries_assignments
    aeries_data.periods_to_assignment_submissions = aeries_submission_data
    aeries_data.periods_to_gradebook_information = periods_to_classroom_data
    aeries_data.request_verification_token = 'request_verification_token'

    assert _get_or_create_aeries_assignment(
        google_classroom_assignment=GoogleClassroomAssignment(submissions={1: 3, 2: 4, 3: 1},
                                                              assignment_name='hw1',
                                                              point_total=5,
                                                              category='Practice'),
        aeries_data=aeries_data,
        period=1,
        next_assignment_id=91
    ) == (AeriesAssignmentData(id=80,
                               point_total=5,
                               category='Practice'), 91)


def test_get_or_create_aeries_assignment_exception():
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

    mock_google_classroom_data = Mock()
    mock_google_classroom_data.periods_to_assignments = periods_to_assignment_data

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
        1: {'hw1': AeriesAssignmentData(id=80, point_total=10, category='Performance'),
            'hw2': AeriesAssignmentData(id=81, point_total=5, category='Practice')},
        2: {'hw1': AeriesAssignmentData(id=90, point_total=10, category='Performance')}
    }

    aeries_submission_data = {
        1: {80: {1000: '', 2000: 'N/A', 3000: 'MI'},
            81: {3000: '3', 2000: '4'}},
        2: {90: {6000: '10'}}
    }

    periods_to_classroom_data = {
        1: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=1.0)},
            end_term_dates={'F': Arrow(2022, 1, 22)}
        ),
        2: AeriesClassroomData(
            categories={'Practice': AeriesCategory(id=1,
                                                   name='Practice',
                                                   weight=0.5),
                        'Performance': AeriesCategory(id=2,
                                                      name='Performance',
                                                      weight=0.5)},
            end_term_dates={'F': Arrow(2022, 1, 22), 'S': Arrow(2022, 6, 4)}
        )
    }

    aeries_data = AeriesData(periods=[1, 2], s_cookie='s_cookie')
    aeries_data.periods_to_gradebook_ids = periods_to_gradebook_ids
    aeries_data.periods_to_student_ids_to_student_nums = periods_to_student_ids_to_student_nums
    aeries_data.periods_to_assignment_information = periods_to_assignment_name_to_aeries_assignments
    aeries_data.periods_to_assignment_submissions = aeries_submission_data
    aeries_data.periods_to_gradebook_information = periods_to_classroom_data
    aeries_data.request_verification_token = 'request_verification_token'

    with raises(ValueError, match='Expected gradebook number to be of pattern <number>/<S or F>, '
                                  'but was Bad Format/F'):
        with patch('importer._generate_patch_data_for_assignment',
                   side_effect=[[
                       AssignmentPatchData(student_num=1000,
                                           assignment_number=80,
                                           grade=10),
                       AssignmentPatchData(student_num=2000,
                                           assignment_number=80,
                                           grade=None)
                   ], [
                       AssignmentPatchData(student_num=1000,
                                           assignment_number=81,
                                           grade=3),
                       AssignmentPatchData(student_num=2000,
                                           assignment_number=81,
                                           grade=4),
                       AssignmentPatchData(student_num=3000,
                                           assignment_number=81,
                                           grade=1)
                   ], [
                       AssignmentPatchData(student_num=5000,
                                           assignment_number=90,
                                           grade=10),
                       AssignmentPatchData(student_num=6000,
                                           assignment_number=90,
                                           grade=None)
                   ]]) as mock_generate_patch_data_for_assignment:
            _join_google_classroom_and_aeries_data(
                google_classroom_data=mock_google_classroom_data,
                aeries_data=aeries_data
            )

            mock_generate_patch_data_for_assignment.assert_has_calls([
                call(google_classroom_data=mock_google_classroom_data,
                     google_classroom_submissions={1: 10, 2: None},
                     aeries_data=aeries_data,
                     aeries_assignment_id=80,
                     period=1),
                call(google_classroom_data=mock_google_classroom_data,
                     google_classroom_submissions={1: 3, 2: 4, 3: 1},
                     aeries_data=aeries_data,
                     aeries_assignment_id=81,
                     period=1),
                call(google_classroom_data=mock_google_classroom_data,
                     google_classroom_submissions={1: 10, 2: None},
                     aeries_data=aeries_data,
                     aeries_assignment_id=90,
                     period=2)
            ])


@mark.parametrize('google_classroom_submissions,aeries_submissions,student_ids_to_student_nums,'
                  'expected_assignment_patch_data', (
                          ({1: None, 2: None}, {1000: '', 2000: '10', 3000: 'MI'}, {1: 1000, 2: 2000, 3: 3000},
                           [
                               AssignmentPatchData(student_num=2000,
                                                   assignment_number=80,
                                                   grade=None)
                           ]),
                          ({1: 3, 2: 0, 3: 0}, {1000: '', 3000: '3', 2000: 'MI'}, {1: 1000, 2: 2000, 3: 3000},
                           [
                               AssignmentPatchData(student_num=1000,
                                                   assignment_number=80,
                                                   grade=3),
                               AssignmentPatchData(student_num=3000,
                                                   assignment_number=80,
                                                   grade=0)
                           ]),
                          ({1: 3, 2: 10, 3: 20, 4: 30, 5: 50}, {1000: '', 2000: 'N/A', 3000: 'MI', 4000: '10', 5000: 50},
                           {1: 1000, 2: 2000, 3: 3000, 4: 4000, 5: 5000},
                           [
                               AssignmentPatchData(student_num=1000,
                                                   assignment_number=80,
                                                   grade=3),
                               AssignmentPatchData(student_num=2000,
                                                   assignment_number=80,
                                                   grade=10),
                               AssignmentPatchData(student_num=3000,
                                                   assignment_number=80,
                                                   grade=20),
                               AssignmentPatchData(student_num=4000,
                                                   assignment_number=80,
                                                   grade=30)
                           ]),
                          ({1: 0, 2: 10, 3: 20}, {}, {1: 1000, 2: 2000, 3: 3000},
                           [
                               AssignmentPatchData(student_num=1000,
                                                   assignment_number=80,
                                                   grade=0),
                               AssignmentPatchData(student_num=2000,
                                                   assignment_number=80,
                                                   grade=10),
                               AssignmentPatchData(student_num=3000,
                                                   assignment_number=80,
                                                   grade=20)
                           ])))
def test_generate_patch_data_for_assignment(google_classroom_submissions,
                                            aeries_submissions,
                                            student_ids_to_student_nums,
                                            expected_assignment_patch_data):
    google_classroom_data = GoogleClassroomData(periods=[1], classroom_service=Mock())
    aeries_data = AeriesData(periods=[1], s_cookie='s_cookie')
    aeries_data.periods_to_student_ids_to_student_nums = {1: student_ids_to_student_nums}
    aeries_data.periods_to_assignment_submissions = {1: {80: aeries_submissions}}

    assignment_patch_data = _generate_patch_data_for_assignment(
        google_classroom_data=google_classroom_data,
        google_classroom_submissions=google_classroom_submissions,
        aeries_data=aeries_data,
        aeries_assignment_id=80,
        period=1
    )

    assert assignment_patch_data == expected_assignment_patch_data


def test_generate_patch_data_for_assignment_exception():
    google_classroom_submissions = {
        1000: 10,
        2: None
    }

    student_ids_to_student_nums = {
        1: 1000,
        2: 2000,
        3: 3000
    }

    aeries_submissions = {
        1000: '', 2000: 'N/A', 3000: 'MI'
    }

    aeries_data = AeriesData(periods=[1], s_cookie='s_cookie')
    aeries_data.periods_to_student_ids_to_student_nums = {1: student_ids_to_student_nums}
    aeries_data.periods_to_assignment_submissions = {1: {80: aeries_submissions}}

    google_classroom_data = GoogleClassroomData(periods=[1], classroom_service=Mock())
    google_classroom_data.user_ids_to_names = {1000: 'John Doe'}

    with raises(ValueError, match='Student John Doe found in Google Classroom who is not enrolled in the Aeries '
                                  'roster. Please check Aeries if they need to added to the class, or if they '
                                  'should be dropped from the Google Classroom roster.'):
        _generate_patch_data_for_assignment(
            google_classroom_data=google_classroom_data,
            google_classroom_submissions=google_classroom_submissions,
            aeries_data=aeries_data,
            aeries_assignment_id=80,
            period=1
        )
