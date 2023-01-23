# aeries-importer
Import grades from Google Classroom to Aeries.

Setup Google authentication using steps here: https://developers.google.com/classroom/quickstart/go

### Algorithm

Google Classroom READ side
1. Extract the student email address to get student ID.
2. Fetch all student submissions for published assignments and questions.
3. Transform to mapping of period num list of assignment submissions.

End result:
* A Mapping of period num to assignment name to student grades (using Student ID).

Aeries READ side
1. Crawl scoresByClass to get a mapping of student ID and student number.
2. Map period numbers to Gradebook IDs by crawling the list of gradebooks for Gradebook ID.
3. Crawl the list of assignments in each Gradebook to get a list of Assignment IDs.

End result:
* A mapping of period num to Gradebook ID
* A mapping of period num to assignment name to assignment data.
* A mapping of student ID to student number.

Join Algorithm:
1. Iterate over period num to assignment name to student submissions.
2. Get student number from student ID of submission.
3. Match submission to Aeries assignment based on period num and name. Create assignment if it doesn't exist in Aeries.
4. Validate matched assignment and submission data line up.

End result:
* A mapping of Gradebook ID to list of grading data (student num, assignment number, grade).

Patch Algorithm:
1. Use Milpitas School code: 341
2. Use Gradebook ID, Student num, School Code, Assignment number to patch the grade in Aeries.
3. Validate that the overall grades are accurate and consistent.