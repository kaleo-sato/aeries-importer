# aeries-importer
Import grades from Google Classroom to Aeries.

Setup Google authentication using steps here: https://developers.google.com/classroom/quickstart/go

### Algorithm

Google Classroom READ side
1. Extract the student email address to get student number and map to their Aeries ID.
2. Fetch all student submissions for published assignments and questions.
3. Transform to mapping of period num list of assignment submissions.

End result:
* A Mapping of period num to assignment name to student grades (using Aeries ID).

Aeries READ side
1. Crawl scoresByClass to get a mapping of student ID and student number.
2. Map period numbers to Gradebook IDs by crawling the list of gradebooks for Gradebook ID.
3. Crawl the list of assignments in each Gradebook to get a list of Assignment IDs.

End result:
* A mapping of period num to Gradebook ID.
* A mapping of Gradebook ID to assignment name to assignment data.

Join Algorithm:
1. Iterate over period num to assignment name.
2. For each period and assignment, match Aeries assignment and submission data. Create Aeries assignment if necessary.
3. Validate matched assignment and submission data line up.

End result:
A mapping of Gradebook ID to list of grading data (student ID, assignment number, grade).

Patch Algorithm:
1. Use Milpitas School code: 341
2. Use Gradebook ID, Student ID, School Code, Assignment number to patch the grade in Aeries.
3. Validate that the overall grades are accurate and consistent.