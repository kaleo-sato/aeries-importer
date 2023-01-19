from unittest.mock import Mock, patch, call

import pytest

from importer import run_import, _get_emails_to_grades, OverallGrades


def test_run_import():
    mock_classroom_service = Mock()
    periods = [1, 2]

    with patch('importer._get_emails_to_grades', return_value={'email1': {'hw1': 10, 'hw2': None},
                                                               'email2': {'hw1': 9, 'hw2': 4},
                                                               'email3': {'hw5': 10}}) as mock_get_emails_to_grades:
        assert run_import(classroom_service=mock_classroom_service,
                          periods=periods) == {'email1': {'hw1': 10, 'hw2': None},
                                               'email2': {'hw1': 9, 'hw2': 4},
                                               'email3': {'hw5': 10}}
        mock_get_emails_to_grades.assert_called_once_with(classroom_service=mock_classroom_service,
                                                          periods=periods)


def test_get_emails_to_grades():
    mock_classroom_service = Mock()
    periods = [1, 2]

    with patch('importer.get_periods_to_course_ids', return_value={1: 10, 2: 20}) as mock_get_periods_to_course_ids:
        with patch('importer.get_user_ids_to_student_emails',
                   side_effect=[{100: 'kaleoemail', 200: 'cindyemail'},
                                {300: 'someone', 400: 'else'}]) as mock_get_user_ids_to_student_emails:
            with patch('importer.get_all_published_coursework',
                       side_effect=[[(1000, 'hw1'), (2000, 'hw2')],
                                    [(1000, 'hw10'), (2000, 'hw20')]]) as mock_get_all_published_coursework:
                with patch('importer.get_grades_for_coursework',
                           side_effect=[{100: 10, 200: 10},
                                        {100: None, 200: 5},
                                        {300: 9, 400: 9},
                                        {300: None, 400: 6}]) as mock_get_grades_for_coursework:
                    assert _get_emails_to_grades(classroom_service=mock_classroom_service,
                                                 periods=periods) == {
                        'kaleoemail': OverallGrades(assignment_name_to_grades={'hw1': 10, 'hw2': None}),
                        'cindyemail': OverallGrades(assignment_name_to_grades={'hw1': 10, 'hw2': 5}),
                        'someone': OverallGrades(assignment_name_to_grades={'hw10': 9, 'hw20': None}),
                        'else': OverallGrades(assignment_name_to_grades={'hw10': 9, 'hw20': 6})}
                    mock_get_periods_to_course_ids.assert_called_once_with(classroom_service=mock_classroom_service,
                                                                           periods=periods)
                    mock_get_user_ids_to_student_emails.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                               course_id=10),
                                                                          call(classroom_service=mock_classroom_service,
                                                                               course_id=20)])
                    mock_get_all_published_coursework.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                             course_id=10),
                                                                        call(classroom_service=mock_classroom_service,
                                                                             course_id=20)])
                    mock_get_grades_for_coursework.assert_has_calls([call(classroom_service=mock_classroom_service,
                                                                          course_id=10,
                                                                          coursework_id=1000),
                                                                     call(classroom_service=mock_classroom_service,
                                                                          course_id=10,
                                                                          coursework_id=2000),
                                                                     call(classroom_service=mock_classroom_service,
                                                                          course_id=20,
                                                                          coursework_id=1000),
                                                                     call(classroom_service=mock_classroom_service,
                                                                          course_id=20,
                                                                          coursework_id=2000)])
