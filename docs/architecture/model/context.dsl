# People and the systems around Seatlock.

attendee = person "Attendee" "Browses workshops, registers for a seat, joins the waitlist and cancels."
organizer = person "Organizer" "Staff member. Sees seats taken, the waitlist size and who registered."
operator = person "Operator" "Ships releases, answers alarms and follows the runbooks."

email = softwareSystem "Email service" "Sends the promotion email. Amazon SES is the plan. In development the console backend prints the email to the log." "External"
github = softwareSystem "GitHub" "Source code, pull requests and GitHub Actions: CI and the load test." "External"
aws = softwareSystem "Amazon Web Services" "Hosts the target deployment in eu-west-1: ECS Fargate, RDS, ElastiCache, CloudFront, S3." "External"
