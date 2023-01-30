# aeries-importer
Import grades from Google Classroom to Aeries.

## Prerequisites:
* Python 3
* Have Kaleo add your email to the [list of test users](https://console.cloud.google.com/apis/credentials/consent?authuser=1&project=aeries-importer).
  * This is to enable Google authentication for Google Classroom.

## Disclaimer:
I developed this with many frail assumptions about the data format in mind. The Aeries API is limited to IT department
of the school district. As a result, I do not have access to a more supported, robust, way to query and manipulate data
to work with Aeries. The methodology described below for Aeries may be fragile and prone to breaking upon random updates
to Aeries' website, and in the worst case scenario, might perform grade updates in an undesired manner.

Because of this, I highly recommend backing up your gradebook before running this script, in case something goes massively
wrong. In the case that you come across a bug, feel free to raise an issue in the Github project, but do not expect me
to get around to responding or fixing it within a timely manner.


## Algorithm

### Google Classroom
1. For each period, get a list of all assignment submissions for all published assignments and questions. Students are
   identified by the student id, which is extracted manually from their email name format.

### Aeries
1. HTML parse the scoresByClass page to get a mapping of student ID and student number.
2. HTML parse the Gradebook IDs by scanning the list of gradebooks page for Gradebook ID.
3. HTML parse the Student Numbers by scanning the list class overall grades page for a mapping from student ID to number.
4. HTML parse list of assignments in each Gradebook to get a list of Assignment IDs, name, point total, and category.
5. HTML parse the categories page for each gradebook to get the class weights for each category.

## Join Algorithm
1. Iterate over period num to assignment name to student submissions.
2. Get student number from student ID of submission.
3. Match submission to Aeries assignment based on period num and name. Create a new assignment if it doesn't exist in Aeries.

## Update Algorithm:
1. Use Milpitas School code: 341
2. Use Gradebook ID, Student num, School Code, Assignment number to send a request to update the grade in Aeries.
