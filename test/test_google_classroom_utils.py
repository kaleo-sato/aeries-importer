from unittest.mock import Mock, patch, call

from arrow import Arrow
from pytest import raises

from google_classroom_utils import GoogleClassroomAssignment, GoogleClassroomData


def test_get_submissions():
    mock_classroom_service = Mock()
    periods = [1, 2]

    google_classroom_data = GoogleClassroomData(periods=periods, classroom_service=mock_classroom_service)

    with patch.object(google_classroom_data, '_get_periods_to_course_ids',
                      return_value={1: 10, 2: 20}) as mock_get_periods_to_course_ids:
        with patch.object(google_classroom_data, '_get_user_ids_to_student_ids',
                          side_effect=[{100: 11, 200: 22}, {300: 33, 400: 44}]) as mock_get_user_ids_to_student_ids:
            with patch.object(google_classroom_data, '_get_all_published_coursework',
                              side_effect=[{1000: GoogleClassroomAssignment(submissions={},
                                                                            assignment_name='hw1',
                                                                            point_total=10,
                                                                            category='Performance'),
                                            2000: GoogleClassroomAssignment(submissions={},
                                                                            assignment_name='hw2',
                                                                            point_total=5,
                                                                            category='Practice')
                                            },
                                           {1000: GoogleClassroomAssignment(submissions={},
                                                                            assignment_name='hw10',
                                                                            point_total=10,
                                                                            category='Performance'),
                                            2000: GoogleClassroomAssignment(submissions={},
                                                                            assignment_name='hw20',
                                                                            point_total=5,
                                                                            category='Practice')
                                            }]) as mock_get_all_published_coursework:
                with patch.object(google_classroom_data, '_get_grades_for_coursework',
                                  side_effect=[{100: 10, 200: 10},
                                               {100: None, 200: 5},
                                               {300: 9, 400: 9},
                                               {300: None, 400: 6}]) as mock_get_grades_for_coursework:
                    google_classroom_data.get_submissions()
                    assert google_classroom_data.periods_to_assignments == {
                        1: [GoogleClassroomAssignment(submissions={11: 10, 22: 10},
                                                      assignment_name='hw1',
                                                      point_total=10,
                                                      category='Performance'),
                            GoogleClassroomAssignment(submissions={11: None, 22: 5},
                                                      assignment_name='hw2',
                                                      point_total=5,
                                                      category='Practice')],
                        2: [GoogleClassroomAssignment(submissions={33: 9, 44: 9},
                                                      assignment_name='hw10',
                                                      point_total=10,
                                                      category='Performance'),
                            GoogleClassroomAssignment(submissions={33: None, 44: 6},
                                                      assignment_name='hw20',
                                                      point_total=5,
                                                      category='Practice')]
                    }

                    mock_get_periods_to_course_ids.assert_called_once_with()
                    mock_get_user_ids_to_student_ids.assert_has_calls([call(course_id=10),
                                                                       call(course_id=20)])
                    mock_get_all_published_coursework.assert_has_calls([call(course_id=10),
                                                                        call(course_id=20)])
                    mock_get_grades_for_coursework.assert_has_calls([call(course_id=10,
                                                                          coursework_id=1000),
                                                                     call(course_id=10,
                                                                          coursework_id=2000),
                                                                     call(course_id=20,
                                                                          coursework_id=1000),
                                                                     call(course_id=20,
                                                                          coursework_id=2000)])


def test_get_periods_to_course_ids():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.list.return_value.execute.return_value = {
        'courses': [{'name': 'course foo',
                     'section': '3A',
                     'courseState': 'ACTIVE',
                     'id': 23},
                    {'name': 'The English II',
                     'section': 'Period 1',
                     'courseState': 'ACTIVE',
                     'id': 10},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'courseState': 'ACTIVE',
                     'id': 20},
                    {'name': 'English I: SDAIE',
                     'courseState': 'ACTIVE',
                     'id': 20},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'courseState': 'ARCHIVED',
                     'id': 20},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 3 & 4',
                     'courseState': 'ACTIVE',
                     'id': 30}
                    ]}

    google_classroom_data = GoogleClassroomData(periods=[1, 2, 3], classroom_service=mock_classroom_service)
    assert google_classroom_data._get_periods_to_course_ids() == {1: 10, 2: 20, 3: 30}


def test_get_periods_to_course_ids_invalid_period():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.list.return_value.execute.return_value = {
        'courses': [{'name': 'course foo',
                     'section': '3A',
                     'courseState': 'ACTIVE',
                     'id': 23},
                    {'name': 'The English II',
                     'section': 'Period 1',
                     'courseState': 'ACTIVE',
                     'id': 10},
                    {'name': 'English I: SDAIE',
                     'section': 'Period 2',
                     'courseState': 'ACTIVE',
                     'id': 20}]}

    google_classroom_data = GoogleClassroomData(periods=[1, 2, 3], classroom_service=mock_classroom_service)
    with raises(ValueError, match=r'Period 3 is not a valid period number.'):
        google_classroom_data._get_periods_to_course_ids()


def test_get_user_ids_to_student_ids():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.students.return_value.list.return_value.execute.side_effect = [
        {
            'students': [{'userId': 33, 'profile': {'emailAddress': 'ab12345@student.musd.org',
                                                    'name': {'fullName': 'Alice Bob'}}},
                         {'userId': 51, 'profile': {'emailAddress': 'un902934@student.musd.org',
                                                    'name': {'fullName': 'Fredward Jacobs'}}}],
            'nextPageToken': 'next_page_token'
        },
        {
            'students': [{'userId': 99, 'profile': {'emailAddress': 'np783273@student.musd.org',
                                                    'name': {'fullName': 'James Dude'}}}]
        },
    ]

    google_classroom_data = GoogleClassroomData(periods=[1, 2, 3], classroom_service=mock_classroom_service)
    assert google_classroom_data._get_user_ids_to_student_ids(course_id=11) == {
        33: 12345,
        51: 902934,
        99: 783273
    }
    assert google_classroom_data.user_ids_to_names == {
        12345: 'Alice Bob',
        902934: 'Fredward Jacobs',
        783273: 'James Dude'
    }


def test_get_user_ids_to_student_ids_invalid_email():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.students.return_value.list.return_value.execute.return_value = {
        'students': [{'userId': 33, 'profile': {'emailAddress': 'asdf5@gmail.com',
                                                'name': {'fullName': 'James Dude'}}}]
    }

    google_classroom_data = GoogleClassroomData(periods=[1, 2, 3], classroom_service=mock_classroom_service)
    with raises(ValueError, match=r'Student email address is in an unexpected format: asdf5@gmail.com'):
        google_classroom_data._get_user_ids_to_student_ids(course_id=11)


def test_get_all_published_coursework():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.courseWork.return_value.list.return_value.execute.return_value = {
        'courseWork': [{'id': 10, 'title': 'Biology ', 'dueDate': {'month': 6}, 'maxPoints': 10,
                        'gradeCategory': {'name': 'Performance'}},
                       {'id': 20, 'title': ' Math  ', 'dueDate': {'month': 1}, 'maxPoints': 100,
                        'gradeCategory': {'name': 'Practice'}},
                       {'id': 30, 'title': 'Wrong', 'dueDate': {'month': 12}, 'maxPoints': 24,
                        'gradeCategory': {'name': 'Participation'}},
                       {'id': 40, 'title': 'Wrong', 'dueDate': {'month': 11}, 'maxPoints': 10,
                        'gradeCategory': {'name': 'Performance'}},
                       {'id': 50, 'title': 'Skip this', 'dueDate': {'month': 4}, 'gradeCategory': {'name': 'Practice'}}]
    }

    google_classroom_data = GoogleClassroomData(periods=[1, 2, 3], classroom_service=mock_classroom_service)

    with patch('google_classroom_utils.Arrow.now', return_value=Arrow(year=2018, month=3, day=7)) as mock_arrow_now:
        assert google_classroom_data._get_all_published_coursework(course_id=11) == {
            10: GoogleClassroomAssignment(submissions={},
                                          assignment_name='Biology',
                                          point_total=10,
                                          category='Performance'),
            20: GoogleClassroomAssignment(submissions={},
                                          assignment_name='Math',
                                          point_total=100,
                                          category='Practice')
        }

        mock_arrow_now.assert_has_calls([call(), call(), call()])  # fourth case is truncated due to sort by dueDate


def test_get_grades_for_coursework():
    mock_classroom_service = Mock()
    (mock_classroom_service
     .courses.return_value
     .courseWork.return_value
     .studentSubmissions.return_value
     .list.return_value
     .execute.return_value) = {
        'studentSubmissions': [{'userId': 10, 'assignedGrade': 20.3},
                               {'userId': 20}]
    }

    google_classroom_data = GoogleClassroomData(periods=[1, 2, 3], classroom_service=mock_classroom_service)
    assert google_classroom_data._get_grades_for_coursework(course_id=11,
                                                            coursework_id=33) == {10: 20.3, 20: None}


def test_get_student_ids_to_names():
    mock_classroom_service = Mock()
    mock_classroom_service.courses.return_value.students.return_value.list.return_value.execute.side_effect = [
        {
            'students': [{'userId': 33, 'profile': {'emailAddress': 'ab12345@student.musd.org',
                                                    'name': {'fullName': 'Alice Bob'}}},
                         {'userId': 51, 'profile': {'emailAddress': 'un902934@student.musd.org',
                                                    'name': {'fullName': 'Fredward Jacobs'}}}],
            'nextPageToken': 'next_page_token'
        },
        {
            'students': [{'userId': 99, 'profile': {'emailAddress': 'np783273@student.musd.org',
                                                    'name': {'fullName': 'James Dude'}}}]
        },
        {
            'students': [{'userId': 33, 'profile': {'emailAddress': 'ab12345@student.musd.org',
                                                    'name': {'fullName': 'Alice Bob'}}},
                         {'userId': 51, 'profile': {'emailAddress': 'un902934@student.musd.org',
                                                    'name': {'fullName': 'Fredward Jacobs'}}}],
            'nextPageToken': 'next_page_token'
        },
        {
            'students': [{'userId': 99, 'profile': {'emailAddress': 'np783273@student.musd.org',
                                                    'name': {'fullName': 'James Dude'}}}]
        }
    ]

    google_classroom_data = GoogleClassroomData(periods=[1, 2], classroom_service=mock_classroom_service)

    with patch.object(google_classroom_data, '_get_periods_to_course_ids',
                      return_value={1: 10, 2: 20}) as mock_get_periods_to_course_ids:
        assert google_classroom_data.get_student_ids_to_names() == {
            1: {
                12345: 'Alice Bob',
                902934: 'Fredward Jacobs',
                783273: 'James Dude'
            },
            2: {
                12345: 'Alice Bob',
                902934: 'Fredward Jacobs',
                783273: 'James Dude'
            }
        }
        mock_get_periods_to_course_ids.assert_called_once_with()


def test_get_overall_grades_not_populated():
    mock_classroom_service = Mock()
    google_classroom_data = GoogleClassroomData(periods=[1, 2], classroom_service=mock_classroom_service)
    with raises(ValueError, match=r'Google Classroom data has not been populated yet.'):
        google_classroom_data.get_overall_grades(period=1, categories_to_weights={'foo': 0.5})


def test_get_overall_grades():
    periods_to_assignments = {

        1: [GoogleClassroomAssignment(submissions={11: 10, 22: 10},
                                      assignment_name='hw1',
                                      point_total=10,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={11: None, 22: 5},
                                      assignment_name='hw2',
                                      point_total=5,
                                      category='Practice'),
            GoogleClassroomAssignment(submissions={11: 2, 22: None},
                                      assignment_name='hw3',
                                      point_total=5,
                                      category='Participation')],
        2: [GoogleClassroomAssignment(submissions={33: 9, 44: 9},
                                      assignment_name='hw10',
                                      point_total=10,
                                      category='Performance'),
            GoogleClassroomAssignment(submissions={33: None, 44: 9},
                                      assignment_name='hw20',
                                      point_total=5,
                                      category='Practice')]
    }

    google_classroom_data = GoogleClassroomData(periods=[1, 2], classroom_service=Mock())
    google_classroom_data.periods_to_assignments = periods_to_assignments

    assert google_classroom_data.get_overall_grades(period=1, categories_to_weights={
        'Performance': 0.5, 'Practice': 0.4, 'Participation': 0.1
    }) == {
        11: 90,  # ((10/10 * 0.5) + (2/5 * 0.1)) / 0.6 * 100  Ignore Practice 40% due to lack of grade in the category
        22: 100
    }

    assert google_classroom_data.get_overall_grades(period=2, categories_to_weights={
        'Performance': 0.5, 'Practice': 0.4, 'Participation': 0.1
    }) == {
        33: 90,  # ((9/10 * 0.5) / 0.5) * 100  Ignore Practice and Participation % due to lack of grades
        44: 130  # (((9/5 * 0.4) + (9/10 * 0.5)) / 0.9) * 100
    }
