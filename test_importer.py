from unittest.mock import Mock, patch, call

from arrow import Arrow
from pytest import mark, raises

from aeries_utils import AeriesAssignmentData, AeriesCategory, AeriesClassroomData
from google_classroom_utils import GoogleClassroomAssignment
from importer import run_import, _join_google_classroom_and_aeries_data, AssignmentPatchData, \
    _generate_patch_data_for_assignment


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

        with patch('importer.extract_gradebook_ids_from_html',
                   return_value={1: '111/S', 2: '222/F'}) as mock_gradebook_ids:
            with patch('importer.extract_student_ids_to_student_nums_from_html',
                       return_value=student_ids_to_student_nums) as mock_student_ids_to_student_nums:
                with patch('importer.extract_assignment_information_from_html',
                           return_value=aeries_assignment_data) as mock_extract_assignment_information:
                    with patch('importer.extract_assignment_submissions_from_html',
                               return_value=aeries_submission_data) as mock_extract_assignment_submissions:
                        with patch('importer.extract_gradebook_information_from_html',
                                   return_value=(periods_to_classroom_data, 'token')) as mock_classroom_information:
                            with patch('importer._join_google_classroom_and_aeries_data',
                                       return_value=assignment_patch_data) as mock_patch_data:
                                with patch('importer.update_grades_in_aeries',
                                           return_value=assignment_patch_data) as mock_update_grades_in_aeries:
                                    run_import(classroom_service=mock_classroom_service,
                                               periods=periods,
                                               s_cookie='s_cookie')

                                mock_google_classroom_data.assert_called_once_with(
                                    periods=periods,
                                    classroom_service=mock_classroom_service
                                )
                                mock_google_classroom_data.return_value.get_submissions.assert_called_once()
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
                                mock_extract_assignment_submissions.assert_called_once_with(
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    s_cookie='s_cookie'
                                )
                                mock_classroom_information.assert_called_once_with(
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    s_cookie='s_cookie'
                                )
                                mock_patch_data.assert_called_once_with(
                                    google_classroom_data=mock_google_classroom_data.return_value,
                                    periods_to_gradebook_ids={1: '111/S', 2: '222/F'},
                                    periods_to_student_ids_to_student_nums=student_ids_to_student_nums,
                                    periods_to_assignment_name_to_aeries_assignments=aeries_assignment_data,
                                    periods_to_assignment_ids_to_aeries_submissions=aeries_submission_data,
                                    periods_to_classroom_data=periods_to_classroom_data,
                                    s_cookie='s_cookie',
                                    request_verification_token='token'
                                )
                                mock_update_grades_in_aeries.assert_called_once_with(
                                    assignment_patch_data=assignment_patch_data,
                                    s_cookie='s_cookie'
                                )


def test_join_google_classroom_and_aeries_data():
    mock_classroom_service = Mock()
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

    with patch('importer.create_aeries_assignment',
               return_value=AeriesAssignmentData(id=91,
                                                 point_total=5,
                                                 category='Practice')) as mock_create_aeries_assignment:
        with patch('importer.patch_aeries_assignment',
                   side_effect=[AeriesAssignmentData(id=81,
                                                     point_total=5,
                                                     category='Practice'),
                                AeriesAssignmentData(id=90,
                                                     point_total=10,
                                                     category='Performance')]) as mock_patch_aeries_assignment:
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
                    google_classroom_data=mock_google_classroom_data,
                    periods_to_gradebook_ids=periods_to_gradebook_ids,
                    periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
                    periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
                    periods_to_assignment_ids_to_aeries_submissions=aeries_submission_data,
                    periods_to_classroom_data=periods_to_classroom_data,
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

                mock_create_aeries_assignment.assert_called_once_with(
                    gradebook_number='6789',
                    assignment_id=91,
                    assignment_name='hw3',
                    point_total=5,
                    category=AeriesCategory(id=1,
                                            name='Practice',
                                            weight=0.5),
                    end_term_date=Arrow(2022, 1, 22),
                    s_cookie='s_cookie',
                    request_verification_token='request_verification_token')

                mock_patch_aeries_assignment.assert_has_calls([
                    call(gradebook_number='12345',
                         assignment_id=81,
                         assignment_name='hw2',
                         point_total=5,
                         category=AeriesCategory(id=1,
                                                 name='Practice',
                                                 weight=1.0),
                         end_term_date=Arrow(2022, 6, 4),
                         s_cookie='s_cookie',
                         request_verification_token='request_verification_token'),
                    call(gradebook_number='6789',
                         assignment_id=90,
                         assignment_name='hw1',
                         point_total=10,
                         category=AeriesCategory(id=2,
                                                 name='Performance',
                                                 weight=0.5),
                         end_term_date=Arrow(2022, 1, 22),
                         s_cookie='s_cookie',
                         request_verification_token='request_verification_token')])

                mock_generate_patch_data_for_assignment.assert_has_calls([
                    call(google_classroom_data=mock_google_classroom_data,
                         google_classroom_submissions={1: 10, 2: None},
                         aeries_submissions={1000: '', 2000: 'N/A', 3000: 'MI'},
                         aeries_assignment_id=80,
                         student_ids_to_student_nums={
                             1: 1000,
                             2: 2000,
                             3: 3000
                         }),
                    call(google_classroom_data=mock_google_classroom_data,
                         google_classroom_submissions={1: 3, 2: 4, 3: 1},
                         aeries_submissions={3000: '3', 2000: '4'},
                         aeries_assignment_id=81,
                         student_ids_to_student_nums={
                             1: 1000,
                             2: 2000,
                             3: 3000
                         }),
                    call(google_classroom_data=mock_google_classroom_data,
                         google_classroom_submissions={1: 10, 2: None},
                         aeries_submissions={6000: '10'},
                         aeries_assignment_id=90,
                         student_ids_to_student_nums={
                             1: 5000,
                             2: 6000,
                             3: 7000
                         }),
                    call(google_classroom_data=mock_google_classroom_data,
                         google_classroom_submissions={1: 3, 2: 4, 3: 1},
                         aeries_submissions={},
                         aeries_assignment_id=91,
                         student_ids_to_student_nums={
                             1: 5000,
                             2: 6000,
                             3: 7000
                         })
                ])


def test_join_google_classroom_and_aeries_data_exception():
    mock_classroom_service = Mock()
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
                periods_to_gradebook_ids=periods_to_gradebook_ids,
                periods_to_student_ids_to_student_nums=periods_to_student_ids_to_student_nums,
                periods_to_assignment_name_to_aeries_assignments=periods_to_assignment_name_to_aeries_assignments,
                periods_to_assignment_ids_to_aeries_submissions=aeries_submission_data,
                periods_to_classroom_data=periods_to_classroom_data,
                s_cookie='s_cookie',
                request_verification_token='request_verification_token'
            )

            mock_generate_patch_data_for_assignment.assert_has_calls([
                call(google_classroom_data=mock_google_classroom_data,
                     google_classroom_submissions={1: 10, 2: None},
                     aeries_submissions={1000: '', 2000: 'N/A', 3000: 'MI'},
                     aeries_assignment_id=80,
                     student_ids_to_student_nums={
                         1: 1000,
                         2: 2000,
                         3: 3000
                     }),
                call(google_classroom_data=mock_google_classroom_data,
                     google_classroom_submissions={1: 3, 2: 4, 3: 1},
                     aeries_submissions={3000: '3', 2000: '4'},
                     aeries_assignment_id=81,
                     student_ids_to_student_nums={
                         1: 1000,
                         2: 2000,
                         3: 3000
                     }),
                call(google_classroom_data=mock_google_classroom_data,
                     google_classroom_submissions={1: 10, 2: None},
                     aeries_submissions={6000: '10'},
                     aeries_assignment_id=90,
                     student_ids_to_student_nums={
                         1: 5000,
                         2: 6000,
                         3: 7000
                     })
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
    mock_google_classroom_data = Mock()

    assignment_patch_data = _generate_patch_data_for_assignment(
        google_classroom_data=mock_google_classroom_data,
        google_classroom_submissions=google_classroom_submissions,
        aeries_submissions=aeries_submissions,
        aeries_assignment_id=80,
        student_ids_to_student_nums=student_ids_to_student_nums,
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

    with patch('importer.GoogleClassroomData') as mock_google_classroom_data:
        mock_google_classroom_data.get_student_name.return_value = 'John Doe'

        with raises(ValueError, match='Student John Doe found in Google Classroom who is not enrolled in the Aeries '
                                      'roster. Please check Aeries if they need to added to the class, or if they '
                                      'should be dropped from the Google Classroom roster.'):
            _generate_patch_data_for_assignment(
                google_classroom_data=mock_google_classroom_data,
                google_classroom_submissions=google_classroom_submissions,
                aeries_submissions=aeries_submissions,
                aeries_assignment_id=80,
                student_ids_to_student_nums=student_ids_to_student_nums,
            )
        mock_google_classroom_data.get_student_name.assert_called_once_with(student_id=1000)
